import sqlite3
import os
import json
import pdb
import sys
from typing import List, Dict, Any, Optional, Generator
from dotenv import load_dotenv
import numpy as np
from openai import OpenAI
import numpy.typing as npt
from contextlib import contextmanager

from ..logging.logger import log_info, log_error, log_warning, log_debug
from ..utils.openai_logger import log_openai_interaction

DB_PATH = "data/lore.db"

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def clean_duplicate_entries():
    """Remove duplicate entries keeping only the most recent version."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Find duplicates
        cursor.execute('''
            WITH DuplicateTitles AS (
                SELECT title, COUNT(*) as count, MAX(id) as latest_id
                FROM lore
                GROUP BY title
                HAVING count > 1
            )
            DELETE FROM lore 
            WHERE title IN (SELECT title FROM DuplicateTitles)
            AND id NOT IN (SELECT latest_id FROM DuplicateTitles)
        ''')
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count

def init_db():
    log_info("Initializing database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS lore (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT NOT NULL,
            template TEXT,
            fields TEXT NOT NULL,
            embedding BLOB NOT NULL,
            linked_entries TEXT DEFAULT '[]'
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    # Check for and clean up duplicates
    deleted_count = clean_duplicate_entries()
    if (deleted_count > 0):
        log_info(f"Cleaned up {deleted_count} duplicate entries")

def embed_text(text: str) -> npt.NDArray[np.float32]:
    """Generate embeddings for input text using OpenAI's API.
    
    Args:
        text: Input text to embed. Must be non-empty.
        
    Returns:
        numpy.ndarray: Embedding vector as float32 array
        
    Raises:
        ValueError: If text is empty or invalid
        OpenAIError: If API request fails
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")
        
    try:
        # Clean and prepare the text
        cleaned_text = text.strip()
        # OpenAI has a token limit for embeddings
        if len(cleaned_text) > 8191:
            cleaned_text = cleaned_text[:8191]
            
        response = client.embeddings.create(
            input=cleaned_text,
            model="text-embedding-ada-002",
            encoding_format="float"  # Explicitly specify format
        )
        
        # New API returns embedding directly
        embedding_data = response.data[0].embedding
        return np.array(embedding_data, dtype=np.float32)
        
    except Exception as e:
        raise ValueError(f"Embedding generation failed: {str(e)}")

def get_entry_by_title(title: str) -> Optional[Dict[str, Any]]:
    """Get a single lore entry by its title."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT title, content, tags, template, fields FROM lore WHERE title = ?',
            (title,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "title": row[0],
            "content": row[1],
            "tags": json.loads(row[2]) if row[2] else [],
            "template": row[3],
            "fields": json.loads(row[4]) if row[4] else {}
        }

def compute_linked_entries(content: Dict[str, Any], all_titles: List[str]) -> List[str]:
    """Scan content for mentions of other entries.
    
    Uses a more comprehensive approach:
    1. Scans all field content
    2. Uses more robust text matching
    3. Prioritizes exact matches
    """
    linked = set()
    
    # Convert all content to searchable text
    all_text = []
    for field, value in content.items():
        if isinstance(value, str) and field != "Tags":  # Skip tags field
            # Split into sentences/phrases for more precise matching
            phrases = [p.strip() for p in value.split('.')]
            all_text.extend(phrases)
    
    # Look for matches, prioritizing exact matches
    for title in all_titles:
        title_lower = title.lower()
        
        # First look for exact matches
        if any(title in text for text in all_text):
            linked.add(title)
            continue
            
        # Then look for case-insensitive matches
        if any(title_lower in text.lower() for text in all_text):
            linked.add(title)
    
    return list(linked)

def add_lore_to_db(
    title: str, 
    content: str | Dict[str, Any], 
    tags: List[str] | str, 
    template: Optional[str] = None,
    linked_entries: Optional[List[str]] = None
) -> None:
    """Add a new lore entry to the database."""
    log_info(f"Adding lore entry: {title}")
    try:
        # Check if entry already exists
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM lore WHERE title = ?', (title,))
            if cursor.fetchone():
                log_warning(f"Entry with title '{title}' already exists, skipping")
                return

            # Get all existing titles for link computation
            cursor.execute('SELECT title FROM lore')
            all_titles = [row[0] for row in cursor.fetchall()]
            
            if isinstance(content, dict):
                fields_json = json.dumps(content)
                # Extract meaningful content for embedding
                content_str = "\n".join(
                    f"{k}: {v}" for k, v in content.items() 
                    if k != "Tags" and v and str(v).strip()
                )
                # Use provided linked_entries or compute them
                final_linked_entries = linked_entries if linked_entries is not None else compute_linked_entries(content, all_titles)
            else:
                fields_json = json.dumps({})
                content_str = content
                final_linked_entries = linked_entries if linked_entries is not None else []
            
            if not content_str.strip():
                log_warning(f"Empty content for entry '{title}', using title as content")
                content_str = title
            
            tags_json = json.dumps(tags) if isinstance(tags, list) else tags
            embedding = embed_text(content_str).tobytes()
            linked_json = json.dumps(final_linked_entries)
            
            cursor.execute(
                """INSERT INTO lore 
                   (title, content, tags, template, fields, embedding, linked_entries) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title, content_str, tags_json, template, fields_json, embedding, linked_json)
            )
            conn.commit()
        log_info(f"Successfully added lore entry: {title}")
    except Exception as e:
        log_error(f"Failed to add lore entry: {title} - {str(e)}")
        raise

