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
