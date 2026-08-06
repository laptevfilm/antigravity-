# Workstation and Project Setup Profile — 2026-08-06

This document captures and preserves the current settings, hardware configuration, and active projects in the `D:\AI` directory on the user's workstation. It serves as a persistent technical reference for all future sessions and assistant workflows.

---

## 1. Workstation & System Specifications

* **Operating System**: Microsoft Windows 11 Pro (build 26200, 64-bit) / WSL Ubuntu 22.04 LTS
* **CPU**: 13th Gen Intel Core i5-13420H (8 cores / 12 logical processors)
* **RAM**: ~16 GB physical memory
* **GPU**:
  * **Discrete**: NVIDIA GeForce RTX 3050 Laptop GPU (6 GB VRAM, Driver `32.0.15.9159`)
  * **Integrated**: Intel UHD Graphics (Driver `31.0.101.4146`)
* **Display**: Internal 1920 × 1080 @ 144 Hz (Intel UHD interface)

---

## 2. Active Projects in `D:\AI`

### 📂 Project 1: `hermes-brain`
* **Purpose**: Durable, shared Markdown-based long-term memory vault between the remote Hermes Personal Assistant (VDS) and the local Codex assistant.
* **Repository**: Cloned from `https://github.com/laptevfilm/hermes-brain.git`
* **Local Path**: [hermes-brain](file:///D:/AI/hermes-brain)
* **Current Status**: Completely synchronized (`origin/main` at commit `6c76f6e`).
* **Core Rules**:
  * Check `INDEX.md`, `AGENT.md`, and `LOG.md` before starting non-trivial tasks.
  * Run `git pull --rebase` before modifying the memory.
  * Keep short summaries in `LOG.md` and detailed guidelines in the respective folders (`projects/`, `ops/`, `decisions/`).
  * **Strictly forbid** storing secrets, keys, or private credentials in this repository.

### 📂 Project 2: `airoom-hermes-vds-native-codex-kit`
* **Purpose**: A native (non-Docker) Ansible-like deployment bundle designed for Codex to install Hermes Personal Assistant on clean Ubuntu/Debian virtual servers.
* **Local Path**: [airoom-hermes-vds-native-codex-kit](file:///D:/AI/airoom-hermes-vds-native-codex-kit)
* **Target Environment**: Standard Ubuntu VDS, user `hermes`, native path `/home/hermes/.hermes/hermes-agent`, workspace at `/srv/hermes/workspace`.
* **Key Components**:
  * `scripts/local_deploy_via_ssh.sh`: Local deployment bootstrap script.
  * `remote/bootstrap_ubuntu_native.sh`: Native remote host provisioning script.
  * `CODEX_INSTALL_PROMPT.md` and `AGENTS.md`: Instruction templates for AI-driven deployment.

### 📂 Project 3: `kilo-free-llm-kit`
* **Purpose**: Concrete VS Code + Kilo Code configuration bundle optimized for utilizing free and free-tier cloud LLMs (OpenRouter, Gemini, Groq).
* **Repository**: Cloned from `https://github.com/laptevfilm/kilo-free-llm-kit.git`
* **Local Path**: [kilo-free-llm-kit](file:///D:/AI/kilo-free-llm-kit)
* **Active Config (`kilo.jsonc`)**:
  * **Ask / Chat**: Cheapest/free general model.
  * **Code / Refactor**: `openrouter/cohere/north-mini-code:free` (temp 0.2).
  * **Architect / Plan**: `openrouter/nvidia/nemotron-3-super-120b-a12b:free` (temp 0.2).
  * **Debug**: `openrouter/poolside/laguna-xs-2.1:free` (temp 0.15).

### 📂 Project 4: `iphone-vless-setup`
* **Purpose**: Security, configuration profiles, and research summaries for routing iPhone traffic safely through VLESS Reality and Hysteria2.
* **Local Path**: [iphone-vless-setup](file:///D:/AI/iphone-vless-setup)
* **Current State & Knowledge**:
  * Target Server: `89.40.70.42`
  * Active Protocols: VLESS Reality (`443/tcp`), Hysteria2 (`443/udp` - high speed on iPhone via Karing app), SOCKS5 (`50101/tcp` - fallback backup).
  * Key Findings: Yandex speedtest requires custom direct rules; Karing app does not guarantee stable split-tunneling (ru-split) via imported YAML profiles, requiring manual app-level verification rather than simple browser-based checks.

### 📂 Project 5: `braw_forensics` & `BRAW Recovery`
* **Purpose**: Advanced, low-level binary diagnostics and forensic repair of partially unfinalized or corrupted Blackmagic RAW (BRAW) video clips directly from CFast card images.
* **Local Paths**: [braw_forensics](file:///D:/AI/braw_forensics) and [BRAW Recovery](file:///D:/AI/BRAW%20Recovery) (also referenced as [braw-recovery-tool](file:///D:/AI/braw-recovery-tool))
* **Core Repair Strategy**:
  1. Work **read-only** against `.img` card files; never write directly to the image.
  2. Parse the ISO Base Media File Format (BMFF) / QuickTime Atoms (`mdat`, `moov`, sample tables).
  3. Search for physical, unindexed frame payloads (starting with `bmdf` / containing `braw` signature) beyond the indexed end of the clip.
  4. Manually patch standard container index tables: sample sizes (`stsz`), offsets (`co64`), durations (`stts`, `tkhd`, `mdhd`), and edit lists (`edts/elst`).
  5. Validate using independent table parsers and verify in DaVinci Resolve or Blackmagic RAW Player.
  6. Successfully proven cases: F004 C007 (+125 frames, +5.00s) and C022 C009 (+24 frames, +0.96s).

### 📂 Project 6: `sglang-local`
* **Purpose**: High-performance local LLM execution engine SGLang setup within WSL Ubuntu.
* **Local Path**: [sglang-local](file:///D:/AI/sglang-local)
* **Architecture**:
  * Because Windows native setup fails due to missing `sglang-kernel` wheel compilation targets, SGLang is deployed inside WSL Ubuntu.
  * Runs small local models (e.g. Qwen) using the laptop's RTX 3050 discrete GPU.
  * API endpoint exposed locally to Windows at `http://localhost:30000/v1`.

### 📂 Project 7: `Tools`
* **Purpose**: Local portable runtime components and developer tools mapped to the sandbox environment.
* **Local Path**: [Tools](file:///D:/AI/Tools)
* **Components**: FFmpeg, portable Python (3.12.10), and portable PowerShell (7.6.3).

---

## 3. Long-Term Memory Event Log (Recent Highlights)

The latest entries in `LOG.md` (synchronized from GitHub up to 2026-08-05) show:
* **2026-07-29**: Kilo Code free LLM kit initialized, pushed to `laptevfilm/kilo-free-llm-kit`.
* **2026-07-31 / 2026-08-01**: Updates to GitHub CLI (`gh 2.97.0`) and preparation for Hermes Agent patches.
* **2026-08-02**: Local `gh` updated to security release `2.97.0`. Context7 client updated to `0.5.7` to prevent false bearer-token OAuth invalidations.
* **2026-08-03**: Warning issued that `gpt-5.4` and `gpt-5.4-mini` will be deprecated in OpenAI Codex on **2026-08-31**. Recommendation to migrate defaults/scheduled crons to `gpt-5.6-terra` or `gpt-5.6-luna`.
* **2026-08-04 / 2026-08-05**: Major release `v0.20.0 / v2026.8.3` of Hermes Agent successfully deployed on the VDS. Verification checks completed. Next scheduled maintenance task: systemd gateway restart (`sudo hermes gateway restart --system`).

---

## 4. Current Workstation Status (As of Aug 6, 2026)

* **Git Workspace**: Fully clean, synced up-to-date with remote repositories.
* **Codex Interface**: Portable PowerShell 7.6.3 + Python 3.12.10 ready.
* **Local LLM Engine**: WSL SGLang pipeline and Ollama installation packages verified.
* **Unreal Engine Bridge**: Dedicated Unreal Engine 5.7.4 installation detected at `D:\UE_5.7`, utilizing PythonScriptPlugin and RemoteControl. A reverse SSH tunnel connects Hermes Gateway to the local editor.
