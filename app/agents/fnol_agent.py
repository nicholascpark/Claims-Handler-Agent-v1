"""
FNOL Agent

LangGraph-based First Notice of Loss claims intake agent.
Manages conversation flow and claim data extraction.
"""

import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from trustcall import create_extractor

from app.core.config import settings
from app.models.claim import FNOLPayload, create_default_payload
from app.services.llm import create_llm
from .prompts import create_prompt_template
from .tools import AGENT_TOOLS

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the FNOL agent graph."""
    messages: Annotated[List[BaseMessage], add_messages]
    payload: FNOLPayload
    is_form_complete: bool
    process_complete: bool
    api_call_successful: bool
    language: str


class FNOLAgent:
    """
    FNOL Voice Agent using LangGraph.
    
    Manages the conversation flow for collecting claim information
    through a voice-first interface.
    """
    
    def __init__(
        self,
        language: str = "en",
        use_memory: bool = True,
    ):
        """
        Initialize the FNOL agent.
        
        Args:
            language: Language code for the agent (default: 'en')
            use_memory: Whether to use checkpointing for conversation memory
        """
        self.language = language
        self.use_memory = use_memory
        
        # Initialize LLM
        self.llm = create_llm()
        
        # Create prompt template
        self.prompt = create_prompt_template(language)
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(AGENT_TOOLS)
        
        # Create the runnable chain
        self.chain = self.prompt | self.llm_with_tools
        
        # Create extractor for structured data extraction
        self.extractor = create_extractor(
            create_llm(),
            tools=[FNOLPayload],
            enable_inserts=True
        )
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the graph
        builder = StateGraph(AgentState)
        
        # Add nodes
        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", ToolNode(AGENT_TOOLS))
        builder.add_node("extractor", self._extractor_node)
        
        # Set entry point
        builder.set_entry_point("agent")
        
        # Add conditional edges
        builder.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                END: "extractor"
            }
        )
        
        # Tool output goes to extractor
        builder.add_edge("tools", "extractor")
        
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
        
        # Prepare state for the chain
        chain_input = {
            "messages": messages,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Get response from LLM
        response = await self.chain.ainvoke(chain_input, config)
        
        # Check if tool was called
        api_call_successful = False
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.get('name') == 'submit_claim':
                    api_call_successful = True
        
        return {
            "messages": [response],
            "api_call_successful": api_call_successful
        }
    
    async def _extractor_node(
        self, 
        state: AgentState, 
        config: RunnableConfig
    ) -> Dict[str, Any]:
        """
        Extractor node - extracts structured claim data from conversation.
        """
        payload_before = state.get("payload", create_default_payload())
        
        # Prepare existing data for the extractor
        existing_data = {}
        if payload_before:
            existing_data = {"FNOLPayload": payload_before.model_dump()}
        
        # Get recent messages for extraction
        recent_messages = state["messages"][-5:]
        
        # Prepare input for trustcall
        extractor_input = {"messages": recent_messages}
        if existing_data:
            extractor_input["existing"] = existing_data
        
        # Run extraction
        try:
            result = await self.extractor.ainvoke(extractor_input)
            
            updated_payload = payload_before
            if result.get("responses"):
                updated_payload = result["responses"][0]
            
            # Check if form is complete
            is_complete = updated_payload.is_complete() if updated_payload else False
            
            logger.info(f"Extraction complete. Form complete: {is_complete}")
            
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
            "payload": create_default_payload(),
            "is_form_complete": False,
            "process_complete": False,
            "api_call_successful": False,
            "language": self.language
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
                    if not is_conversation_start or last_message.content != "[CONVERSATION_START]":
                        response_text = last_message.content
        
        # Handle empty response for conversation start
        if is_conversation_start and not response_text:
            response_text = "Hello! I'm here to help you file your insurance claim. To begin, could you please tell me what happened?"
        
        # Get final payload
        payload = final_state.get("payload", create_default_payload()) if final_state else create_default_payload()
        is_complete = final_state.get("is_form_complete", False) if final_state else False
        
        return {
            "response": response_text,
            "payload": payload,
            "is_form_complete": is_complete,
            "api_call_successful": final_state.get("api_call_successful", False) if final_state else False
        }


# Singleton agent instance
_agent: Optional[FNOLAgent] = None


def create_agent(language: str = "en") -> FNOLAgent:
    """
    Factory function to create or get the FNOL agent.
    
    Args:
        language: Language code for the agent
        
    Returns:
        FNOLAgent instance
    """
    global _agent
    if _agent is None:
        _agent = FNOLAgent(language=language)
        logger.info(f"Created FNOL agent with language: {language}")
    return _agent


def reset_agent() -> None:
    """Reset the agent instance."""
    global _agent
    _agent = None
    logger.info("Agent reset")
