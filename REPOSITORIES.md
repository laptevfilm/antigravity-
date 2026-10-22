# Linked Repositories

This file links and maps the three repositories involved in the multi-agent personal assistant ecosystem.

## Repository Directory

- `laptevfilm/hermes-brain`
  - Durable Hermes memory vault.
  - Local path: `D:\AI\hermes-brain`
  - GitHub: `https://github.com/laptevfilm/hermes-brain`
- `laptevfilm/kilo-free-llm-kit`
  - Kilo Code + free OpenRouter LLM setup kit.
  - Local path: `D:\AI\kilo-free-llm-kit`
  - GitHub: `https://github.com/laptevfilm/kilo-free-llm-kit`
- `laptevfilm/antigravity-`
  - Antigravity agent workspace & code archive for local projects.
  - Local path: `D:\AI\Antigravity`
  - GitHub: `https://github.com/laptevfilm/antigravity-`
  - Contained projects & tools:
    - `projects/braw-recovery-tool/` — BRAW / HFS+ / BMFF video recovery package (`brawrec`), CLI, GUI, tests (mirrors `D:\AI\braw-recovery-tool`)
    - `projects/braw_forensics/` — 14 forensic analysis & carving scripts + runbooks (mirrors `D:\AI\braw_forensics`)
    - `projects/airoom-hermes-vds-native-codex-kit/` — Hermes VPS + VLESS/Hysteria2 deployment & routing kit (mirrors `D:\AI\airoom-hermes-vds-native-codex-kit`)
    - `projects/iphone-vless-setup/` & `projects/iphone-vless-current-context/` — iOS VLESS Reality setup guides
    - `tools/ZeroBrightnessOff/` — MacBook-style screen-off daemon below 0% brightness (`F5`)
    - `.agents/` — Unified agent operating protocol (`AGENTS.md`, `rules/`, `skills/`)

## Relationship and Collaboration

- **`hermes-brain`** stores the global durable context, rules, daily research digests, and chronological logs (`LOG.md`) shared by both the local Codex/ChatGPT and the remote VPS-bound Hermes assistant.
- **`kilo-free-llm-kit`** provides concrete VS Code and Kilo Code extension configuration templates for daily developer-centric work.
- **`antigravity-`** (This Repo) serves as the workspace and local runtime orchestration center of the Antigravity agent, coordinating with both Hermes and Codex.

Keep this file in all three repositories so that future sessions and different assistant instances can immediately discover the relationships and maintain complete awareness of the entire suite.
