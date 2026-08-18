# 🗺️ ContextMap

<div align="center">

**Narrative Mental Map of Projects for AI Agents**

[![English Version](https://img.shields.io/badge/Read_in-English_🇬🇧-0052CC?style=for-the-badge&logo=googletranslate&logoColor=white)](README_EN.md)
[![Versión en Español](https://img.shields.io/badge/Versión_en-Español_🇪🇸-D00000?style=for-the-badge&logo=googletranslate&logoColor=white)](README.md)

*Capture the soul of your project, establish automated governance, and keep living context available for any AI Agent (`Antigravity`, `Cursor`, `Claude Code`, `Hermes`, `Copilot`, `Windsurf`, `Gemini`).*

[![Release](https://img.shields.io/badge/version-v2.1.0-blue.svg?style=for-the-badge)](https://github.com/kudawasama/ContextMap)
[![PyPI](https://img.shields.io/pypi/v/context-map-ai.svg?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/context-map-ai/)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Readiness](https://img.shields.io/badge/Readiness-100%2F100-brightgreen.svg?style=for-the-badge)](file:///.context-map/CONTEXT.md)
[![MCP Powered](https://img.shields.io/badge/MCP-11%20Tools-purple.svg?style=for-the-badge)](https://modelcontextprotocol.io/)

[🚀 Quick Start](#-10-second-quick-start) • [✨ Key Features](#-key-features) • [🤖 Autonomous Self-Maintenance](#-autonomous-self-maintenance-v190) • [⚖️ Comparison](#️-functional-comparison-contextmap-vs-top-market-tools) • [📜 Release History](#-release-history) • [💻 CLI Reference](#-complete-cli-commands)

</div>

> 🇪🇸 **¿Hablante de Español?** Haz clic en la insignia **`Versión en Español 🇪🇸`** arriba o lee la documentación completa en Español en 👉 [**README.md**](README.md).

---

## 💡 What is ContextMap and why does it exist?

When working with AI Agents in your IDE (`Antigravity`, `Cursor`, `Claude Code`, `Copilot`, etc.), AI often forgets past decisions, ignores strict architecture constraints, or proposes blind refactors that break the system.

**ContextMap solves this by creating a living memory for your project:**
It builds an interconnected **Obsidian Vault** ([Strict Tree Graph View](file:///.context-map/vault-ContextMap/)) and an AI Executive Brief ([`CONTEXT.md`](file:///.context-map/CONTEXT.md)) that teach any AI Agent:
- **Why does the project exist?** (Purpose, business, and identity).
- **What risks does it face?** (Static complexity, code alerts, and sensitive zones).
- **What is implemented vs. pending?** (Deduplicated graph of ideas, bases, and changes).
- **What architecture decisions were made?** (Living memory of past conversations and commit histories).

> 🚫 **ContextMap is not just a passive doc generator.** It is an active system for **Agentic Governance**, **Permanent Memory**, **Readiness Assessment**, and **Autonomous Self-Maintenance**.

---

## ⚡ 10-Second Quick Start

### 1. Global Installation (via `pip` or `uv`)

```bash
# Option 1: Official PyPI Package (Recommended via pip)
pip install context-map-ai

# Option 2: Global isolated tool via uv
uv tool install context-map-ai

# Option 3: Direct from GitHub repository
uv tool install git+https://github.com/kudawasama/ContextMap.git
```

### 2. Contextualize a Project

In any chat with your AI Agent inside your IDE, simply tell it:

> 💬 **"Initialize ContextMap for this project"**

Or run it directly from your terminal:

```bash
# Full automated 1-step setup:
ctxmap auto .

# Daily workflow: keep context updated after making changes:
ctxmap refresh .
```

---

## ✨ Key Features

### 🧠 1. Narrative Context with Soul
Every note in the Obsidian Vault is automatically enriched with narrative structure based on its semantic role:
* 💡 **IDEAS**: Origin, architectural rationale, and a **Pros & Cons** decision matrix.
* ⚠️ **RISKS**: Code location, severity level, impact of ignoring it, and **Mitigation Strategy**.
* 🔧 **CHANGES & FIXES**: Rationale, affected components, and **Non-Regression Verification**.
* 📦 **BASE**: Structural role in the architecture and key integrations.
* 🧪 **TESTS**: Acceptance criteria and verified `pytest` commands.
* 📄 **DOCUMENTS**: Extractive ingestion of PDFs, Markdown, and text files with cited references.

### 🤖 2. Autonomous Self-Maintenance (v1.9.0)
* 🏥 **Self-Healing (`ctxmap doctor --fix`)**: Automatically diagnoses and repairs vault inconsistencies, project name fragmentation, and metadata without losing manual notes.
* 👀 **Watcher Daemon (`ctxmap watch .`)**: Background process monitoring file events (`.py`, `.md`, `.json`, etc.) with debouncing (500ms) for real-time incremental updates.
* ⚓ **Transparent Git Hooks (`ctxmap hook install`)**: Automatically injects `pre-commit` and `post-commit` scripts to keep code and context synchronized on every commit.

### 🔌 3. Native MCP Server (11 Tools stdio)
Exposes **11 native MCP tools** via stdio (`ctxmap mcp`) for compatible agents like **Hermes Agent**, **Claude Desktop**, or **Cursor** to execute `refresh`, `scan`, `build`, `check`, `doctor`, or `install_hooks` directly without shell access:

```bash
# Connect to Hermes Agent:
hermes mcp add ctxmap --command ctxmap --args mcp
```

### 🛡️ 4. Protected Living Memory (`7.0-MANUAL/` & `8.0-KNOWLEDGE/`)
* **`7.0-MANUAL/`**: Stores session notes, daily journals (`Diario/YYYY-MM-DD.md`), and user agreements. The build engine **never deletes them** (`preserve: true`).
* **`8.0-KNOWLEDGE/`**: Reusable actionable lessons documented by AI: Lesson · Solution · Specific Prompt · Previous Instruction · Connections.

### 📦 5. Personal Consolidated Multi-Project Database (`ctxmap personal`)
Consolidates all events, lessons, and decisions across **all** your local projects into a single portable **SQLite + FTS5** database (`~/.context-map/personal/personal.db`):

```bash
ctxmap personal sync --todos      # Synchronizes all local repositories
ctxmap personal query "terms"     # Ultra-fast full-text search (low token usage)
```

---

## 🏛️ Multi-IDE Governance

ContextMap generates and injects stack-specific rules adapted for over 10 AI development tools:

| Agent / IDE | Generated Rules File |
| :--- | :--- |
| **Universal Standard** | [`AGENTS.md`](file:///AGENTS.md) |
| **Claude Code** | `CLAUDE.md` |
| **Cursor** | `.cursor/rules/contextmap.mdc` & `.cursorrules` |
| **Windsurf** | `.windsurfrules` |
| **GitHub Copilot** | `.github/copilot-instructions.md` |
| **Gemini CLI** | `GEMINI.md` |
| **Hermes Agent** | `.hermes/config.yaml` + Workflows |
| **Cline & Roo Code** | `.clinerules` / `.roo/rules/contextmap.md` |
| **OpenCode & Aider** | `opencode.json` / `.aider.conf.yml` |

---

## ⚖️ Functional Comparison: ContextMap vs. Top Market Tools

In the AI developer tooling ecosystem (2026), there are 4 main approaches for providing context to LLMs. The table below compares **ContextMap** with the most popular web and CLI tools:

| Feature / Capability | CLI Packagers (`Repomix`) | Web Ingestors (`Gitingest`) | Repo Maps (`Aider`) | IDE Indexers (`Cursor` / `Windsurf`) | **ContextMap v1.9.0** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Primary Focus** | Dump repo to XML/MD file | GitHub URL to prompt | AST map + PageRank | Local Vector RAG | **Governance + Living Memory + Vault + Self-Maintenance** |
| **Token Consumption** | 🔴 Massive (entire file) | 🔴 Massive | 🟢 Efficient | 🟡 Medium | 🟢 **Ultra-efficient (`CONTEXT.md` / MCP)** |
| **Interactive Visual Vault (Obsidian Vault)** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Yes (Strict Tree Graph, Canvas, Dataview)** |
| **Captures Rationale & Intent ("Soul")** | ❌ No (code only) | ❌ No | ❌ No (signatures only) | ❌ No | **✅ Yes (Polymorphic narrative notes)** |
| **Multi-IDE Governance (`AGENTS.md` + 10 IDEs)** | ❌ No | ❌ No | ❌ No | 🟡 Own IDE only | **✅ Yes (Portable across 10+ IDEs)** |
| **Protected Living Memory (`7.0-MANUAL/`)** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Yes (`preserve: true`, never deleted)** |
| **Agent Knowledge Store (`8.0-KNOWLEDGE/`)** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Yes (Actionable lessons format)** |
| **Native MCP Server (stdio)** | ❌ No | ❌ No | ❌ No | 🟡 Proprietary | **✅ Yes (`ctxmap mcp`, 11 stdio Tools)** |
| **Personal Multi-Project DB** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Yes (SQLite + FTS5 portable)** |
| **System Readiness Index (Score 0-100)** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Yes (`ctxmap check .`)** |
| **Exact Token Counter per Model** | ✅ Yes (`tiktoken`) | 🟡 Approximate | ❌ No | 🟡 Internal | **✅ Yes (`tiktoken` + fallback)** |
| **Preventive Secrets & Credentials Scanner** | ✅ Yes | ❌ No | ❌ No | ❌ No | **✅ Yes (`security.py`)** |
| **Portable Context Export (XML/JSON/MD)** | ✅ Yes | ✅ Yes | ❌ No | ❌ No | **✅ Yes (`ctxmap export`)** |
| **Active Watcher Daemon** | ❌ No | ❌ No | ❌ No | ✅ Yes (Background) | **✅ Yes (`ctxmap watch .`)** |
| **Vault Self-Healing & Auto-Repair** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Yes (`ctxmap doctor --fix`)** |
| **Transparent Git Hooks Installer** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Yes (`ctxmap hook install`)** |

---

## 📜 Release History

To view the complete version history, release notes, and changelog from v1.0.0 to **v1.9.0**, please visit the [**CHANGELOG.md**](CHANGELOG.md) file.

---

## 💻 Complete CLI Commands

```bash
# 🚀 Daily workflow (recommended): keep context updated in 1 step
ctxmap refresh .                      # scan + build (preserving manual notes) + check

# 👀 Background monitoring daemon
ctxmap watch .                        # Real-time event listener daemon

# 🏥 Diagnosis & Self-Healing
ctxmap doctor . --fix                 # Diagnoses and auto-repairs project and vault

# ⚓ Git Hooks setup
ctxmap hook install                   # Injects transparent pre-commit & post-commit hooks

# 🔄 Work session closing
ctxmap wrap                           # refresh + summary of logged living memory

# 📦 Portable Context Exporter (Repomix compatible)
ctxmap export . --format xml          # Exports flat context XML, JSON, or Markdown

# 🤖 MCP Server
ctxmap mcp                            # Runs stdio MCP server

# 📦 Personal Multi-Project Database
ctxmap personal sync --todos          # Synchronizes all local repos
ctxmap personal query "terms"         # Full-text search across your project history

# 🛠️ Build & Scan
ctxmap auto .                         # Full scan + git import + build
ctxmap build                          # Rebuilds Obsidian Vault
ctxmap build --brief                  # Generates CONTEXT.md and AGENTS.md
ctxmap check .                        # Audits Readiness Score (0-100)
```

---

## 🛡️ Badge for your Project

If you use ContextMap for context governance in your repository, feel free to add our official badge to your `README.md`:

```markdown
[![ContextMap Verified](https://img.shields.io/badge/ContextMap-100%2F100_Ready-blue?style=for-the-badge&logo=obsidian)](https://github.com/kudawasama/ContextMap)
```

---

## 📄 License

MIT © [kudawasama](https://github.com/kudawasama)

