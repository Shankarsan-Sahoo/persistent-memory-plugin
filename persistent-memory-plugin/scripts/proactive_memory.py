import sys
import json
import sqlite3
import re
from pathlib import Path
from harness import build_safe_fts_query, extract_keywords

DB_PATH = Path(__file__).resolve().parent.parent / "memory.db"

def extract_last_user_prompt(transcript_path):
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Search backwards for the last USER_INPUT
            for line in reversed(lines):
                if not line.strip(): continue
                try:
                    step = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if step.get("type") == "USER_INPUT":
                    content = step.get("content", "")
                    clean_content = re.sub(r'<USER_REQUEST>\n?(.*?)\n?</USER_REQUEST>.*', r'\1', content, flags=re.DOTALL).strip()
                    return clean_content
    except Exception:
        return None
    return None

def search_memory(query, keywords):
    if not DB_PATH.exists():
        return None
        
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            SELECT c.workspace, f.role, f.content, f.timestamp, bm25(messages_fts) as rank
            FROM messages_fts f
            JOIN conversations c ON f.conversation_id = c.id
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT 3
        ''', (query,))
        
        results = c.fetchall()
        conn.close()
        
        if not results:
            return None
            
        formatted_results = ["<PROACTIVE_MEMORY>"]
        formatted_results.append("The system has automatically retrieved relevant past context based on your prompt:\n")
        
        for workspace, role, content, timestamp, rank in results:
            content_lower = content.lower()
            # Simple keyword highlighting for snippet extraction
            first_keyword = next((kw for kw in keywords if kw in content_lower), None)
            
            if first_keyword:
                idx = content_lower.find(first_keyword)
                start_idx = max(0, idx - 500)
                end_idx = min(len(content), idx + 500)
                prefix = "...\n" if start_idx > 0 else ""
                suffix = "\n..." if end_idx < len(content) else ""
                context_snippet = prefix + content[start_idx:end_idx] + suffix
            else:
                context_snippet = content[:1000] + ("\n..." if len(content) > 1000 else "")
                
            formatted_results.append(
                f"Project: {workspace}\n"
                f"Date: {timestamp}\n"
                f"Role: {role}\n"
                f"Context:\n{context_snippet}\n"
                f"{'-'*40}"
            )
            
        formatted_results.append("</PROACTIVE_MEMORY>")
        return "\n".join(formatted_results)
    except Exception as e:
        return None

def main():
    # Read payload from stdin
    try:
        input_data = sys.stdin.read()
        payload = json.loads(input_data)
    except Exception:
        print(json.dumps({}))
        return

    transcript_path = payload.get("transcriptPath")
    if not transcript_path:
        print(json.dumps({}))
        return
        
    prompt = extract_last_user_prompt(transcript_path)
    if not prompt:
        print(json.dumps({}))
        return
        
    keywords = extract_keywords(prompt)
    fts_query = build_safe_fts_query(prompt)
    if not fts_query:
        print(json.dumps({}))
        return
        
    memory_context = search_memory(fts_query, keywords)
    
    if memory_context:
        output = {
            "injectSteps": [
                {
                    "ephemeralMessage": memory_context
                }
            ]
        }
        print(json.dumps(output))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
