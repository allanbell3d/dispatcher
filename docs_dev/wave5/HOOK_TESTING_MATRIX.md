# Hook Testing Matrix

| Hook | Trigger | Expected proof |
|---|---|---|
| `dispatch_gate.py` | gated write/edit/bash | trace entry in `decision_trace.log` and audit entry for working/halted/waiting state transitions |
| `inbox_access_guard.py` | read/grep/glob/bash | allow/deny trace entry |
| `check_gate.py` | `git commit` | allow/deny decision + active reviewer message |
| `activity_logger.py` | post-tool activity | `activity_<agent>.log` entry and trace entry; fallback mail only when `monitor_activity_to_dispatch=true` |
| `monitor_ingest.py` | coder post-tool activity | fresh JSON in `dispatch/gate-monitor/inbox/` and trace entry |
| `on_file_message.py` | inbox file write | file moved/processed without loss; wildcard runtime firing still needs one live interactive proof |
| `dispatch_next_bug.py` | successful commit | current task advancement |
| `stop_notify.py` | session stop | stop notification / trace |
