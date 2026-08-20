<p align="center">
  <a href="README.zh-CN.md">简体中文</a> · <strong>English</strong>
</p>

<div align="center">
  <img src="icon.svg" width="152" alt="Blindspot Relay signal icon">
  <h1>BLINDSPOT RELAY</h1>
  <p><strong>You see the system. He sees the room. Neither of you can escape alone.</strong></p>
  <p>A single-player AI conversation thriller about trust, incomplete information, and one damaged relay.</p>
</div>

[![Blindspot Relay gameplay trailer](assets/branding/blindspot-gameplay-preview.gif)](assets/branding/blindspot-gameplay-trailer.mp4)

<p align="center">
  <a href="assets/branding/blindspot-gameplay-trailer.mp4"><strong>▶ Watch / download the gameplay trailer</strong></a>
</p>

<p align="center">
  <a href="https://blindspot-relay.onrender.com"><strong>▶ PLAY IN BROWSER</strong></a>
  &nbsp; · &nbsp;
  <a href="https://github.com/OneYaYa/BlindSpot/releases"><strong>⬇ WINDOWS DEMO / RELEASES</strong></a>
</p>

## One Screen. Two Truths.

K-17 is failing. You are the remote dispatcher with access to damaged facility telemetry. Lin Lan, an injured maintenance technician trapped behind sealed bulkheads, can only report what is directly in front of him.

Your records are incomplete. His labels are burned away. Talk across the blind spot, compare both sides of the evidence, and decide which risks another human being should take.

This is not a chatbot sitting beside a puzzle. Conversation is the puzzle.

## What You Say Survives the Run

Lin Lan remembers more than your name. Reassurance, deception, reckless orders, careful repairs, promises, and costly mistakes become structured events that can change his trust, his willingness to act, and what he says after the escape.

Five personal memories surface in different rooms. A clean rescue preserves the accident evidence and reopens the investigation. An emergency escape may save a life while destroying the proof. Failure leaves only the carrier signal.

## The AI Can Speak. It Cannot Rewrite Reality.

- **Natural conversation** — ask about injuries, surroundings, memories, fears, or the next step in your own words.
- **Information asymmetry** — the dispatcher and technician hold different halves of every critical clue.
- **Player authorization** — the AI can propose one locally valid action; it cannot execute anything without you.
- **Deterministic consequences** — Godot owns rooms, resources, puzzles, trust, mistakes, and endings.
- **No-key fallback** — the complete incident remains playable through local character rules when the online model is unavailable.
- **Replayable evidence** — cable readings, pressure calibration, routes, and the accident signature change between runs.

## Five Rooms. One Voice in the Dark.

1. Acquire the damaged relay and establish contact.
2. Recover dispatcher-only telemetry without leaking it to Lin Lan.
3. Cross-check burned cable labels against remote electrical records.
4. Reconstruct the coolant pressure sequence from two incomplete viewpoints.
5. Choose a full repair or an emergency bypass, then live with the evidence you saved—or destroyed.

Every room has its own visual landmark and radio layer. Lin Lan shifts between neutral, listening, injured, and relieved performances as oxygen, trust, actions, and the ending change.

## Play the Demo

### Browser — play instantly, no API key required

Play the current Godot build at **[blindspot-relay.onrender.com](https://blindspot-relay.onrender.com)**. The game, authoritative simulation, and AI NPC all run through one same-origin Render service. The provider credential remains server-side and is never shipped to the browser. No download, account, Godot installation, or personal API key is required.

The Web build uses a browser-safe single-thread export and bundled Chinese font. Runtime-generated radio audio is currently disabled on Web for compatibility; use the Windows build for the complete audio presentation. A free Render instance may need a short cold start after inactivity.

### Windows — full local build

The public v0.5.2 Windows demo is available on [GitHub Releases](https://github.com/OneYaYa/BlindSpot/releases/tag/v0.5.2). Download `BlindspotRelay-Windows-v0.5.2.zip`, extract it, and run `BlindspotRelay.exe`. The package includes the Godot runtime and local relay, so players do not need Godot or Python. It contains no developer API key; local fallback keeps the entire mission playable. When no online provider is configured, the launcher opens a local-only setup page where players can add their own credential, encrypted for their Windows account with DPAPI. If a credential is already configured, the launcher confirms that online AI is enabled. The internal game executable now directs players back to the one-click launcher when opened by mistake.

See [Demo Distribution](docs/DEMO_DISTRIBUTION.md) for build, hosting, security, and compatibility details.

<details>
<summary><strong>Run from source</strong></summary>

Requires Godot 4.6 or newer.

```powershell
git clone https://github.com/OneYaYa/BlindSpot.git
cd BlindSpot
& "C:\path\to\Godot_v4.6.3-stable_win64_console.exe" --path .
```

The game automatically uses local NPC rules when the Python relay is not running. To test optional online dialogue, copy `.env.example` to `.env`, add a dedicated `OPENAI_API_KEY`, and run `python server.py` before launching Godot.

</details>

<details>
<summary><strong>Architecture and validation</strong></summary>

Blindspot uses a Godot 4.6 authoritative simulation, a least-privilege NPC context compiler, a local rule-based fallback, and an optional Python Responses API relay. Dispatcher telemetry and hidden puzzle answers are filtered before model calls. Every returned action is checked by Python, checked again by Godot, and held for player authorization.

Current regression baseline:

- Python: 37 tests
- Godot simulation: 254 checks
- Godot integration: 100 checks
- Chinese live AI experience set: 12 cases covering persona, grounding, leakage, action safety, repetition, latency, usage, failures, and fallback

Technical notes: [AI NPC Upgrade](docs/AI_NPC_TECH_UPGRADE.md) · [AI and Privacy](docs/AI_AND_PRIVACY.md) · [Release Checklist](docs/RELEASE_CHECKLIST.md)

</details>
