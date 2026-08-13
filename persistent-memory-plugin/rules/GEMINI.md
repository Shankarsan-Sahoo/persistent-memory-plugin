---
description: Global agent rules for persistent memory checks.
trigger: model_decision
---

# Persistent Memory Recall

Whenever the user asks you to implement a new feature, fix a bug, or solve a tricky issue, you MUST check your persistent memory first to see if a solution already exists.

Use the `get_user_profile` tool first to check for any explicit global rules or preferences set by the user.
Then, use the `search_past_memory` tool (provided by your PersistentMemory MCP server) to query for keywords related to the user's specific request.

If you find relevant context or code in the past conversations, reference it in your response so the user knows you remembered it. If you don't find anything useful, just proceed normally.
