import sqlite3
from mcp.server.fastmcp import FastMCP

from pathlib import Path
from harness import init_db

# Initialize FastMCP server
mcp = FastMCP("PersistentMemory")

DB_PATH = Path(__file__).resolve().parent.parent / "memory.db"

@mcp.tool()
def search_past_memory(query: str, limit: int = 5) -> str:
    """
    Search past conversations across all projects in the persistent memory database.
    Use this tool whenever you need to recall past solutions, bug fixes, or context.
    
    Args:
        query: The search query to look for in past messages.
        limit: Maximum number of messages to return.
    """
    try:
        conn = init_db(silent=True)
        c = conn.cursor()
        
        c.execute('''
            SELECT c.workspace, f.role, f.content, f.timestamp, bm25(messages_fts) as rank
            FROM messages_fts f
            JOIN conversations c ON f.conversation_id = c.id
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (query, limit))
        
        results = c.fetchall()
        conn.close()
        
        if not results:
            return f"No past memory found for query: '{query}'"
            
        formatted_results = [f"--- Search Results for '{query}' ---"]
        for workspace, role, content, timestamp, rank in results:
            
            # Smart Context Windowing (Python-based)
            # Find the match and extract 1000 chars before and after for proper AI context
            query_lower = query.lower()
            content_lower = content.lower()
            idx = content_lower.find(query_lower)
            
            if idx != -1:
                start_idx = max(0, idx - 1000)
                end_idx = min(len(content), idx + 1000)
                
                prefix = "...\n" if start_idx > 0 else ""
                suffix = "\n..." if end_idx < len(content) else ""
                
                context_snippet = prefix + content[start_idx:end_idx] + suffix
            else:
                # Fallback if exact match not found (e.g., BM25 fuzzy matched it)
                context_snippet = content[:2000] + ("\n..." if len(content) > 2000 else "")
                
            formatted_results.append(
                f"Project: {workspace}\n"
                f"Date: {timestamp}\n"
                f"Role: {role}\n"
                f"Relevance: {rank:.2f}\n"
                f"Context:\n{context_snippet}\n"
                f"{'-'*40}"
            )
            
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error searching memory: {str(e)}"

@mcp.tool()
def get_user_profile() -> str:
    """
    Get the consolidated user profile containing explicit rules, preferences, and long-term instructions.
    Always check this to ensure you are following the user's coding style and preferences.
    """
    try:
        conn = init_db(silent=True)
        c = conn.cursor()
        c.execute("SELECT rule, timestamp FROM user_profile ORDER BY timestamp DESC")
        results = c.fetchall()
        conn.close()
        
        if not results:
            return "No consolidated rules or preferences found yet."
            
        formatted = ["--- Consolidated User Profile ---"]
        for rule, timestamp in results:
            formatted.append(f"[{timestamp}] {rule}")
            
        return "\n".join(formatted)
    except Exception as e:
        return f"Error reading user profile: {str(e)}"

if __name__ == "__main__":
    # Run the server using stdin/stdout streams
    mcp.run(transport='stdio')
