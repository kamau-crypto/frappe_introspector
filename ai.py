import os
import sqlite3
import uuid
from typing import List, Sequence

from ollama import Client, Message, chat
from pydantic import BaseModel


class ChatMessages(BaseModel):
    role: str
    thinking: str
    content: str


class AIChat:
    """Handles all AI related interactions"""

    def __init__(self):
        self.model: str = "gemma3:4b"
        self.authenticated: bool = True  # An assertion for drawing inference
        self.user: str = "guest"

    """pass Messages from the client to the server for AI interactions"""

    def chat(self, messages: Sequence[Message]):
        """Stream chat responses as they arrive"""
        client = Client(
            host="https://ollama.com",
            headers={'Authorization': 'Bearer ' + os.environ.get("OLLAMA_API_KEY", "")}
        )
        stream = client.chat(model=self.model, messages=messages, stream=True)
        
        # Yield each content chunk as it arrives for real-time streaming
        for chunk in stream:
            if chunk.message.content:
                yield chunk.message.content

class AIChatDB:
    """Sets up the database for AI chat interactions"""

    def __init__(self):
       conn= self.__setup_db__()
       self.conn = conn
    
    def __setup_db__(self):
        """Set up the database schema for storing AI chat interactions"""
        # Implement the logic to create necessary tables and indexes
        conn = sqlite3.connect("ai_chat.db")
        cursor = conn.cursor()
        # "WITHOUT ROWID" makes the database smaller and faster for primary key lookups
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id TEXT PRIMARY KEY,
                user_id TEXT,
                role TEXT,
                thinking BOOLEAN,
                content TEXT
                message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) WITHOUT ROWID
        """)
        conn.commit()
        return conn
    
    def store_message(self, user_id: str, role: str, content: str, thinking: bool = False):
        """Store a chat message in the database"""
        cursor = self.conn.cursor()
        message_id = str(uuid.uuid4())  # Generate a unique message ID
        cursor.execute("""
            INSERT INTO chat_messages (message_id, user_id, role, thinking, content)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, user_id, role, thinking, content))
        self.conn.commit()
    
    def retrieve_messages(self, user_id: str) -> List[tuple[str, str, bool, str]]:
        """Retrieve chat messages for a specific user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT message_id, role, thinking, content FROM chat_messages
            WHERE user_id = ?
            ORDER BY message_id ASC
        """, (user_id,))
        return cursor.fetchall()