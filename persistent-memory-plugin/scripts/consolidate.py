import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "memory.db"

def extract_rules(text):
    rules = []
    # Heuristic patterns to catch user instructions/preferences
    patterns = [
        r'(?i)\b(?:always|never)\s+(?:do|use|make|write)\b.+',
        r'(?i)^rule:\s*.+',
        r'(?i)\bremember that\b.+',
        r'(?i)\bmy\s+(?:preference|prefer)\s+is\b.+'
    ]
    for p in patterns:
        matches = re.findall(p, text, flags=re.MULTILINE)
        for m in matches:
            rules.append(m.strip())
    return rules

def run_consolidation():
    if not DB_PATH.exists():
        return
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT id, conversation_id, content, timestamp FROM messages WHERE role = 'USER'")
    rows = c.fetchall()
    
    new_rules = []
    for msg_id, conv_id, content, timestamp in rows:
        extracted = extract_rules(content)
        for rule in extracted:
            new_rules.append((rule, conv_id, timestamp))
            
    # Insert ignore to avoid duplicates
    c.executemany("INSERT OR IGNORE INTO user_profile (rule, source_conversation, timestamp) VALUES (?, ?, ?)", new_rules)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_consolidation()
