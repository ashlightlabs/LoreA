import sqlite3
import os
import json
import openai
from typing import List
from dotenv import load_dotenv
import numpy as np

DB_PATH = "data/lore.db"

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lore (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            embedding BLOB
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def embed_text(text: str) -> List[float]:
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def add_lore_to_db(title, content, tags):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    embedding = embed_text(content)
    cursor.execute('INSERT INTO lore (title, content, tags, embedding) VALUES (?, ?, ?, ?)',
                   (title, content, json.dumps(tags), json.dumps(embedding)))
    conn.commit()
    conn.close()

def get_all_lore_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT title, content, tags FROM lore')
    rows = cursor.fetchall()
    conn.close()
    return [{"title": r[0], "content": r[1], "tags": json.loads(r[2])} for r in rows]

def get_relevant_lore(prompt: str, top_k=5):
    prompt_embedding = np.array(embed_text(prompt))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT content, embedding FROM lore')
    rows = cursor.fetchall()
    scored = []
    for content, emb_json in rows:
        emb = np.array(json.loads(emb_json))
        similarity = np.dot(prompt_embedding, emb) / (np.linalg.norm(prompt_embedding) * np.linalg.norm(emb))
        scored.append((similarity, content))
    conn.close()
    scored.sort(reverse=True)
    return [c for _, c in scored[:top_k]]

def update_lore_entry(original_title, new_title, new_content, new_tags):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    embedding = embed_text(new_content)
    cursor.execute('''
        UPDATE lore
        SET title = ?, content = ?, tags = ?, embedding = ?
        WHERE title = ?
    ''', (new_title, new_content, json.dumps(new_tags), json.dumps(embedding), original_title))
    conn.commit()
    conn.close()


def generate_text_from_lore(prompt, lore_entries=None):
    if lore_entries is None:
        lore_entries = get_relevant_lore(prompt)
    lore_context = "\n".join(entry["content"] for entry in lore_entries)
    final_prompt = f"Using the following lore context, write a response to: {prompt}\n\nLore:\n{lore_context}\n\nResponse:"
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a narrative assistant for a game studio, helping write dialogue or story events based on lore."},
            {"role": "user", "content": final_prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    return response.choices[0].message.content

def delete_lore_entry_by_title(title):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM lore WHERE title = ?', (title,))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()