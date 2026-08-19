# Blindspot Relay

[简体中文](README.zh-CN.md) | **English**

Blindspot Relay is a single-player conversation-driven puzzle game. You are a remote dispatcher with access to the K-17 facility's global telemetry; the trapped technician can only confirm what he can see in his current room. Cross-check both sides of the relay, issue one-step instructions, authorize their execution, restore the power and cooling systems, and escape.

The project is deliberately scoped for solo development. It uses one transparent, chest-up pixel portrait of the male technician, while Godot draws the five room backgrounds, character animation, video-signal effects, and state feedback at runtime.

## Features

- One NPC, five rooms, eight action categories, and two resources: oxygen and power
- A single carrying slot, modular power-routing puzzle, coolant-pressure puzzle, and explicit confirmation for hazardous actions
- Three resource routes: a full repair with the phase fuse core, a costly emergency-cell bypass, or a portable oxygen reserve
- Standard success, costly success, and failure endings with instant mission restart
- Complete deterministic local dialogue rules, so the game remains fully playable offline
- Optional OpenAI-powered dialogue and action proposals
- Puzzle clues split between dispatcher-only telemetry and the NPC's local observations
- Natural-language commands produce at most one action candidate for player authorization
- A contextual `NEXT` panel, editable keyword chips, and broad quick-conversation prompts
- Room-specific remote video, a pixelated transition, and a skippable four-second relay-acquisition intro
- Visual feedback for breathing, injury, stress, low oxygen, communication, authorization, actions, and endings
- A least-privilege NPC context compiler with source IDs, prompt traces, relationship state, and deterministic post-generation validation
- Procedural radio ambience and event sounds
- Font size, audio, reduced-motion, online/offline AI, quick authorization, and narrow-screen settings

## Run the Game

Open `project.godot` with Godot 4.6 or later and run the main scene. From PowerShell:

```powershell
& "C:\path\to\Godot_v4.6.3-stable_win64_console.exe" --path .
```

Without the Python service, all text input is handled by the local NPC rules. The offline parser understands room names, colors, route items, and the I/B/P pressure-regulator aliases. Ambiguous requests are rejected instead of being guessed.

### Controls

- Mouse: choose quick prompts, send text, and authorize or reject an action candidate
- Keyword chips: insert facility, item, or connector names without sending the message
- `Enter`: send text; with an empty input and a safe candidate, authorize it
- `Ctrl+T`: focus the input field
- `Ctrl+R`: restart the mission after confirmation
- `SETTINGS`: adjust text, audio, motion, and AI mode

## Optional Online AI

The API key stays in a local Python process and is never embedded in the Godot client or committed to the repository.

```powershell
Copy-Item .env.example .env
# Add OPENAI_API_KEY to .env
python server.py
```

The client calls `http://127.0.0.1:8787/api/npc/decide` by default. The proxy uses the OpenAI Responses API, low reasoning effort, and a strict JSON Schema:

```text
reply / intent / action / target / mood / referenced_ids
```

Unknown actions, invalid targets, and stale candidates are downgraded or rejected by both Python and Godot. Network errors automatically fall back to the local rules. Conversation history is managed locally and API requests use `store: false`. See [AI and Privacy](docs/AI_AND_PRIVACY.md).

## Architecture

```text
Player text ──> online model / local dialogue rules
                       │
                       └──> NPC reply + at most one allowlisted candidate
                                                     │
                                              player authorization
                                                     │
                                                     v
                                      MissionSimulation.propose()
                                                     │
                                      deterministic state update
```

Before every model call, `NpcContextCompiler` packages six budgeted sections: character and scene, known beliefs, subjective memory, relationship, director intent, and recent dialogue. Dispatcher claims never become world facts without verification. The authoritative simulator always owns items, resources, puzzles, and endings.

Key files:

- `scripts/core/mission_simulation.gd`: authoritative state machine, relationships, resources, and endings
- `scripts/core/puzzles/`: power-routing and coolant-pressure puzzle modules
- `data/mission.json`: rooms, items, costs, and mission data
- `scripts/main.gd`: orchestration between simulation, UI, and NPC services
- `scripts/services/npc_decision_service.gd`: HTTP, allowlist filtering, and local fallback
- `scripts/services/npc_context_compiler.gd`: least-privilege context compilation and traces
- `scripts/services/procedural_audio.gd`: runtime radio ambience and event sounds
- `scripts/ui/mission_console_ui.gd`: code-driven terminal interface
- `scripts/ui/signal_boot_overlay.gd`: relay-acquisition intro
- `scripts/ui/npc_portrait.gd`: room renderer, transitions, and state animation
- `server.py`: local OpenAI proxy that keeps credentials out of the client

## Tests

```powershell
python -m unittest discover -s tests/python -v

$godot = "C:\path\to\Godot_v4.6.3-stable_win64_console.exe"
& $godot --headless --path . --editor --quit
& $godot --headless --path . res://tests/godot/mission_simulation_test.tscn
& $godot --headless --path . res://tests/godot/main_integration_test.tscn
```

The online service smoke test makes a real API request:

```powershell
& $godot --headless --path . res://tests/godot/online_service_test.tscn
```

## Mission Tips

Inspect the telemetry console first. For a full repair, take the phase fuse core to the main power room and combine its three local connector readings with the remote closed-loop values. The emergency cell offers a costly bypass. After power is restored, take the cryogenic sealant to the cooling corridor and combine the remote target pressure with Lin Lan's I/B/P regulator readings. Seal the leak, then reach the escape pod. Each restart generates new circuit readings, pressure calibration, and an accident signature.

## Windows Build

The release script packages the Godot runtime, compiled PCK, Python AI proxy, and process launcher into one ZIP:

```powershell
python -m pip install --user pyinstaller
& .\packaging\build_windows_release.ps1 -EmbedApiCredential
```

The archive is written to `build/releases/BlindspotRelay-Windows-v0.4.0.zip`. Embedded credentials are only suitable for limited private testing; public builds should use an authenticated hosted proxy with TLS, rate limits, and billing alerts. See `packaging/DISTRIBUTOR_SECURITY_NOTICE.md` and `docs/RELEASE_CHECKLIST.md`.