def get_all_lore_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT title, content, tags, template, fields, linked_entries FROM lore')
    rows = cursor.fetchall()
    conn.close()
    return [{
        "title": r[0],
        "content": r[1],
        "tags": json.loads(r[2]) if r[2] else [],
        "template": r[3],
        "fields": json.loads(r[4]) if r[4] else {},
        "linked_entries": json.loads(r[5]) if r[5] else []
    } for r in rows]

def get_relevant_lore(prompt: str, top_k: int = 5) -> List[str]:
    prompt_embedding = embed_text(prompt)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT content, embedding FROM lore')
    rows = cursor.fetchall()
    scored = []
    for content, emb_blob in rows:
        emb = np.frombuffer(emb_blob, dtype=np.float32)
        similarity = np.dot(prompt_embedding, emb) / (np.linalg.norm(prompt_embedding) * np.linalg.norm(emb))
        scored.append((similarity, content))
    conn.close()
    scored.sort(reverse=True)
    return [c for _, c in scored[:top_k]]

def update_lore_entry(original_title: str, new_title: str, new_content: str, new_tags: List[str], new_template: Optional[str] = None, new_fields: Optional[Dict[str, Any]] = None) -> None:
    log_info(f"Updating lore entry: {original_title} -> {new_title}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        embedding = embed_text(new_content).tobytes()
        fields_json = json.dumps(new_fields) if new_fields else "{}"
        cursor.execute('''
            UPDATE lore
            SET title = ?, content = ?, tags = ?, template = ?, fields = ?, embedding = ?
            WHERE title = ?
        ''', (new_title, new_content, json.dumps(new_tags), new_template, fields_json, embedding, original_title))
        conn.commit()
        conn.close()
        log_info(f"Successfully updated lore entry: {new_title}")
    except Exception as e:
        log_error(f"Failed to update lore entry: {original_title} - {str(e)}")
        raise

def generate_text_from_lore(prompt: str, lore_entries: Optional[List[str]] = None) -> str:
    log_info("Generating text from lore prompt")
    try:
        if lore_entries is None:
            lore_entries = get_relevant_lore(prompt)
        lore_context = "\n".join(lore_entries)
        final_prompt = f"Using the following lore context, write a response to: {prompt}\n\nLore:\n{lore_context}\n\nResponse:"
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a narrative assistant for a game studio, helping write dialogue or story events based on lore."},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        log_info("Successfully generated text from lore")
        return response.choices[0].message.content
    except Exception as e:
        log_error(f"Failed to generate text from lore: {str(e)}")
        raise

def delete_lore_entry_by_title(title: str) -> None:
    log_info(f"Deleting lore entry: {title}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM lore WHERE title = ?', (title,))
        conn.commit()
        conn.close()
        log_info(f"Successfully deleted lore entry: {title}")
    except Exception as e:
        log_error(f"Failed to delete lore entry: {title} - {str(e)}")
        raise

def delete_settings() -> None:
    """Delete all settings from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM settings')
        conn.commit()

def delete_all_entries() -> None:
    """Delete all entries from the lore database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM lore')
        conn.commit()

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key: str, value: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def get_filtered_lore(
    tags: Optional[List[str]] = None,
    entry_type: Optional[str] = None,
    query: Optional[str] = None
) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        base_query = '''
            SELECT title, content, tags, template, fields, linked_entries
            FROM lore 
            WHERE 1=1
        '''
        params = []
        
        if tags:
            for tag in tags:
                base_query += " AND json_extract(tags, '$') LIKE ?"
                params.append(f'%{tag}%')
        
        if entry_type:
            base_query += " AND template = ?"
            params.append(entry_type)
        
        if query:
            base_query += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f'%{query}%', f'%{query}%'])
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        
        return [{
            "title": r[0],
            "content": r[1],
            "tags": json.loads(r[2]) if r[2] else [],
            "template": r[3],
            "fields": json.loads(r[4]) if r[4] else {},
            "linked_entries": json.loads(r[5]) if r[5] else []
        } for r in rows]

