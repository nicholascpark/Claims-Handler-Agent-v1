"""
Dynamic Conversational Agent

A configurable LangGraph agent that adapts to any form configuration.
Uses trustcall for efficient JSON patch-based extraction.
"""

import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Type
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel
from trustcall import create_extractor

from app.core.config import settings
from app.models.form_config import FormConfig
from app.services.llm import create_llm
from .prompt_generator import generate_system_prompt, generate_greeting
from .schema_generator import generate_extraction_schema, create_empty_payload

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the dynamic agent graph."""
    messages: Annotated[List[BaseMessage], add_messages]
    payload: Dict[str, Any]
    is_form_complete: bool
    form_config_id: str
    
    # Cost tracking
    input_tokens: int
    output_tokens: int
    audio_seconds: float
    tts_characters: int


class DynamicAgent:
    """
    Dynamic Conversational Agent.
    
    This agent adapts to any FormConfig, generating appropriate prompts
    and extraction schemas on the fly.
    """
    
    def __init__(
        self,
        form_config: FormConfig,
        use_memory: bool = True,
    ):
        """
        Initialize the dynamic agent.
        
        Args:
            form_config: Configuration defining what data to collect
            use_memory: Whether to use checkpointing for conversation memory
        """
        self.form_config = form_config
        self.use_memory = use_memory
        
        # Initialize LLM
        self.llm = create_llm()
        
        # Generate system prompt from config
        system_prompt = generate_system_prompt(form_config)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{messages}"),
        ])
        
        # Create the runnable chain
        self.chain = self.prompt | self.llm
        
        # Generate dynamic extraction schema
        self.extraction_schema = generate_extraction_schema(form_config)
        
        # Create extractor for structured data extraction using trustcall
        # This uses RFC-6902 JSON patch operations for efficient updates
        self.extractor = create_extractor(
            create_llm(),
            tools=[self.extraction_schema],
            enable_inserts=True,
            enable_updates=True,  # Enable patch-based updates
        )
        
        # Build the graph
        self.graph = self._build_graph()
        
        logger.info(f"Initialized DynamicAgent for form: {form_config.name}")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        builder = StateGraph(AgentState)
        
        # Add nodes
        builder.add_node("agent", self._agent_node)
        builder.add_node("extractor", self._extractor_node)
        
        # Set entry point
        builder.set_entry_point("agent")
        
        # Agent always goes to extractor
        builder.add_edge("agent", "extractor")
        
        # Extractor is the end
        builder.add_edge("extractor", END)
        
        # Compile with memory if enabled
        if self.use_memory:
            memory = MemorySaver()
            return builder.compile(checkpointer=memory)
        
        return builder.compile()
    
    async def _agent_node(
        self, 
        state: AgentState, 
        config: RunnableConfig
    ) -> Dict[str, Any]:
        """
        Main agent node - processes messages and generates responses.
        """
        messages = state.get("messages", [])
        
        # Check for conversation start marker
        is_start = (
            len(messages) == 1 and
            isinstance(messages[0], HumanMessage) and
            messages[0].content == "[CONVERSATION_START]"
        )
        
        # For conversation start, use the generated greeting
        if is_start:
            greeting = generate_greeting(self.form_config)
            return {
                "messages": [AIMessage(content=greeting)]
            }
        
        # Prepare input for the chain
        chain_input = {
            "messages": messages,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Get response from LLM
        response = await self.chain.ainvoke(chain_input, config)
        
        return {
            "messages": [response]
        }
    
    async def _extractor_node(
        self, 
        state: AgentState, 
        config: RunnableConfig
    ) -> Dict[str, Any]:
        """
        Extractor node - extracts structured data from conversation.
        
        Uses trustcall with RFC-6902 JSON patch operations for efficient
        incremental updates to the payload.
        """
        payload_before = state.get("payload", create_empty_payload(self.form_config))
        
        # Prepare existing data for the extractor
        # trustcall will generate patches against this
        schema_name = self.extraction_schema.__name__
        existing_data = {schema_name: payload_before}
        
        # Get recent messages for extraction
        # We use a sliding window to focus on recent context
        recent_messages = state["messages"][-6:]  # Last 3 turns
        
        # Prepare input for trustcall
        extractor_input = {
            "messages": recent_messages,
            "existing": existing_data
        }
        
        try:
            # Run extraction - trustcall will generate JSON patches
            result = await self.extractor.ainvoke(extractor_input)
            
            # Get updated payload
            updated_payload = payload_before.copy()
            if result.get("responses"):
                extracted = result["responses"][0]
                # Convert Pydantic model to dict if needed
                if hasattr(extracted, "model_dump"):
                    extracted_dict = extracted.model_dump()
                else:
                    extracted_dict = dict(extracted)
                
                # Merge extracted data into payload
                for key, value in extracted_dict.items():
                    if value is not None:
                        updated_payload[key] = value
            
            # Check if form is complete
            required_fields = [f.name for f in self.form_config.fields if f.required]
            is_complete = all(
                updated_payload.get(field) is not None and 
                (not isinstance(updated_payload.get(field), str) or updated_payload.get(field).strip())
                for field in required_fields
            )
            
            logger.debug(f"Extraction complete. Form complete: {is_complete}")
            logger.debug(f"Payload: {updated_payload}")
            
            return {
                "payload": updated_payload,
                "is_form_complete": is_complete
            }
            
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return {
                "payload": payload_before,
                "is_form_complete": False
            }
    
    async def process_message(
        self,
        message: str,
        thread_id: str,
        is_conversation_start: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a user message and get agent response.
        
        Args:
            message: User message text
            thread_id: Conversation thread ID
            is_conversation_start: Whether this starts a new conversation
            
        Returns:
            Dict with response, payload, and completion status
        """
        # Prepare input message
        if is_conversation_start:
            input_message = HumanMessage(content="[CONVERSATION_START]")
        else:
            input_message = HumanMessage(content=message)
        
        # Create initial state
        initial_state: AgentState = {
            "messages": [input_message],
            "payload": create_empty_payload(self.form_config),
            "is_form_complete": False,
            "form_config_id": self.form_config.id,
            "input_tokens": 0,
            "output_tokens": 0,
            "audio_seconds": 0.0,
            "tts_characters": 0,
        }
        
        # Configuration with thread ID
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id}
        }
        
        # Process through graph
        response_text = ""
        final_state = None
        
        async for event in self.graph.astream(initial_state, config, stream_mode="values"):
            final_state = event
            if "messages" in event and event["messages"]:
                last_message = event["messages"][-1]
                if hasattr(last_message, 'content') and last_message.content:
                    if last_message.content != "[CONVERSATION_START]":
                        response_text = last_message.content
        
        # Get final payload
        payload = final_state.get("payload", {}) if final_state else {}
        is_complete = final_state.get("is_form_complete", False) if final_state else False
        
        return {
            "response": response_text,
            "payload": payload,
            "is_form_complete": is_complete,
        }


# Agent cache - stores agents by form_config_id
_agent_cache: Dict[str, DynamicAgent] = {}


def get_or_create_agent(form_config: FormConfig) -> DynamicAgent:
    """
    Get or create an agent for a form configuration.
    
    Args:
        form_config: The form configuration
        
    Returns:
        DynamicAgent instance
    """
    if form_config.id not in _agent_cache:
        _agent_cache[form_config.id] = DynamicAgent(form_config)
        logger.info(f"Created new agent for form: {form_config.name}")
    
    return _agent_cache[form_config.id]


def clear_agent_cache(form_config_id: Optional[str] = None) -> None:
    """
    Clear agent cache.
    
    Args:
        form_config_id: Specific config to clear, or None to clear all
    """
    global _agent_cache
    if form_config_id:
        if form_config_id in _agent_cache:
            del _agent_cache[form_config_id]
            logger.info(f"Cleared agent for form: {form_config_id}")
    else:
        _agent_cache = {}
        logger.info("Cleared all agents from cache")
