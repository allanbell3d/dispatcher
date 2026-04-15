---
name: No restart needed for settings
description: Claude Code reloads settings.json and hooks dynamically — never suggest restarting sessions
type: feedback
---

Settings.json, settings.local.json, and hook scripts all reload on the fly. Never suggest restarting a session for config/hook changes to take effect.

**Why:** Allan has confirmed this repeatedly. Restarts waste time.

**How to apply:** After editing any settings or hook file, just test immediately. Don't say "restart to pick up changes."