def get_entries_for_export() -> List[Dict[str, Any]]:
    """Get all entries formatted for JSON export."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT template, fields, linked_entries FROM lore')
        rows = cursor.fetchall()
        
        entries = [{
            "template": row[0],
            "fields": json.loads(row[1]) if row[1] else {},
            "linked_entries": json.loads(row[2]) if row[2] else []
        } for row in rows]
        
        # Use json.dumps and loads to clean up any escaped Unicode
        cleaned = json.loads(json.dumps(entries, ensure_ascii=False))
        return cleaned

def get_entries_for_markdown_export() -> str:
    """Get all entries formatted as Markdown text."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT template, fields, linked_entries FROM lore')
        rows = cursor.fetchall()
        
        markdown_chunks = []
        for row in rows:
            template = row[0]
            fields = json.loads(row[1]) if row[1] else {}
            linked = json.loads(row[2]) if row[2] else []
            
            # Start with template type as heading
            chunk = [f"# {template}\n"]
            # Add name as regular text
            chunk.append(f"{fields.get('Name', 'Untitled')}\n\n")
            
            # Add each field
            for field, value in fields.items():
                if field != "Name":  # Skip name since we used it already
                    if isinstance(value, list):  # Handle tags
                        value = ", ".join(value)
                    chunk.append(f"### {field}\n{value}\n\n")
            
            # Add linked entries section if any exist
            if linked:
                chunk.append("### Linked Entries\n")
                for link in linked:
                    chunk.append(f"- {link}\n")
                chunk.append("\n")
            
            chunk.append("---\n\n")  # Add separator between entries
            markdown_chunks.append("".join(chunk))
        
        return "".join(markdown_chunks)

def generate_field_content(
    entry_title: str,
    field_name: str,
    template_type: str,
    current_content: str,
    user_prompt: Optional[str] = None,
    tags: Optional[List[str]] = None,
    generation_style: str = "Default"
) -> str:
    """Generate content for a specific field using GPT-4."""
    # Check for dev mode
    if get_setting("dev_mode") == "true":
        return f"[DEV MODE] Sample generated content for {field_name} of {entry_title} using [{generation_style}] style.\nPrompt: {user_prompt or 'No prompt provided'}"
    
    # Create descriptive context from tags
    tag_context = f"Consider these descriptive elements, filter for nouns that add color and depth. Adjectives are less of a priority: {', '.join(tags)}" if tags else ""
    
    # Craft the system prompt
    system_prompt = (
        f"You are a narrative assistant helping write content for a {template_type}'s {field_name} field. "
    )
    
    if generation_style != "Default":
        system_prompt += (
            f"Format the content as {generation_style}. For example, if generating Character Dialogue, "
            f"write the content as spoken dialogue from the character's perspective. "
        )
    
    system_prompt += (
        "Provide only the content without including the field name. "
        f"{tag_context} "
        "Keep the tone consistent with existing lore and be specific."
    )

    # Get relevant entries for context
    related_entries = get_relevant_lore(current_content or entry_title, top_k=3)
    
    # Craft the user prompt with style guidance
    base_prompt = f"Write {generation_style} content for the {field_name} field of {entry_title}."
    context = f"Current content: {current_content}\n" if current_content else ""
    context += f"Related lore:\n{chr(10).join(related_entries)}\n" if related_entries else ""
    final_prompt = f"{base_prompt}\n{context}"
    if user_prompt:
        final_prompt += f"\nSpecific request: {user_prompt}"
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": final_prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )

    # Clean up response to remove any field name prefixes
    content = response.choices[0].message.content
    if ":" in content and content.split(":")[0].strip().lower() == field_name.lower():
        content = content.split(":", 1)[1].strip()
    
    # Log the interaction
    log_openai_interaction(
        entry_title=entry_title,
        field_name=field_name,
        system_prompt=system_prompt,
        user_prompt=final_prompt,
        response=content
    )
    
    return content.strip()

def process_template_fields(template_fields: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
    """Process template fields and extract tags.
    Returns tuple of (fields_dict, tags)."""
    fields_dict = {}
    tags = []
    
    for field, value in template_fields.items():
        if field == "Tags":
            tags = value  # Tags are already a list from the input processing
        else:
            fields_dict[field] = value
            
    fields_dict["Tags"] = tags
    return fields_dict, tags
