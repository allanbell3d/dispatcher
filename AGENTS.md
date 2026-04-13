# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Telegram bot that automates posting room rental ads on Dubizzle (Dubai). Allan sends voice/text commands via Telegram, the bot classifies intent, fills the Dubizzle form via Playwright, and handles the full posting lifecycle with human-in-the-loop approval checkpoints.

Two villas (60 and 62), 22 rooms total. Templates live in `adverts/`, photos in `Pictures/`, bot code in `service/`.

## Commands

```bash
# Install dependencies (from service/)
cd service && pip install -r requirements.txt

# Install Playwright browsers (first time only)
playwright install chromium

# Run the bot
cd service && python bot.py

# Optional: install stealth plugin
pip install playwright-stealth
```

No test suite exists. No linter configured. No build step.

## Architecture — What Requires Multi-File Understanding

### Intent Flow: Two Layers

`ai_provider.py:_regex_classify()` catches trivial commands (`?`, `help`, `hi`) instantly with zero cost. Everything else goes to `classify_intent()` which calls the AI with `prompts/intent_classifier.md` as the system prompt. The AI returns JSON: `{"intent": str, "rooms": ["01"], "params": {}}`. The bot dispatches to the matching handler function registered in `handlers.py:register_all()`.

### Threading Model for Posting

The main thread long-polls Telegram (`bot.py:run()`). When a post command arrives, `handlers.py:_run_posting_async()` spawns a **daemon thread** with its own asyncio event loop to run Playwright. The posting thread communicates with Allan through a bridge:

- **Posting thread** calls `bot.wait_for_reply(chat_id)` which blocks on a `threading.Event`
- **Main poll thread** detects `chat_id in self._reply_waiters` and feeds the reply text, setting the event
- This means **during a posting flow, Allan's next message is consumed as a checkpoint reply**, not as a new command

After payment, a second layer: `_poll_approval_background()` runs as an asyncio Task inside the posting thread, polling Dubizzle's My Ads page for the ad to go live. This doesn't block the next room in a batch.

### Config Dependency Chain

Every module imports `config.py`. Two JSON files drive everything:

- **`config.json`** — credentials, paths, AI provider, trigger config. The `paths` section uses `base_dir` as root, everything else is relative to it.
- **`rooms.json`** — per-room metadata (villa, bathroom, balcony, features) + `form_defaults` (values filled into every Dubizzle form) + `photo_paths` (where to find Selected/ folders)

`config.py:resolve_path(key)` = `base_dir / config.paths[key]`. All photo lookups go through `config.py:photo_dirs(room)` which builds paths from `rooms.json:photo_paths`.

### Ad File Lifecycle

Template (`yyyy-mm-dd_room-XX_*.md`) → dated copy (`2026-04-04_room-XX_*.md`) → optionally revised (`*_rev_allan.md`). `ad_manager.py:find_ad_file()` picks the most recent dated file, falling back to template. The bot **never modifies templates** — always creates dated copies first.

Ad files are parsed by looking for `**Title:**`, `**Price:**`, `**Room:**`, `**Villa:**` lines, and the description is everything after the first `\n---\n`.

### Notification Dual-Channel

`notifications.py:Notifier` sends to Telegram (bidirectional, primary) and WhatsApp via CallMeBot (send-only, backup for when Allan is in UAE or Spain). `notify_all()` fires both. Most handlers use `reply()` which is Telegram-only.

### AI Provider Swapping

`config.json:ai.provider` controls which backend is used. Options: `claude_cli` (uses Claude Code CLI via subprocess — no API key needed, uses subscription), `anthropic` (API key), `openai`/`deepseek`/`qwen` (OpenAI-compatible). The API key is read from the env var named in `config.json:ai.api_key_env` — never stored in config directly.

## Tunable Variables in rooms.json

