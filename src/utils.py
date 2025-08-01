from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode as BaseToolNode
import pgeocode
import pandas as pd
from src.schema import example_json
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from config.settings import settings
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Global LLM instances cache for singleton pattern
_llm_cache = {}

class AzureOpenAIWrapper:
    """
    Wrapper class to handle Azure OpenAI tool_choice compatibility.
    Converts 'any' tool_choice to 'auto' which is supported by Azure OpenAI.
    """
    def __init__(self, llm):
        self.llm = llm
        # Pass through all attributes to the wrapped LLM
        for attr in dir(llm):
            if not attr.startswith('_') and not callable(getattr(llm, attr)):
                setattr(self, attr, getattr(llm, attr))
    
    def bind_tools(self, tools, tool_choice=None, **kwargs):
        # Convert 'any' to 'auto' for Azure OpenAI compatibility
        if tool_choice == 'any':
            tool_choice = 'auto'
        return self.llm.bind_tools(tools, tool_choice=tool_choice, **kwargs)
    
    def __getattr__(self, name):
        # Delegate any other method calls to the wrapped LLM
        return getattr(self.llm, name)

def create_tool_node_with_fallback(tools: list) -> dict:
    return BaseToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def create_llm(azure_compatible=False, test_connection=False):
    """
    Factory function to create an LLM instance with caching for performance.
    
    This function tries to create an Azure OpenAI client first, and falls back to 
    regular OpenAI if Azure is not available or configured. It uses a singleton 
    pattern to cache instances and avoid expensive recreations.
    
    Args:
        azure_compatible (bool): If True, returns an AzureOpenAIWrapper that handles
                               tool_choice compatibility issues (e.g., converts 'any' to 'auto').
                               Defaults to False for backward compatibility.
        test_connection (bool): If True, tests the LLM connection with a simple call.
                              Defaults to False for better performance.
    
    Returns:
        AzureChatOpenAI, ChatOpenAI, or AzureOpenAIWrapper: The LLM instance, optionally wrapped.
    """
    # Create cache key based on configuration
    cache_key = f"azure_compatible_{azure_compatible}"
    
    # Return cached instance if available
    if cache_key in _llm_cache:
        print(">> Using cached LLM client...")
        return _llm_cache[cache_key]
    
    # Try Azure OpenAI first
    if settings.AZURE_OPENAI_API_KEY:
        print(">> Creating new Azure OpenAI client...")
        try:
            # Create the Azure LLM instance using environment variables
            llm = AzureChatOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                azure_deployment=settings.AZURE_DEPLOYMENT_NAME,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
                max_retries=settings.MAX_RETRIES,
            )
            print(">> Azure OpenAI client created successfully")
        except Exception as e:
            print(f">> Azure OpenAI failed: {e}")
            print(">> Falling back to regular OpenAI...")
            llm = None
    else:
        print(">> No Azure OpenAI API key found, using regular OpenAI...")
        llm = None
    
    # Fallback to regular OpenAI
    if llm is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("FATAL: Neither AZURE_OPENAI_API_KEY nor OPENAI_API_KEY is set.") from None
        
        llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
            max_retries=settings.MAX_RETRIES,
        )
        print(">> Regular OpenAI client created successfully")
    
    # Optional connection test (disabled by default for performance)
    if test_connection:
        print("----------------------------------------------------------------")
        print("Testing the llm...")
        print("----------------------------------------------------------------")
        try:
            print(llm.invoke("Tell me a joke."))
            print("----------------------------------------------------------------")
            print("-----LLM tested SUCCESSFULLY-----")
            print("----------------------------------------------------------------")
        except Exception as e:
            print(f"LLM test failed: {e}")
            print("----------------------------------------------------------------")
    
    # Wrap if azure_compatible is True (only for Azure OpenAI)
    if azure_compatible and isinstance(llm, AzureChatOpenAI):
        print(">> Wrapping LLM for Azure OpenAI compatibility (tool_choice fixes)")
        llm = AzureOpenAIWrapper(llm)
    
    # Cache the instance
    _llm_cache[cache_key] = llm
    print(">> LLM client created and cached successfully")
    
    return llm

