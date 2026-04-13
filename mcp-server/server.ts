#!/usr/bin/env bun
import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { ListToolsRequestSchema, CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js'
import { mkdirSync, existsSync, readFileSync, writeFileSync, readdirSync, renameSync } from 'fs'
import { join, resolve, basename } from 'path'

const AGENT_NAME = process.env.AGENT_NAME
const PROJECT_ROOT = process.env.PROJECT_ROOT

if (!AGENT_NAME || !PROJECT_ROOT) {
  process.stderr.write('dispatch MCP: AGENT_NAME and PROJECT_ROOT required\n')
  process.exit(1)
}

const ORCH_DIR = resolve(PROJECT_ROOT, '.orchestrator')
const DISPATCH_DIR = resolve(PROJECT_ROOT, 'dispatch')
const AGENT_DIR = join(DISPATCH_DIR, AGENT_NAME)
const INBOX_DIR = join(AGENT_DIR, 'inbox')
const OUTBOX_DIR = join(AGENT_DIR, 'outbox')
const REPORTS_DIR = join(AGENT_DIR, 'reports')
const DONE_DIR = join(AGENT_DIR, 'done')

for (const dir of [INBOX_DIR, OUTBOX_DIR, REPORTS_DIR, DONE_DIR, join(AGENT_DIR, 'archive')]) {
  mkdirSync(dir, { recursive: true })
}

function ts(): string {
  return new Date().toISOString().replace('T', ' ').slice(0, 19)
}

function stamp(): string {
  return new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_')
}

function writeDispatchFile(dir: string, prefix: string, content: string): string {
  const file = join(dir, `${stamp()}-${prefix}.md`)
  writeFileSync(file, content, 'utf8')
  return file
}

function canonicalMessage(to: string, message: string, type = 'direct_message', taskId = '', verdict = ''): string {
  const lines = [`FROM: ${AGENT_NAME}`, `TO: ${to}`, `TYPE: ${type}`]
  if (taskId) lines.push(`TASK_ID: ${taskId}`)
  if (verdict) lines.push(`VERDICT: ${verdict}`)
  lines.push(`TIMESTAMP: ${ts()}`, '---', message.trim(), '')
  return lines.join('\n')
}

function listInboxFiles(): string[] {
  return readdirSync(INBOX_DIR).filter(name => name.endsWith('.md')).sort()
}

function consumeInbox(name: string): string {
  const src = join(INBOX_DIR, name)
  const dest = join(DONE_DIR, name)
  renameSync(src, dest)
  return readFileSync(dest, 'utf8')
}

const mcp = new Server(
  { name: `dispatch-${AGENT_NAME}`, version: '3.0.0' },
  {
    capabilities: { tools: {} },
    instructions: [
      `You are the ${AGENT_NAME} gate agent.`,
      'All live coordination traffic is file-based under dispatch/<agent>/.',
      'Use send for outbound messages and read_inbox for inbound work.',
      'Use write_approval to write approvals into .orchestrator/approvals/.',
    ].join('\n'),
  },
)

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'send',
      description: 'Queue an outbound dispatch message by writing to your outbox.',
      inputSchema: {
        type: 'object',
        properties: {
          to: { type: 'string' },
          message: { type: 'string' },
          type: { type: 'string' },
          task_id: { type: 'string' },
        },
        required: ['to', 'message'],
      },
    },
    {
      name: 'read_inbox',
      description: 'Read and consume unread files from dispatch/<agent>/inbox/.',
      inputSchema: {
        type: 'object',
        properties: {
          all: { type: 'boolean' },
        },
      },
    },
    {
      name: 'write_approval',
      description: 'Write a task approval JSON file into .orchestrator/approvals/.',
      inputSchema: {
        type: 'object',
        properties: {
          task_id: { type: 'string' },
          verdict: { type: 'string' },
          diff_sha256: { type: 'string' },
        },
        required: ['task_id'],
      },
    },
    {
      name: 'read_diff',
      description: 'Read a diff file from .orchestrator/diffs/.',
      inputSchema: {
        type: 'object',
        properties: { task_id: { type: 'string' } },
        required: ['task_id'],
      },
    },
  ],
}))

mcp.setRequestHandler(CallToolRequestSchema, async req => {
  const args = (req.params.arguments ?? {}) as Record<string, unknown>
  try {
    switch (req.params.name) {
      case 'send': {
        const to = String(args.to)
        const message = String(args.message)
        const type = String(args.type ?? 'direct_message')
        const taskId = String(args.task_id ?? '')
        const file = writeDispatchFile(OUTBOX_DIR, `to-${to}`, canonicalMessage(to, message, type, taskId))
        return { content: [{ type: 'text', text: `queued ${basename(file)}` }] }
      }
      case 'read_inbox': {
        const files = listInboxFiles()
        if (!files.length) {
          return { content: [{ type: 'text', text: 'no unread dispatch files' }] }
        }
        const readAll = Boolean(args.all)
        const chosen = readAll ? files : [files[0]]
        const payload = chosen.map(name => `# ${name}\n\n${consumeInbox(name).trim()}`).join('\n\n')
        return { content: [{ type: 'text', text: payload }] }
      }
      case 'write_approval': {
        const taskId = String(args.task_id)
        const verdict = String(args.verdict ?? 'approved')
        const diffSha = String(args.diff_sha256 ?? '')
        const file = join(ORCH_DIR, 'approvals', `${taskId}-${AGENT_NAME}.json`)
        mkdirSync(join(ORCH_DIR, 'approvals'), { recursive: true })
        writeFileSync(file, JSON.stringify({ task_id: taskId, agent: AGENT_NAME, verdict, approved: verdict === 'approved', diff_sha256: diffSha, at: ts() }, null, 2), 'utf8')
        return { content: [{ type: 'text', text: `approval written: ${file}` }] }
      }
      case 'read_diff': {
        const taskId = String(args.task_id)
        const file = join(ORCH_DIR, 'diffs', `${taskId}.diff`)
        if (!existsSync(file)) {
          return { content: [{ type: 'text', text: `no diff found at ${file}` }], isError: true }
        }
        return { content: [{ type: 'text', text: readFileSync(file, 'utf8') || '(empty diff)' }] }
      }
      default:
        return { content: [{ type: 'text', text: `unknown tool: ${req.params.name}` }], isError: true }
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return { content: [{ type: 'text', text: `${req.params.name} failed: ${msg}` }], isError: true }
  }
})

await mcp.connect(new StdioServerTransport())