| Variable | Location | Effect |
|----------|----------|--------|
| `form_defaults.security_deposit` | `rooms.json` | Dubizzle deposit field value |
| `form_defaults.number_of_tenants` | `rooms.json` | Max tenants shown on listing |
| `form_defaults.nationality` | `rooms.json` | Nationality preference on Dubizzle |
| `form_defaults.amenities` | `rooms.json` | Checkboxes ticked on Dubizzle form |
| `form_defaults.neighbourhoods` | `rooms.json` | Rotation pool for area field |
| `rooms.{id}.bathroom` | `rooms.json` | "ensuite" or "shared" — sets Dubizzle field |
| `rooms.{id}.balcony` | `rooms.json` | true/false — sets Dubizzle field |
| `rooms.{id}.features` | `rooms.json` | Room-specific features (e.g. private_entrance) |
| `photo_paths.villa_{n}` | `rooms.json` | Where to find room/outdoor/living Selected/ folders |

## Tunable Variables in config.json

| Variable | Effect |
|----------|--------|
| `telegram.poll_timeout_seconds` | Long-poll duration (default 60s) |
| `ai.provider` | AI backend: `claude_cli`, `anthropic`, `openai`, `deepseek`, `qwen` |
| `ai.model` | Model name passed to provider |
| `ai.max_tokens` | Default max response tokens |
| `ai.cli_timeout` | Subprocess timeout for `claude -p` calls (default 30s) |
| `paths.*` | All file locations (relative to `base_dir`) |
| `paths.session_file` | Dubizzle browser session file (default `dubizzle_session.json`) |
| `stt.engine` | `whisper_local` (NAS queue) or disabled |
| `stt.whisper_queue_path` | Explicit NAS Whisper queue path |
| `dubizzle.urls.post` | Dubizzle Place an Ad URL |
| `dubizzle.urls.my_ads` | Dubizzle My Ads URL |
| `dubizzle.max_photos` | Upload limit per ad (default 10) |
| `dubizzle.max_revisions` | Max revision rounds at M1 checkpoint (default 5) |
| `dubizzle.viewport` | Browser viewport `{width, height}` (default 1440x1200) |
| `dubizzle.locale` | Browser locale (default `en-US`) |
| `dubizzle.timezone` | Browser timezone (default `Asia/Dubai`) |
| `dubizzle.timeouts.page_load` | Playwright page load timeout ms (default 30000) |
| `dubizzle.timeouts.upload_wait` | Wait after photo upload ms (default 15000) |
| `dubizzle.timeouts.field_delay` | Delay between form fills ms (default 500) |
| `dubizzle.timeouts.approval_poll` | Poll interval for ad approval seconds (default 30) |
| `dubizzle.timeouts.approval_max_wait` | Max wait for ad approval seconds (default 1200) |
| `dubizzle.timeouts.checkpoint_reply` | Max wait for Allan's checkpoint reply seconds (default 600) |

## Rules — Non-Negotiable

- **Never post without Allan's explicit Telegram approval** (M1 review checkpoint)
- **Never pay without Allan's explicit Telegram approval** (M3 payment checkpoint)
- **Only process messages from `allowed_chat_ids`** (config.json)
- **Never overwrite `yyyy-mm-dd_` template files** — always create dated copies
- **Alternate neighbourhood** between Umm Suqeim 1 and Jumeirah 3 across ads
- **Read payment info FROM THE SCREEN**, never from local files

## Key File Locations

| What | Path |
|------|------|
| Bot entry point | `service/bot.py` |
| Intent handlers | `service/handlers.py` |
| Dubizzle automation | `service/dubizzle.py` |
| AI prompts | `service/prompts/*.md` |
| Room metadata | `service/rooms.json` |
| Credentials & paths | `service/config.json` |
| Ad templates | `adverts/yyyy-mm-dd_room-XX_*.md` |
| Posting queue | `posting_queue.md` |
| Interface contracts | `service/contracts.md` |
| Feature roadmap | `rev_02/feature_checklist.md` |
| Posting flow spec | `service/prompts/posting_flow.md` |
| Dubizzle UI reference | `service/prompts/dubizzle-posting/dubizzle-ui.md` |

## Stubs (Not Yet Implemented)

These handlers exist in `handlers.py` but return placeholder messages:
- `handle_refresh_ad` — needs Playwright to update live ad text
- `handle_repost` — needs Playwright to create new ad from expired
- `handle_deactivate` — needs Playwright to remove live ad
- `handle_view_link` — needs link tracking (Dubizzle URLs not stored)