def handle_tool_error(state) -> dict:
    error = state.get("error")
    retry_count = state.get("api_retry_count", 0)
    
    if retry_count >= 2:
        return {
            "messages": [
                ToolMessage(
                    content="API call failed multiple times. Concluding the conversation.",
                    tool_call_id=state["messages"][-1].tool_calls[0]["id"],
                )
            ],
            "process_complete": True    
        }
    
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ],
        "api_retry_count": retry_count + 1
    }

def _print_event(event: dict, _printed: set, max_length=1500):
    """
    Optimized event printing with performance improvements.
    
    Performance optimizations:
    - Early returns to avoid processing
    - Optimized string operations
    - Memory-efficient message handling
    """
    # Early return if no relevant data
    if not event:
        return
        
    current_state = event.get("dialog_state")
    if current_state:
        print("Currently in: ", current_state[-1])
        
    message = event.get("messages")
    if not message:
        return
        
    # Handle message list efficiently
    if isinstance(message, list):
        if not message:  # Empty list
            return
        message = message[-1]
    
    # Check if already printed to avoid duplicates
    if hasattr(message, 'id') and message.id in _printed:
        return
        
    # Process message content
    if hasattr(message, 'pretty_repr'):
        try:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            print(msg_repr)
            
            # Add to printed set
            if hasattr(message, 'id'):
                _printed.add(message.id)
        except Exception as e:
            print(f"Error printing message: {e}")

def get_mermaid_code(graph):

    mermaid_code = graph.get_graph(xray=True).draw_mermaid()
    
    print("=== MERMAID GRAPH CODE ===")
    print(mermaid_code)
    print("=========================")
    
    # Save to file for easy copying
    with open("graph.mmd", "w") as f:
        f.write(mermaid_code)
    
    print(f"Mermaid code also saved to: graph.mmd")
    print("You can copy this code and paste it into:")
    print("- https://mermaid.live/")
    print("- https://mermaid-js.github.io/mermaid-live-editor/")

def get_city_state(zip_code):
    nomi = pgeocode.Nominatim('us')  # Use 'us' for United States, change as needed
    location = nomi.query_postal_code(zip_code)
    
    if pd.notnull(location.place_name) and pd.notnull(location.state_code):
        return location.place_name, location.state_code
    else:
        return None, None

def check_payload_completeness(state) -> bool:
    """
    Optimized check for payload completeness with better performance.
    
    Performance optimizations:
    - Early returns to avoid unnecessary computations
    - Cached example data comparison
    - Minimal memory allocation
    """
    
    # Early return for missing state or payload
    if not state.get("payload") or not state["payload"].claim:
        return False
    
    try:
        claim = state["payload"].claim.model_dump()
    except (AttributeError, TypeError):
        return False

    print("Checking payload completeness...")
    
    # Cache example data for comparison (static, computed once)
    if not hasattr(check_payload_completeness, '_example_cache'):
        check_payload_completeness._example_cache = {
            'policy_number': example_json["policy"]["number"],
            'insured_name': example_json["insured"]["full_name"],
            'incident_datetime': example_json["incident"]["datetime"],
            'incident_city': example_json["incident"]["location"]["city"],
            'incident_state': example_json["incident"]["location"]["state"],
            'vehicles_involved': example_json["incident"]["vehicles_involved"]
        }
    
    cache = check_payload_completeness._example_cache
    
    # Optimized required field checks with early termination
    required_checks = [
        # claim["claim_id"] != example_json["claim_id"],
        claim.get("policy", {}).get("number") != cache['policy_number'],
        claim.get("insured", {}).get("full_name") != cache['insured_name'],
        claim.get("incident", {}).get("datetime") != cache['incident_datetime'],
        claim.get("incident", {}).get("location", {}).get("city") != cache['incident_city'],
        claim.get("incident", {}).get("location", {}).get("state") != cache['incident_state'],
        claim.get("incident", {}).get("vehicles_involved") != cache['vehicles_involved']
    ]
    
    # Use all() for short-circuit evaluation
    return all(required_checks)