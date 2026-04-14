# Logging And Monitor Contract

## Purpose

This contract defines the single event pipeline for dispatcher logging and monitor streaming.

The goal is to:

- tail Claude session JSONL incrementally
- parse each new record fully exactly once
- derive both durable trace output and monitor output from the same parsed event
- avoid overlapping loggers that describe the same event in different partial formats

## Source Of Truth

The source input is Claude session JSONL, not ad hoc hook summaries.

- Main-session transcripts live under `C:\Users\Allan\.claude\projects\<project-slug>\<session-id>.jsonl`
- Subagent transcripts may be passed directly via hook payload `transcript_path`
- Hook payload is only the trigger and session locator
- The pipeline must prefer:
  1. `transcript_path` from hook input when present
  2. `session_id` + current project cwd to resolve the exact JSONL
  3. latest project JSONL only as a last-resort fallback

Project slug resolution follows Claude's project directory rule:

- replace `:` with `-`
- replace `\` and `/` with `-`

Example:

- `D:\IA\dispatcher_repo` -> `D--IA-dispatcher-repo`

## Trigger Model

The current dispatcher hook path remains the activation point.

- `hooks/monitor_ingest.py` is the primary trigger into the consolidated pipeline
- the hook must read `session_id`, optional `transcript_path`, and current agent identity
- the hook does not invent its own activity summary as the primary data model
- reviewer sessions may also trigger the same pipeline so their output can become secondary monitor input

## Tailing Contract

The tailer must treat transcripts as append-only JSONL.

- checkpoint by byte offset
- read only bytes after the last committed offset
- parse complete lines only
- if the last line is partial or invalid JSON because the write is incomplete, stop before that line and keep its starting offset for the next poll
- never advance the checkpoint past an incomplete final line

Checkpoint state must be durable and keyed by source session.

Minimum checkpoint fields:

- `session_id`
- `transcript_path`
- `offset`
- `updated_at`

## Canonical Parsed Event Model

Each raw JSONL line produces at most one canonical parsed event.

Every canonical event must preserve the original record's meaningful content without summarizing it away.

Minimum canonical fields:

- `session_id`
- `source_agent`
- `source_role`
- `source_kind`
- `timestamp`
- `uuid`
- `parent_uuid`
- `record_type`
- `subtype`
- `cwd`
- `git_branch`
- `text_blocks`
- `code_blocks`
- `tool_uses`
- `tool_results`
- `decision_messages`
- `warning_messages`
- `raw_content`

The parser must understand real Claude session record shapes including:

- `user`
- `assistant`
- `system`
- `permission-mode`
- `file-history-snapshot`
- `attachment`
- `queue-operation`

The parser must extract meaningful assistant content block types including:

- `text`
- `tool_use`
- `thinking` as metadata only, not monitor content by default

The parser must extract meaningful user-side tool result content including:

- normal tool results
- error tool results
- tool result payloads that carry filenames, content, or structured metadata

The parser must also recognize decision or warning-style records from:

- stop hook summaries
- permission or hook error messages
- queue/interruption system messages

## Render Contract

Two renders are derived from the same canonical parsed event.

### Trace render

The trace render is durable and structured.

It must preserve:

- timestamp
- session and source identity
- ids and parent ids
- record type and subtype
- tool/action fields
- decision or warning fields
- enough content to reconstruct what happened later

The trace render is not a high-frequency refresh log and must not emit duplicate unchanged state snapshots.

### Monitor render

The monitor render is a noise-stripped text render, not a lossy summary.

It must keep:

- user prompts
- assistant text
- tool use
- code blocks
- decision messages
- warning messages

It should strip or suppress:

- opaque IDs when they do not help the human monitor
- timestamps unless needed for meaning
- empty thinking blocks
- file-history snapshots
- repetitive queue bookkeeping that adds no human signal

## Routing Contract

Routing happens after parsing and rendering, not before.

Primary source policy:

- `gate-ralph` live stream is primary
- reviewer outputs are secondary
- reviewer outputs become monitor-visible when Ralph is idle or when the event is itself a review-significant decision

Output routing rules:

- v1 sends to one monitor target
- route model must already be fan-out capable so multiple monitor recipients can be added later without redesign
- routing must choose recipients from one output list, not hardcoded single-target logic buried inside renderer code

## Durable Trace Logging

The durable monitor trace is a single structured log sink for this pipeline.

- one useful record per parsed event
- stable JSON-lines format
- no giant payload dumping when the same signal can be represented cleanly
- no spammy repeated refresh-style records for unchanged state
- optional size-based rotation is allowed if retention is bounded and deterministic

This durable monitor trace is separate from low-level hook decision tracing so the event pipeline can stay coherent and human-usable.

## Integration Boundaries

This session may update monitor/logging integration only.

Allowed:

- monitor/logging scripts
- monitor/logging hooks
- focused hook wiring changes needed to activate the pipeline
- tests and docs for the pipeline

Not allowed in this contract:

- launcher redesign
- dispatcher architecture redesign outside monitor/logging flow
- unrelated hook refactors

## Non-Negotiables

- one consolidated event pipeline
- one canonical parse per event
- no lossy monitor summarization by default
- monitor render and trace render come from the same parsed event flow
- partial last-line writes are handled safely
- checkpoint advancement is exact
- current working behavior outside the monitor/logging path is preserved
