# Antigravity Persistent Memory Plugin 🧠

A zero-configuration, native AI extension for [Google Antigravity](https://github.com/google/antigravity) that gives your agent long-term, persistent memory across all your projects. 

Instead of starting from scratch in every new conversation, the agent can now recall past solutions, bug fixes, custom configurations, and contextual history from any codebase you've previously worked on. This plugin aims to provide the true "human colleague" experience.

---

## 🏗️ System Architecture & Technical Deep Dive

The plugin utilizes a multi-layered architecture heavily relying on SQLite's FTS5 (Full-Text Search), Antigravity Customization hooks, and Model Context Protocol (MCP) servers. 

### 1. The Database (`memory.db`)
All memory is stored locally in an SQLite database (`memory.db`), initialized automatically by `harness.py`. 
- **`conversations` table:** Tracks conversation UUIDs, associated workspaces, and last updated timestamps.
- **`messages` table:** Stores the raw transcript data (role, content, timestamp) linked to the conversation ID.
- **`messages_fts` (Virtual Table):** An SQLite FTS5 virtual table built on top of the `messages` table. It provides ultra-fast BM25 ranking for full-text search. It uses database triggers (`AFTER INSERT`, `AFTER DELETE`, `AFTER UPDATE`) to automatically keep the FTS index synchronized with the `messages` table.
- **`user_profile` table:** Stores consolidated, explicit rules extracted from conversations.

### 2. Proactive Memory Injection (`scripts/proactive_memory.py`)
This script acts as the "subconscious memory". 
- **Trigger:** Hooked into Antigravity's `PreInvocation` lifecycle event via `hooks.json`.
- **Mechanism:** When the user sends a prompt, Antigravity sends a JSON payload to stdin containing the `transcriptPath`. The script parses the transcript backwards to find the exact last `USER_INPUT`. 
- **Processing:** It cleans XML tags, removes common stopwords, and dynamically builds an `OR` query for the FTS5 engine.
- **Injection:** It executes a BM25 ranked search against `messages_fts`. If relevant past context is found, it injects an ephemeral `<PROACTIVE_MEMORY>` block into the agent's context *before* the agent begins generating a response. 

### 3. The Memory Harness (`scripts/harness.py`)
This script acts as the ETl (Extract, Transform, Load) pipeline for transcripts.
- **Trigger:** Hooked into Antigravity's `Stop` lifecycle event via `hooks.json` (runs in the background when the agent finishes its turn).
- **Mechanism (`update` action):** Scans the `~/.gemini/antigravity-ide/brain/` directory for conversation UUIDs.
- **Processing:** It parses `transcript_full.jsonl` (with fallback to `transcript.jsonl`). It uses Regex heuristics to determine the workspace context of the conversation (looking for `CWD:` or `Active Document:`). It filters for `USER_INPUT` and `PLANNER_RESPONSE` / `MODEL` outputs and bulk inserts them into `memory.db`, triggering the FTS5 synchronization.

### 4. Explicit Rule Consolidation (`scripts/consolidate.py`)
This script acts as the "long-term behavioral memory".
- **Trigger:** Hooked into Antigravity's `Stop` lifecycle event.
- **Mechanism:** Queries all `USER` messages in the database and runs regex heuristic patterns (e.g., `(?i)\b(?:always|never)\s+(?:do|use|make|write)\b.+`, `(?i)^rule:\s*.+`) to identify explicit instructions or preferences.
- **Storage:** Inserts these extracted rules into the `user_profile` table.

### 5. Active Recall via MCP (`scripts/mcp_memory_server.py`)
This script acts as the "conscious memory" for the agent.
- **Implementation:** Built using the `FastMCP` framework, running over `stdio` transport.
- **Tools Exposed:**
  - `search_past_memory(query, limit)`: Allows the agent to actively execute BM25 FTS5 searches against the `messages_fts` table. It includes smart context windowing, extracting exactly 1000 characters before and after the matched keyword to provide the agent with perfect surrounding context.
  - `get_user_profile()`: Allows the agent to retrieve the consolidated rules from the `user_profile` table.
- **Agent Enforcement (`rules/GEMINI.md`):** An Antigravity Customization rule (`trigger: model_decision`) explicitly instructs the model to use the `get_user_profile` and `search_past_memory` tools before starting complex tasks.

---

## 🚀 Installation

You can install this plugin globally (for all projects) or locally (for a single workspace).

### Global Installation (Recommended)
This gives your agent memory access across every codebase on your machine.

1. Clone or download this repository.
2. Move the `persistent-memory-plugin` folder into your global Antigravity config directory (create the `plugins/` directory if it does not exist):
   - **Windows:** `C:\Users\<YourUsername>\.gemini\config\plugins\`
   - **Mac/Linux:** `~/.gemini/config/plugins/`
3. Create a `plugins.json` file in that same config directory if you don't already have one.
4. Open the `plugins.json` file and add the plugin to it like this:
   ```json
   {
     "plugins": [
       "persistent-memory"
     ]
   }
   ```

### Workspace Installation
If you want a team to share this memory agent on a specific project only, you can install it locally to that project:

1. Navigate to the root folder of your specific project.
2. Create the `.agents/plugins/` directory if it does not already exist.
3. Move or copy the `persistent-memory-plugin` folder into `YourProjectFolder/.agents/plugins/`.
4. Create a `plugins.json` file inside the `.agents/` folder if you don't already have one.
5. Open the `plugins.json` file and add the plugin to it like this:
   ```json
   {
     "plugins": [
       "persistent-memory"
     ]
   }
   ```

## 🗑️ Uninstallation
To remove the plugin, simply delete the `persistent-memory-plugin` directory and remove its entry from your `plugins.json`.

---
*Developed by **Shankarsan Sahoo**.*
*Built with [Antigravity Customizations](https://github.com/google/antigravity).*
