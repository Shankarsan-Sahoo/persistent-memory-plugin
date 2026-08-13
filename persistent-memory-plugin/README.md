# Antigravity Persistent Memory Plugin 🧠

A zero-configuration, native AI extension for [Google Antigravity](https://github.com/google/antigravity) that gives your agent long-term, persistent memory across all your projects. 

Instead of starting from scratch in every new conversation, the agent can now recall past solutions, bug fixes, custom configurations, and contextual history from any codebase you've previously worked on.

## Features
- **Zero Configuration:** Drop the folder in and it just works. No cron jobs or task schedulers needed.
- **Proactive Memory Injection:** A `PreInvocation` hook automatically searches for past context based on your latest prompt and silently injects it into the agent's mind *before* it responds.
- **Memory Consolidation:** A background script analyzes conversations for explicit rules (e.g., "Always use X") and saves them to a permanent User Profile.
- **Native Lifecycle Integration:** Uses Antigravity's `Stop` hooks to securely run background synchronization only when the agent finishes its work.
- **MCP Tool Integration:** Automatically provides the agent with `search_past_memory` and `get_user_profile` tools to query the built-in SQLite database.
- **Cross-Platform:** Works seamlessly across Windows, macOS, and Linux.

## Installation

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
   
   > [!NOTE]
   > **`plugin.json` vs `plugins.json`**
   > This repository includes a singular `plugin.json` which acts as the manifest for this specific plugin. However, to turn it on, you must add it to your machine's global plural `plugins.json` configuration file, which acts as the master switchboard for all your installed plugins.

### Workspace Installation
If you want a team to share this memory agent on a specific project, drop the `persistent-memory-plugin` folder into:
`YourProjectFolder/.agents/plugins/` (create this directory if it does not exist)

(Don't forget to update the project's local `plugins.json`! Create it if it does not exist)

## How It Works

1. **The Rule (`rules/GEMINI.md`)**: Instructs the agent to always use its memory tools before writing code or making significant decisions.
2. **The Server (`scripts/mcp_memory_server.py`)**: An MCP server that exposes the `search_past_memory` and `get_user_profile` tools to the agent.
3. **The Harness (`scripts/harness.py`)**: A Python script that parses Antigravity conversation transcripts and safely ingests them into a local `memory.db` SQLite database using ultra-fast FTS5 (Full-Text Search).
4. **The Hooks (`hooks.json`)**: Uses Antigravity's lifecycle events:
   - `PreInvocation`: Triggers `proactive_memory.py` to auto-inject context before the agent thinks.
   - `Stop`: Triggers `harness.py update` to sync new memories and `consolidate.py` to extract explicit rules into the user profile.

## Uninstallation
To remove the plugin, simply delete the `persistent-memory-plugin` directory and remove its entry from your `plugins.json`.

---
*Built with [Antigravity Customizations](https://github.com/google/antigravity).*
