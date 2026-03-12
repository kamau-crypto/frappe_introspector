import logging
import os
import sqlite3
import uuid
from typing import List


class AIChatDB:
    """Sets up the database for AI chat interactions"""

    def __init__(self):
       conn= self.__setup_db__()
       self.conn = conn
    
    def __setup_db__(self):
        """Set up the database schema for storing AI chat interactions"""
        try:
            
            # Implement the logic to create necessary tables and indexes
            conn = sqlite3.connect("ai_chat.db")
            cursor = conn.cursor()
            # "WITHOUT ROWID" makes the database smaller and faster for primary key lookups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation(
                    conversation INTEGER PRIMARY KEY,
                    conversation_id TEXT UNIQUE,
                    summary TEXT,
                    user TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP
                ) WITHOUT ROWID
                CREATE TABLE IF NOT EXISTS chat_message (
                    message_id TEXT PRIMARY KEY,
                    conversation TEXT,
                    role TEXT,
                    thinking BOOLEAN,
                    content TEXT,
                    message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation) REFERENCES conversation(conversation_id)
                ) WITHOUT ROWID
                
                CREATE INDEX IF NOT EXISTS idx_conversation_id ON conversation(conversation_id, summary)
                CREATE INDEX IF NOT EXISTS idx_user_id ON chat_message (content, message_time)
            """)
            conn.commit()
            return conn
        # The database can fail to set up for various reasons - log them all for easier debugging
        # and raise the error
        except OSError as e:
            logging.error(f"OS error: {e}")
            raise
        # Catch any SQLite-specific errors and log them
        except sqlite3.Error as e:
            logging.error(f"SQLite error: {e}")
            raise
        # Catch any other unexpected exceptions and log them
        except Exception as e:
            logging.error(f"Error setting up database: {e}")
            raise
    
    def store_session(self, user_id: str) -> str:
        """Create a new chat session and return its ID"""
        try:
            cursor = self.conn.cursor()
            session_id = str(uuid.uuid4())  # Generate a unique session ID
            cursor.execute("""
                INSERT INTO session (id, user)
                VALUES (?, ?)
            """, (session_id, user_id))
            self.conn.commit()
            return session_id
        except sqlite3.Error as e:
            logging.error(f"SQLite error storing session for user {user_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"Error storing session for user {user_id}: {e}")
            raise
    
    def store_message(self, session_id: str, role: str, content: str, thinking: bool = False):
        """Store a chat message in the database"""
        try:
            cursor = self.conn.cursor()
            message_id = str(uuid.uuid4())  # Generate a unique message ID
            cursor.execute("""
                INSERT INTO chat_messages (message_id, session, role, thinking, content)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, session_id, role, thinking, content))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"SQLite error storing message for session {session_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"Error storing message for session {session_id}: {e}")
            raise
    
    def retrieve_conversations(self, user_id: str) -> List[tuple[str, str, str]] | bool:
        """Retrieve chat sessions for a specific user"""
        try: 
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, summary, start_time FROM session
                WHERE user = ?
                ORDER BY start_time DESC
            """, (user_id,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"SQLite error retrieving conversations for user {user_id}: {e}")
            return False
        except Exception as e:
            logging.error(f"Error retrieving conversations for user {user_id}: {e}")
            return False
    
    def retrieve_conversation_messages(self, conversation_id: str, limit:int = 0, offset:int = 0) -> List[tuple[str, str, bool, str]] | bool:
        try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT message_id, role, thinking, content FROM chat_message
                    INNER JOIN conversation ON chat_message.conversation = conversation.conversation_id
                    WHERE conversation_id = ?
                    ORDER BY message_time ASC
                    LIMIT ? OFFSET ?
                """, (conversation_id, limit, offset))
                return cursor.fetchall()
        except sqlite3.Error as e:
                logging.error(f"SQLite error retrieving messages for conversation {conversation_id}: {e}")
                return False
        except Exception as e:
            logging.error(f"Error retrieving messages for conversation {conversation_id}: {e}")
            return False
        
    def update_conversation_summary(self, conversation_id: str, summary: str):
        """Update the summary of a conversation"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE conversation
                SET summary = ?
                WHERE conversation_id = ?
            """, (summary, conversation_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"SQLite error updating summary for conversation {conversation_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"Error updating summary for conversation {conversation_id}: {e}")
            raise 