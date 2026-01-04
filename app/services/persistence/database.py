"""
Database Persistence Service

SQLite-based persistence for conversation history.
Supports saving and loading conversation state.
"""

import logging
import json
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path("./data/conversations.db")


def init_database() -> None:
    """Initialize the SQLite database with required tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Create conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            language TEXT DEFAULT 'en',
            is_complete BOOLEAN DEFAULT 0,
            payload TEXT,
            metadata TEXT
        )
    """)
    
    # Create messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_voice BOOLEAN DEFAULT 0,
            audio_duration REAL,
            metadata TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_thread_id ON conversations(thread_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_id ON messages(conversation_id)")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Database initialized at {DB_PATH}")


async def save_conversation(
    thread_id: str,
    messages: List[Dict[str, Any]],
    payload: Dict[str, Any],
    language: str = "en",
    is_complete: bool = False,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save or update a conversation.
    
    Args:
        thread_id: Unique conversation thread ID
        messages: List of message dictionaries
        payload: Current FNOL payload
        language: Language code
        is_complete: Whether the claim is complete
        metadata: Additional metadata
        
    Returns:
        True if successful
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Check if conversation exists
        cursor.execute(
            "SELECT id FROM conversations WHERE thread_id = ?",
            (thread_id,)
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing conversation
            conversation_id = row[0]
            cursor.execute("""
                UPDATE conversations 
                SET updated_at = ?, payload = ?, is_complete = ?, metadata = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                json.dumps(payload),
                is_complete,
                json.dumps(metadata) if metadata else None,
                conversation_id
            ))
            
            # Delete existing messages and re-insert
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        else:
            # Create new conversation
            cursor.execute("""
                INSERT INTO conversations (thread_id, language, payload, is_complete, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                thread_id,
                language,
                json.dumps(payload),
                is_complete,
                json.dumps(metadata) if metadata else None
            ))
            conversation_id = cursor.lastrowid
        
        # Insert messages
        for msg in messages:
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, is_voice, audio_duration, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                msg.get("role", "user"),
                msg.get("content", ""),
                msg.get("is_voice", False),
                msg.get("audio_duration"),
                json.dumps(msg.get("metadata")) if msg.get("metadata") else None
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved conversation {thread_id} with {len(messages)} messages")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")
        return False


async def load_conversation(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation by thread ID.
    
    Args:
        thread_id: Conversation thread ID
        
    Returns:
        Conversation data dict or None if not found
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get conversation
        cursor.execute(
            "SELECT * FROM conversations WHERE thread_id = ?",
            (thread_id,)
        )
        conv_row = cursor.fetchone()
        
        if not conv_row:
            conn.close()
            return None
        
        # Get messages
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp",
            (conv_row["id"],)
        )
        msg_rows = cursor.fetchall()
        
        conn.close()
        
        # Build result
        messages = []
        for msg in msg_rows:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"],
                "is_voice": bool(msg["is_voice"]),
                "audio_duration": msg["audio_duration"],
                "metadata": json.loads(msg["metadata"]) if msg["metadata"] else {}
            })
        
        return {
            "thread_id": conv_row["thread_id"],
            "created_at": conv_row["created_at"],
            "updated_at": conv_row["updated_at"],
            "language": conv_row["language"],
            "is_complete": bool(conv_row["is_complete"]),
            "payload": json.loads(conv_row["payload"]) if conv_row["payload"] else {},
            "metadata": json.loads(conv_row["metadata"]) if conv_row["metadata"] else {},
            "messages": messages
        }
        
    except Exception as e:
        logger.error(f"Failed to load conversation: {e}")
        return None


async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List conversations with optional filtering.
    
    Args:
        limit: Maximum number of results
        offset: Pagination offset
        language: Filter by language code
        
    Returns:
        List of conversation summaries
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM conversations"
        params = []
        
        if language:
            query += " WHERE language = ?"
            params.append(language)
        
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        return [
            {
                "thread_id": row["thread_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "language": row["language"],
                "is_complete": bool(row["is_complete"])
            }
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        return []


async def delete_conversation(thread_id: str) -> bool:
    """
    Delete a conversation and its messages.
    
    Args:
        thread_id: Conversation thread ID
        
    Returns:
        True if successful
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Get conversation ID
        cursor.execute(
            "SELECT id FROM conversations WHERE thread_id = ?",
            (thread_id,)
        )
        row = cursor.fetchone()
        
        if row:
            conversation_id = row[0]
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
            logger.info(f"Deleted conversation {thread_id}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        return False
