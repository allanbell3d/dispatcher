#!/bin/bash
# Orchestration Sprint Launcher
# Creates a tmux session with one panel per agent.
# Each panel gets the orchestration MCP server registered for its role.
#
# Usage: bash launch.sh <worktree_path> [gate_subdir]
# Example: bash launch.sh ".worktrees/v2-refactor-phase-d" gate
#
# Prerequisites:
# - tmux, bun, claude CLI installed
# - gate/ directory set up with config.json + tasks.json
# - D:/IA/orchestration/mcp-server/ with dependencies installed

set -e

WORKTREE="${1:-.}"
GATE_SUBDIR="${2:-gate}"
GATE_DIR="$WORKTREE/$GATE_SUBDIR"
MCP_SERVER="D:/IA/orchestration/mcp-server/server.ts"
SESSION="sprint"

if [ ! -f "$GATE_DIR/config.json" ]; then
  echo "ERROR: $GATE_DIR/config.json not found."
  exit 1
fi

if [ ! -f "$MCP_SERVER" ]; then
  echo "ERROR: MCP server not found at $MCP_SERVER"
  echo "Run: cd D:/IA/orchestration/mcp-server && bun install"
  exit 1
fi

# Resolve absolute paths
ABS_WORKTREE=$(cd "$WORKTREE" && pwd)
ABS_GATE=$(cd "$GATE_DIR" && pwd)

# Ensure mailbox + task files exist
mkdir -p "$GATE_DIR/mailbox" "$GATE_DIR/approvals" "$GATE_DIR/diffs"
for agent in architect critic ralph playwright monitor allan; do
  touch "$GATE_DIR/mailbox/$agent.md"
done

# Set first task as current if not already set
if [ ! -f "$GATE_DIR/current_task.json" ] && [ -f "$GATE_DIR/tasks.json" ]; then
  python3 -c "
import json
with open('$GATE_DIR/tasks.json') as f:
    tasks = json.load(f)
first = next((t for t in tasks if t['status'] == 'pending'), None)
if first:
    first['status'] = 'in_progress'
    with open('$GATE_DIR/current_task.json', 'w') as f:
        json.dump(first, f, indent=2)
    for t in tasks:
        if t['id'] == first['id']:
            t['status'] = 'in_progress'
    with open('$GATE_DIR/tasks.json', 'w') as f:
        json.dump(tasks, f, indent=2)
    print(f'First task: {first[\"id\"]} — {first[\"title\"]}')
"
fi

echo "=== Orchestration Sprint Launcher ==="
echo "Worktree: $ABS_WORKTREE"
echo "Gate:     $ABS_GATE"
echo "MCP:      $MCP_SERVER"
echo ""

# Register MCP server for each agent
# This adds the orchestration server to the agent's session
register_mcp() {
  local agent=$1
  echo "Registering MCP server for $agent..."
  # claude mcp add registers to the project or user level
  claude mcp add "orchestration-${agent}" \
    --command "bun" \
    --args "$MCP_SERVER" \
    --env "AGENT_NAME=${agent}" \
    --env "GATE_DIR=${ABS_GATE}" \
    --scope project 2>/dev/null || echo "  (may already exist)"
}

for agent in architect critic ralph playwright monitor; do
  register_mcp "$agent"
done

echo ""
echo "Creating tmux session '$SESSION' with 5 panels..."

# Create tmux session
tmux new-session -d -s "$SESSION" -c "$ABS_WORKTREE"
tmux rename-window -t "$SESSION" "sprint"

# Panel 0: Architect (top-left)
tmux send-keys -t "$SESSION" "echo '=== ARCHITECT (Opus) ===' && echo 'Run: claude' && echo 'Then paste architect prompt'" Enter

# Panel 1: Critic (top-right)
tmux split-window -h -t "$SESSION" -c "$ABS_WORKTREE"
tmux send-keys -t "$SESSION" "echo '=== CRITIC (Opus) ===' && echo 'Run: claude' && echo 'Then paste critic prompt'" Enter

# Panel 2: Ralph (middle-left)
tmux split-window -v -t "$SESSION:0.0" -c "$ABS_WORKTREE"
tmux send-keys -t "$SESSION" "echo '=== RALPH (Sonnet) ===' && echo 'Run: claude' && echo 'Then paste ralph prompt'" Enter

# Panel 3: Playwright (middle-right)
tmux split-window -v -t "$SESSION:0.1" -c "$ABS_WORKTREE"
tmux send-keys -t "$SESSION" "echo '=== PLAYWRIGHT (Sonnet) ===' && echo 'Run: claude' && echo 'Then paste playwright prompt'" Enter

# Panel 4: Monitor (bottom)
tmux split-window -v -t "$SESSION:0.2" -c "$ABS_WORKTREE"
tmux send-keys -t "$SESSION" "echo '=== MONITOR (Opus) ===' && echo 'Run: claude' && echo 'Then paste monitor prompt'" Enter

tmux select-layout -t "$SESSION" tiled

echo ""
echo "Done! Attach with: tmux attach -t $SESSION"
echo ""
echo "Panel layout:"
echo "  0: Architect    1: Critic"
echo "  2: Ralph        3: Playwright"
echo "  4: Monitor"
echo ""
echo "In each panel:"
echo "  1. Run 'claude' to start a session"
echo "  2. Paste the rendered prompt from gate/prompts/"
echo "  3. Architect/Critic/Monitor: will load specs then Sleep"
echo "  4. Ralph: will start fixing the first bug"
