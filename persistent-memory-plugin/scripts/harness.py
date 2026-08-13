import os
import json
import sqlite3
import re
from pathlib import Path

# Paths
USER_PROFILE = os.environ.get("USERPROFILE", "C:\\Users\\shank")
BRAIN_DIR = Path(USER_PROFILE) / ".gemini" / "antigravity-ide" / "brain"
DB_PATH = Path(__file__).parent.parent / "memory.db"

def init_db():
    print(f"Initializing database at {DB_PATH.absolute()}...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            workspace TEXT,
            last_updated TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    ''')
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            conversation_id UNINDEXED,
            role UNINDEXED,
            content,
            timestamp UNINDEXED,
            content='messages',
            content_rowid='id'
        )
    ''')
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
            INSERT INTO messages_fts(rowid, conversation_id, role, content, timestamp)
            VALUES (new.id, new.conversation_id, new.role, new.content, new.timestamp);
        END;
    ''')
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, conversation_id, role, content, timestamp)
            VALUES ('delete', old.id, old.conversation_id, old.role, old.content, old.timestamp);
        END;
    ''')
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, conversation_id, role, content, timestamp)
            VALUES ('delete', old.id, old.conversation_id, old.role, old.content, old.timestamp);
            INSERT INTO messages_fts(rowid, conversation_id, role, content, timestamp)
            VALUES (new.id, new.conversation_id, new.role, new.content, new.timestamp);
        END;
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule TEXT UNIQUE,
            source_conversation TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    return conn

def extract_workspace(content):
    """Attempt to extract the workspace path from system context."""
    if not content: return None
    
    # Look for the mapping line like: C:\path\to\workspace -> CorpusName
    match = re.search(r'([A-Za-z]:\\[^\n]+?)\s+->\s+', content)
    if match:
        return match.group(1).strip()
        
    # CWD from terminal actions
    match = re.search(r'CWD:\s*([A-Za-z]:\\[^\n]+)', content)
    if match:
        return match.group(1).strip()
        
    # Active Document
    match = re.search(r'Active Document:\s*([A-Za-z]:\\[^\n]+?)\s*\(', content)
    if match:
        filepath = match.group(1).strip()
        return os.path.dirname(filepath)
        
    return None

def process_transcripts(conn):
    c = conn.cursor()
    if not BRAIN_DIR.exists():
        print(f"Error: Brain directory not found at {BRAIN_DIR}")
        return

    print(f"Scanning for conversations in {BRAIN_DIR}...")
    
    # Iterate through all conversation UUID folders
    for conv_dir in BRAIN_DIR.iterdir():
        if not conv_dir.is_dir():
            continue
            
        conv_id = conv_dir.name
        log_file = conv_dir / ".system_generated" / "logs" / "transcript_full.jsonl"
        
        # Fallback to truncated transcript if full is missing
        if not log_file.exists():
            log_file = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
            
        if not log_file.exists():
            continue
            
        print(f"Processing conversation: {conv_id}")
        
        workspace = "Unknown Project"
        messages_to_insert = []
        last_updated = ""
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        step = json.loads(line)
                        step_type = step.get("type")
                        source = step.get("source")
                        content = step.get("content", "")
                        created_at = step.get("created_at", "")
                        
                        last_updated = created_at
                        
                        # Extract workspace from context
                        if workspace == "Unknown Project":
                            extracted = extract_workspace(content)
                            if extracted:
                                workspace = extracted
                                
                        # Capture user and model messages
                        if step_type == "USER_INPUT":
                            # Clean up the xml tags for cleaner reading
                            clean_content = re.sub(r'<USER_REQUEST>\n?(.*?)\n?</USER_REQUEST>.*', r'\1', content, flags=re.DOTALL).strip()
                            messages_to_insert.append((conv_id, "USER", clean_content, created_at))
                            
                        elif step_type == "PLANNER_RESPONSE" or source == "MODEL":
                            # avoid adding empty responses
                            if content.strip():
                                messages_to_insert.append((conv_id, "AI", content.strip(), created_at))
                                
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"Failed to read {log_file}: {e}")
            continue

        # Insert into DB
        c.execute("INSERT OR REPLACE INTO conversations (id, workspace, last_updated) VALUES (?, ?, ?)", 
                  (conv_id, workspace, last_updated))
        
        # Clear old messages for this conversation to prevent duplicates on re-runs
        c.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        
        c.executemany("INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)", 
                      messages_to_insert)
        
    conn.commit()
    print("Database updated successfully!")

def search_memory(conn, query):
    c = conn.cursor()
    print(f"\n--- Searching for: '{query}' ---\n")
    
    # FTS5 search using MATCH
    c.execute('''
        SELECT c.workspace, f.role, snippet(messages_fts, 2, '>', '<', '...', 64), f.timestamp, bm25(messages_fts) as rank
        FROM messages_fts f
        JOIN conversations c ON f.conversation_id = c.id
        WHERE messages_fts MATCH ?
        ORDER BY rank
        LIMIT 10
    ''', (query,))
    
    results = c.fetchall()
    if not results:
        print("No results found.")
        return
        
    for workspace, role, content, timestamp, rank in results:
        print(f"[{timestamp}] Project: {workspace} | {role} (Rank: {rank:.2f}):")
        # Print a snippet if it's too long
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"{preview}\n{'-'*40}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Persistent Memory Harness")
    parser.add_argument("action", choices=["update", "search"], help="Action to perform")
    parser.add_argument("query", nargs="?", help="Search query (required for search action)")
    
    args = parser.parse_args()
    
    conn = init_db()
    
    if args.action == "update":
        process_transcripts(conn)
    elif args.action == "search":
        if not args.query:
            print("Error: Please provide a search query.")
        else:
            search_memory(conn, args.query)
    
    conn.close()
