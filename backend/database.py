"""
database.py - Database Layer for SQLite

Beginner-Friendly Explanation:
SQLite is a lightweight, zero-configuration database that stores all data
inside a single file (backend/data/farmer_advisor.db).
This file defines our database schema and provides helper functions to:
1. Connect to the database safely.
2. Initialize tables (Users, Conversations, Messages).
3. Query and insert records with protection against SQL injection attacks.
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
import backend.config as config


def get_db_connection():
    """
    Creates and returns a connection to the SQLite database.
    row_factory is set to sqlite3.Row so query results can be accessed like Python dicts
    (e.g., row['username'] instead of row[1]).
    """
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_session():
    """
    Context manager for database operations.
    Automatically commits on success or rolls back changes if an exception occurs.
    Usage:
        with db_session() as conn:
            conn.execute(...)
    """
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Initializes the database schema if tables do not already exist.
    Creates 3 related tables:
    1. users: Stores farmer credentials and display info.
    2. conversations: Tracks chat threads for each farmer.
    3. messages: Stores individual queries and AI advisory replies.
    """
    schema = """
    -- Users table: Stores registered farmers
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        location TEXT DEFAULT 'Delhi,IN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Conversations table: Groups messages into distinct chat sessions
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Messages table: Stores chat history, attached crop images, and weather snapshots
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        sender TEXT NOT NULL CHECK(sender IN ('user', 'assistant')),
        text TEXT NOT NULL,
        image_filename TEXT,
        weather_snapshot TEXT,
        is_simulated INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );

    -- Indexes to speed up queries on foreign keys
    CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
    CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
    """
    with db_session() as conn:
        conn.executescript(schema)


# ---------------------------------------------------------------------------
# Helper Functions for Users
# ---------------------------------------------------------------------------

def create_user(username: str, password_hash: str, full_name: str, location: str = 'Delhi,IN') -> int:
    """Inserts a new user into the database and returns the generated user id."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, location) VALUES (?, ?, ?, ?)",
            (username.strip().lower(), password_hash, full_name.strip(), location.strip() or 'Delhi,IN')
        )
        return cursor.lastrowid


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    """Retrieves a user record by username (case-insensitive)."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
        return cursor.fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    """Retrieves a user record by user ID."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()


# ---------------------------------------------------------------------------
# Helper Functions for Conversations & Messages
# ---------------------------------------------------------------------------

def create_conversation(user_id: int, title: str = "New Query") -> int:
    """Creates a new conversation session for a user."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (user_id, title.strip()[:100])
        )
        return cursor.lastrowid


def get_user_conversations(user_id: int) -> List[Dict[str, Any]]:
    """Retrieves all conversation sessions for a given user, newest first."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_conversation_by_id(conversation_id: int, user_id: int) -> Optional[sqlite3.Row]:
    """Retrieves a specific conversation, ensuring it belongs to the given user."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id)
        )
        return cursor.fetchone()


def update_conversation_title(conversation_id: int, title: str):
    """Updates the display title of a conversation."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title.strip()[:100], conversation_id)
        )


def add_message(
    conversation_id: int,
    sender: str,
    text: str,
    image_filename: Optional[str] = None,
    weather_snapshot: Optional[Dict[str, Any]] = None,
    is_simulated: bool = False
) -> int:
    """
    Appends a new message (from farmer or AI) to the conversation.
    Also updates the conversation's updated_at timestamp.
    """
    weather_json = json.dumps(weather_snapshot) if weather_snapshot else None
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, sender, text, image_filename, weather_snapshot, is_simulated)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, sender, text, image_filename, weather_json, 1 if is_simulated else 0)
        )
        message_id = cursor.lastrowid

        # Update parent conversation timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        return message_id


def get_conversation_messages(conversation_id: int) -> List[Dict[str, Any]]:
    """Retrieves all messages for a conversation in chronological order."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, sender, text, image_filename, weather_snapshot, is_simulated, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,)
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            item = dict(row)
            if item.get('weather_snapshot'):
                try:
                    item['weather_snapshot'] = json.loads(item['weather_snapshot'])
                except (json.JSONDecodeError, TypeError):
                    item['weather_snapshot'] = None
            results.append(item)
        return results


def delete_conversation(conversation_id: int, user_id: int) -> bool:
    """Deletes a conversation and all its cascaded messages."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id)
        )
        return cursor.rowcount > 0
