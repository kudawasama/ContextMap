# 🗺️ ContextMap

<div align="center">

# Permanent Living Memory for Your AI Coding Assistants

### *Stop your AI from forgetting architectural decisions, burning tokens, and breaking working code.*

[![Release](https://img.shields.io/badge/version-v2.4.0-blue.svg?style=for-the-badge)](CHANGELOG.md)
[![PyPI](https://img.shields.io/pypi/v/context-map-ai.svg?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/context-map-ai/)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](pyproject.toml)
[![Tests: 262 Passing](https://img.shields.io/badge/tests-262%2F262%20passing-brightgreen.svg?style=for-the-badge)](context_map/__tests__/)
[![Type Check: Strict MyPy](https://img.shields.io/badge/mypy-100%25%20strict-00599C.svg?style=for-the-badge&logo=python&logoColor=white)](.github/workflows/ci.yml)
[![Prompt Cache: Optimized](https://img.shields.io/badge/Prompt%20Cache->90%25%20Hit%20Rate-orange.svg?style=for-the-badge)](context_map/presentation/briefs/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

[Versión en Español 🇪🇸](README.md) • [📖 Technical Specifications & Architecture 🏛️](README_TECNICO.md) • [Changelog](CHANGELOG.md)

</div>

---

## 😫 The Big Pain of Coding with AI

If you build software using **Cursor, Claude Code, GitHub Copilot, ChatGPT, Antigravity, or Windsurf**, you have definitely experienced this:

1. 🧠 **Constant Amnesia**: You start a fresh chat session and the AI has zero memory of what you agreed on yesterday. You have to explain the entire project from scratch.
2. 💸 **Wasted Tokens & High Costs**: Dumping 100 raw code files into every prompt exhausts context limits, costs money, and causes hallucination.
3. 💥 **Blind Refactorings**: The AI rewrites code that was already working because it doesn't know why it was designed that way in the past.
4. 🔒 **Vendor Lock-in**: If you switch tools (from Cursor to Claude or VS Code), you lose all project context and instructions.

---

## 💡 The Solution: ContextMap

**ContextMap gives a "permanent living hard drive" to all your AI assistants.**

It scans your software repository, understands its architecture, and generates two powerful artifacts:
1. 🗺️ **An Interactive Obsidian Mind Map Vault**: A beautiful visual graph where you can explore how your ideas, modules, risks, and decisions connect in real time.
2. 📄 **An Ultra-Compact Executive AI Brief (`CONTEXT.md`)**: A high-density summary of only **~1,600 tokens** that provides your AI with immediate, accurate project understanding (**>99% token savings**).

```
   ┌───────────────────────────────────────────────────────────────┐
   │                    YOUR SOFTWARE REPOSITORY                   │
   └───────────────────────────────┬───────────────────────────────┘
                                   │
                           [ ctxmap refresh ]
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
        🗺️ OBSIDIAN VAULT                   📄 EXECUTIVE BRIEF
     (Visual, Interactive,              (Only ~1,600 tokens,
      Graph View & Dependencies)         >99% Token Savings for LLMs)
                 │                                   │
                 └─────────────────┬─────────────────┘
                                   ▼
          🤖 COMPATIBLE WITH ANY AI AGENT OR IDE
        Cursor · Claude Code · Copilot · Antigravity · Hermes
```

---

## 🚀 3-Step Quick Start

### 1. Install in 1 command
```bash
pip install context-map-ai
```
*(Or via `uv`: `uv tool install context-map-ai`)*

### 2. Initialize your project
In your IDE chat, simply tell your AI Agent:
> 💬 *"Initialize ContextMap for this project"*

Or run it directly in your terminal:
```bash
ctxmap auto .
```

### 3. Keep context updated as you work
Every time you make code changes or discuss decisions:
```bash
ctxmap refresh .
```

---

## ✨ Why Developers Love ContextMap

### 🧠 1. Indestructible Memory (`7.0-MANUAL/`)
Agreed on an architecture design with your team or client? Save it in your daily log or manual notes. ContextMap **never deletes your human notes** (`preserve: true`). Your AI will remember those agreements forever.

### 🌐 2. Multi-Project Executive Dashboard (`ctxmap personal panorama`)
Working across 5, 10, or 20 repositories? A single command gives you a traffic-light status of active vs. dormant projects and their urgent pending tasks:

```text
============================================================================
🌐 MULTI-PROJECT PANORAMA
============================================================================
Project                Status     Inactive   Events   Lessons/Dec  Sessions
----------------------------------------------------------------------------
E-Commerce-Platform    🟢 Active   1d         582      4/2          3       
Finance-App            🟢 Active   5d         336      4/0          1       
Scraping-Bot           🟡 Warm     21d        32       2/1          0       
----------------------------------------------------------------------------
```

### 🔌 3. Autonomous Control for AI Agents (Native MCP Server & Skills)
Includes a built-in **stdio MCP Server (16 tools)** and **Google Antigravity Skill generator**. Autonomous agents like **Antigravity, Hermes Agent, Claude Desktop, Cursor, and Windsurf** can inspect context, retrieve lessons, and save decisions without manual CLI commands.

### 🛡️ 4. Universal Rules & Skills for 10+ IDEs
Write project rules once, and ContextMap auto-syncs them to every tool's native format:
* **Google Antigravity**: `.agents/skills/contextmap/SKILL.md`
* **Hermes Agent**: `.hermes/workflows/contextmap.yaml` and `.hermes/config.yaml`
* **Universal Standard**: `AGENTS.md`
* **Claude Code**: `CLAUDE.md`
* **Cursor**: `.cursor/rules/contextmap.mdc` and `.cursorrules`
* **GitHub Copilot**: `.github/copilot-instructions.md`
* **Windsurf**: `.windsurfrules`
* **Cline / Roo Code**: `.clinerules`

---

## ⚖️ Comparison: ContextMap vs. Alternatives

| What do you need? | Raw Dumps<br>*(Repomix / Gitingest)* | IDE-Locked Indexers<br>*(Cursor / Windsurf)* | **ContextMap v2.4.0** |
| :--- | :---: | :---: | :---: |
| **Token Consumption** | 🔴 Massive (expensive & slow) | 🟡 Medium | 🟢 **Ultra-efficient (>99% savings)** |
| **Deterministic Prompt Caching** | ❌ Incompatible (breaks hash) | 🟡 Partial | **✅ Frozen Prefix (>90% Hit Rate)** |
| **Interactive Visual Graph** | ❌ None | ❌ None | **✅ Obsidian Vault** |
| **Permanent Architecture Memory** | ❌ Lost on chat close | 🟡 Partial | **✅ Indestructible Memory** |
| **Switch IDEs Without Loss** | ❌ No | ❌ Vendor Lock-in | **✅ 100% Portable** |
| **Multi-Project Portfolio View** | ❌ No | ❌ No | **✅ Consolidated SQLite DB** |
| **Native MCP Server & Skills** | ❌ No | 🟡 Proprietary | **✅ 16 Tools stdio + Antigravity Skill** |

---

## 💻 Essential CLI Commands

```bash
# 🚀 Daily workflow: sync and refresh all context
ctxmap refresh .

# 🌐 Global view: traffic light status across all projects
ctxmap personal panorama

# ⏱️ Timeline: chronological feed of past sessions and commits
ctxmap personal timeline --dias 7

# 🔍 Fast Search: query lessons and architectural decisions
ctxmap personal query "jwt authentication"

# 🏥 Health Check: verify repository readiness score
ctxmap check .
```

---

## 📚 Technical Deep Dive & Architecture

For software architects and engineers who want low-level details (Python AST inspection, McCabe Cyclomatic Complexity, Shannon Entropy Secrets Scanner, stdio MCP protocol, and strict acyclic graph topology):

👉 **[Read the Technical & Architecture Guide (README_TECNICO.md)](README_TECNICO.md)**

---

## 📄 License

Distributed under the **MIT** License. Free for personal and commercial software projects.
