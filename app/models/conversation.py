"""
Conversation Models

Models for managing conversation state, history, and sessions.
These support both the LangGraph state machine and persistence.
"""

from typing import List, Optional, Dict, Any, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import operator

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from .claim import FNOLPayload, create_default_payload


class MessageRole(str, Enum):
    """Role of a message in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """A single message in conversation history."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    is_voice: bool = Field(default=False, description="Whether this was a voice message")
    language: Optional[str] = Field(default=None, description="Detected language code")
    audio_duration: Optional[float] = Field(default=None, description="Audio duration in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationState(BaseModel):
    """
    LangGraph-compatible conversation state.
    
    This TypedDict-style class manages the state passed between
    nodes in the LangGraph workflow.
    """
    # Core conversation state
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    
    # Claim extraction state
    payload: FNOLPayload = Field(default_factory=create_default_payload)
    is_form_complete: bool = Field(default=False)
    
    # Process control
    process_complete: bool = Field(default=False)
    api_retry_count: int = Field(default=0)
    api_call_successful: bool = Field(default=False)
    
    # Language settings
    language: str = Field(default="en")
    
    class Config:
        arbitrary_types_allowed = True


class ConversationSession(BaseModel):
    """
    Session data for a conversation.
    
    This tracks all session-level information including
    thread configuration, timestamps, and metadata.
    """
    thread_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    
    # State tracking
    payload: FNOLPayload = Field(default_factory=create_default_payload)
    is_form_complete: bool = Field(default=False)
    process_complete: bool = Field(default=False)
    api_call_successful: bool = Field(default=False)
    
    # Language
    language: str = Field(default="en")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def update_access_time(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now()
    
    def to_config(self) -> Dict[str, Any]:
        """Get LangGraph configuration for this session."""
        return {"configurable": {"thread_id": self.thread_id}}


class ConversationHistory(BaseModel):
    """
    Persistent conversation history.
    
    This model is used for storing and retrieving
    conversation history from the database.
    """
    id: Optional[int] = None
    thread_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Conversation data
    messages: List[Message] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    is_complete: bool = Field(default=False)
    
    # Session metadata
    language: str = Field(default="en")
    total_messages: int = Field(default=0)
    total_audio_duration: float = Field(default=0.0)
    
    def add_message(self, message: Message) -> None:
        """Add a message to the history."""
        self.messages.append(message)
        self.total_messages += 1
        if message.audio_duration:
            self.total_audio_duration += message.audio_duration
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.model_dump() for m in self.messages],
            "payload": self.payload,
            "is_complete": self.is_complete,
            "language": self.language,
            "total_messages": self.total_messages,
            "total_audio_duration": self.total_audio_duration
        }
