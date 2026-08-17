# 🗺️ ContextMap

<div align="center">

**Narrative Mental Map of Software Projects for AI Agents**

*Capture your project's soul, establish automatic agent governance, and keep context alive for any AI Agent (`Antigravity`, `Cursor`, `Claude`, `Hermes`, `Copilot`, `Windsurf`, `Gemini`).*

[![Release](https://img.shields.io/badge/version-v1.8.0-blue.svg?style=for-the-badge)](https://github.com/kudawasama/ContextMap)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Readiness](https://img.shields.io/badge/Readiness-100%2F100-brightgreen.svg?style=for-the-badge)](.context-map/CONTEXT.md)
[![MCP Powered](https://img.shields.io/badge/MCP-9%20Tools-purple.svg?style=for-the-badge)](https://modelcontextprotocol.io/)

[ 🇪🇸 Versión en Español ](README.md) | [ 🇬🇧 English Version ](README_EN.md)

</div>

---

## 💡 What is ContextMap and Why Does It Exist?

When working with AI Agents in your IDE (`Antigravity`, `Cursor`, `Claude Code`, `Copilot`, etc.), the AI frequently forgets past architectural decisions, ignores non-negotiable project rules, or proposes blind refactorings that break the system.

**ContextMap solves this by creating a living memory for your project:**
It builds an interconnected **Obsidian Vault** ([Strict Tree Graph View](.context-map/vault-ContextMap/)) and an Executive Brief ([`CONTEXT.md`](.context-map/CONTEXT.md)) that teach any AI Agent:
- **Why does the project exist?** (Purpose, business goals, and scope limits).
- **What risks does it face?** (Static complexity, code hotspots, and gravity matrices).
- **What is implemented vs. pending?** (Deduplicated graph of ideas, bases, and changes).
- **What architectural decisions were made?** (Living memory of past user conversations and commit history).

> 🚫 **Not just a passive documentation generator.** It is an active system of **Agent Governance**, **Permanent Memory**, and **Project Readiness**.

---

## ⚡ Quickstart in 10 Seconds

### 1. Global Installation (with `uv`)

```bash
# Recommended: single-command global install (requires https://docs.astral.sh/uv/)
uv tool install git+https://github.com/kudawasama/ContextMap.git

# Or with pip from a local clone:
# git clone https://github.com/kudawasama/ContextMap.git && cd ContextMap && pip install -e .
```

### 2. Contextualizing a Project

In any chat session with your AI Agent inside your IDE, simply type:

> 💬 **"Initialize ContextMap for this project"**

Or run it directly from your terminal:

```bash
# Complete automatic setup in 1 step:
ctxmap auto .

# Daily workflow: keep context fresh after changes:
ctxmap refresh .
```

---

## ✨ Key Features

### 🧠 1. Narrative Context with Soul
Every vault note is automatically enriched with a specialized narrative structure tailored to its semantic role:
* 💡 **IDEAS**: Origin, logic, proposed improvement, and **Pros & Cons** matrix.
* ⚠️ **RISKS**: Location, severity level, impact of ignoring, and **Mitigation Strategy**.
* 🔧 **CHANGES & FIXES**: Reason for change, affected files, and **Non-Regression Verification**.
* 📦 **BASE**: Structural role in the architecture and key integrations.
* 🧪 **TESTS**: Validated functionality, acceptance criteria, and `pytest` execution commands.
* 📄 **DOCUMENTS**: Extractive ingestion of PDFs, Markdown, and text with cited sources.

### 🔌 2. Native MCP Server (Model Context Protocol)
Exposes **9 native MCP tools** via stdio (`ctxmap mcp`) so compatible agents like **Hermes Agent**, **Claude Desktop**, or **Cursor** can call `refresh`, `scan`, `build`, `check`, or `context` directly without shell invocation:

```bash
# Connect to Hermes Agent:
hermes mcp add ctxmap --command ctxmap --args mcp
```

### 🛡️ 3. Protected Zone & Living Memory (`7.0-MANUAL/` & `8.0-KNOWLEDGE/`)
* **`7.0-MANUAL/`**: Holds session notes, daily journals (`Diario/YYYY-MM-DD.md`), and user agreements. The build engine **never deletes them** (`preserve: true`).
* **`8.0-KNOWLEDGE/`**: Actionable reusable learnings documented by the AI: Lesson · Solution Method · Specific Prompt · Specific Instruction · Connections.

### 📦 4. Multi-Project Personal Consolidated Database (`ctxmap personal`)
Consolidates into a single **SQLite + FTS5** database (`~/.context-map/personal/personal.db`) all events, lessons, and decisions across **all** your repositories:

```bash
ctxmap personal sync --todos      # Synchronizes all your repositories
ctxmap personal query "terms"     # Ultra-fast full-text search (low token consumption)
```

---

## 🏛️ Multi-IDE Governance

ContextMap automatically generates and injects contextual rule files adapted for over 10 AI tools:

| Agent / IDE | Rule File Generated |
| :--- | :--- |
| **Universal Standard** | `AGENTS.md` |
| **Claude Code** | `CLAUDE.md` |
| **Cursor** | `.cursor/rules/contextmap.mdc` and `.cursorrules` |
| **Windsurf** | `.windsurfrules` |
| **GitHub Copilot** | `.github/copilot-instructions.md` |
| **Gemini CLI** | `GEMINI.md` |
| **Hermes Agent** | `.hermes/config.yaml` + Workflows |
| **Cline & Roo Code** | `.clinerules` / `.roo/rules/contextmap.md` |
| **OpenCode & Aider** | `opencode.json` / `.aider.conf.yml` |

---

## 📊 Obsidian Vault & Graph View

ContextMap structures your vault following a **Strict Tree Topology** ensuring a clean Graph View in Obsidian:

```
.context-map/vault-ContextMap/
├── 00-INDICE.md                          # Main Dashboard MOC (Level 0)
├── 1.0-PROPOSITO/                        # Purpose, value, and boundaries
├── 2.0-IDEAS/                            # Ideas grouped by concept and status
│   ├── 2.1-Ideas-Pendientes/             # Pending tasks to implement
│   ├── 2.2-Ideas-Futuras/                # Roadmap and active initiatives
│   └── 2.3-Ideas-Completas-e-Implementadas/ # Validated codebase features
├── 3.0-ESTRUCTURA/                       # Base components and foundations
├── 4.0-RIESGOS/                          # Risk matrices and hotspots
├── 5.0-BACKLOG/                          # Sprint backlog
├── 6.0-HISTORIAL/                        # Commit history and changes
├── 7.0-MANUAL/                           # Protected zone: Daily journal & manual backlog
└── 8.0-KNOWLEDGE/                        # Protected zone: Agent learnings
```

---

## 🏗️ System Architecture (Clean Architecture)

ContextMap's source code adheres to strict modular decoupling and single-responsibility principles:

```
context_map/
├── core/                        # Fundamental domain
│   ├── models/                  # Dataclasses (Node, Edge, Event)
│   ├── normalization/           # Semantic standardization (mappings, inference, cleaning)
│   ├── parsing/                 # Event parser and JSONL deserializer
│   ├── storage/                 # JSONL persistence and snapshots
│   └── generators/              # Narrative generators
├── domain/                      # Business logic
│   ├── scanning/                # Static AST scanner and detectors
│   ├── synchronization/         # Incremental graph sync
│   ├── ingestion/               # Markdown, TXT, and PDF ingestion
│   ├── ecosystem/               # Agentic adapter (rules_templates)
│   ├── analysis/                # Readiness evaluator (check 0-100)
│   └── health/                  # Environment diagnostics (doctor)
├── application/                 # Orchestration and CLI
│   ├── cli/                     # CLI argument parser
│   └── commands/                # Commands (refresh, build, scan, personal, wrap)
├── infrastructure/              # External integrations
│   ├── integrations/            # Git, Hermes, Antigravity, MCP Server
│   └── analyzers/               # Static AST analyzers
└── presentation/                # Vault visual output
    ├── vault/                   # Obsidian Vault generator (atomic, consolidated, notas_ideas)
    └── briefs/                  # CONTEXT.md brief generator
```

---

## 💻 CLI Commands Reference

```bash
# 🚀 Daily workflow (recommended): keep context alive in 1 step
ctxmap refresh .                      # scan + build (preserving manuals) + check

# 🔄 Session closure
ctxmap wrap                           # refresh + living memory summary

# 🤖 MCP Server
ctxmap mcp                            # Launch stdio MCP server

# 📦 Personal Multi-Project DB
ctxmap personal sync --todos          # Sync all local repositories
ctxmap personal query "terms"         # Full-text search across all project histories

# 🛠️ Build and Scan
ctxmap auto .                         # Full scan + git import + clean build
ctxmap build                          # Rebuild Obsidian Vault
ctxmap build --brief                  # Generate CONTEXT.md and AGENTS.md
ctxmap check .                        # Audit Readiness Score (0-100)

# 📥 History Importers
ctxmap import-git .                   # Import Git commit history
ctxmap import-sessions                # Import Hermes Agent sessions
ctxmap import-antigravity             # Import Antigravity IDE chats
ctxmap import-chat export.jsonl       # Import Telegram, Discord, or Slack chats
ctxmap ingest document.pdf            # Ingest PDFs/Markdown to vault

# 🧰 Agentic Adapter
ctxmap adapt .                        # Generate rules respecting existing files
ctxmap adapt . --merge               # Merge ContextMap block into user rules
```

---

## ⚖️ Functional Comparison: ContextMap vs Industry Top Tools

| Feature / Capability | Code Concatenators (`Repomix` / `Gitingest`) | Repo Maps (`Aider`) | IDE Indexers (`Cursor` / `Windsurf`) | **ContextMap** |
| :--- | :---: | :---: | :---: | :---: |
| **Primary Approach** | Raw text/XML dump | AST symbol map + PageRank | Vector embeddings | **Governance + Living Memory + Vault** |
| **Token Consumption** | 🔴 Massive (huge file) | 🟢 Efficient | 🟡 Medium | 🟢 **Ultra-efficient (`CONTEXT.md` / MCP)** |
| **Interactive Visual Vault (Obsidian)** | ❌ No | ❌ No | ❌ No | **✅ Yes (Tree Graph, Canvas, Dataview)** |
| **Capture "Why" & "What For" (Soul)** | ❌ No (code only) | ❌ No (signatures only) | ❌ No | **✅ Yes (Polymorphic narrative notes)** |
| **Multi-IDE Governance (`AGENTS.md` + 10 IDEs)** | ❌ No | ❌ No | 🟡 IDE-locked | **✅ Yes (Portable across all IDEs)** |
| **Indestructible Living Memory (`7.0-MANUAL/`)** | ❌ No | ❌ No | ❌ No | **✅ Yes (Never wiped by build)** |
| **Agent Learnings (`8.0-KNOWLEDGE/`)** | ❌ No | ❌ No | ❌ No | **✅ Yes (Actionable lessons format)** |
| **Native MCP Server (9 stdio Tools)** | ❌ No | ❌ No | 🟡 Limited | **✅ Yes (`ctxmap mcp` for any agent)** |
| **Multi-Project Personal Database** | ❌ No | ❌ No | ❌ No | **✅ Yes (Portable SQLite + FTS5)** |
| **System Readiness Index (Score 0-100)** | ❌ No | ❌ No | ❌ No | **✅ Yes (`ctxmap check .`)** |
| **Single-Step Daily Sync Command** | ❌ No | ❌ No | ❌ No | **✅ Yes (`ctxmap refresh .`)** |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Created with ❤️ by [kudawasama](https://github.com/kudawasama)**

</div>
