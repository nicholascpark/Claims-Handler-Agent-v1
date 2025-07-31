from langchain_core.runnables import Runnable, RunnableConfig
from src.schema import FNOLPayload
from config.settings import settings
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from trustcall import create_extractor
from src.state import ConvoState
from dotenv import load_dotenv
from src.prompts import primary_assistant_prompt
from src.tools import get_preliminary_estimate
from src.utils import check_payload_completeness, create_llm
from datetime import datetime
import time
import hashlib

# Lazy imports for better performance
def _get_ssl_context():
    """Lazy import SSL context to avoid loading unless needed"""
    try:
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    except ImportError:
        return None

def _get_custom_httpx_client():
    """Lazy import and create custom httpx client"""
    try:
        import httpx
        return httpx.Client(
            verify=False,
            timeout=httpx.Timeout(60.0)
        )
    except ImportError:
        return None

load_dotenv()

# Create custom httpx client with SSL verification disabled for corporate networks
# ssl_context = ssl.create_default_context()
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

# custom_httpx_client = httpx.Client(
#     verify=False,
#     timeout=httpx.Timeout(60.0)
# )

# Use cached LLM instances for better performance
llm_agent = create_llm()
llm_extractor = create_llm(azure_compatible=True)

# LLM response cache for performance optimization
LLM_RESPONSE_CACHE = {}
CACHE_MAX_SIZE = 200
CACHE_TTL = 1800  # 30 minutes

class Agent:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def _get_cache_key(self, messages):
        """Generate cache key for LLM responses based on message content"""
        # Create a hash of the last few messages for caching
        content_to_hash = ""
        for msg in messages[-3:]:  # Use last 3 messages for context
            if hasattr(msg, 'content'):
                content_to_hash += str(msg.content)
        return hashlib.md5(content_to_hash.encode()).hexdigest()

    def _get_cached_response(self, cache_key):
        """Get cached LLM response if available and not expired"""
        if cache_key in LLM_RESPONSE_CACHE:
            response, timestamp = LLM_RESPONSE_CACHE[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                print(f"LLM cache hit for key: {cache_key[:8]}...")
                return response
            else:
                # Remove expired entry
                del LLM_RESPONSE_CACHE[cache_key]
        return None

    def _cache_response(self, cache_key, response):
        """Cache LLM response with timestamp"""
        LLM_RESPONSE_CACHE[cache_key] = (response, time.time())
        
        # Simple LRU: remove oldest entries if cache is full
        if len(LLM_RESPONSE_CACHE) > CACHE_MAX_SIZE:
            oldest_key = min(LLM_RESPONSE_CACHE.keys(), 
                           key=lambda k: LLM_RESPONSE_CACHE[k][1])
            del LLM_RESPONSE_CACHE[oldest_key]

    async def __call__(self, state: ConvoState, config: RunnableConfig):
        # Ensure the system prompt is properly included in every call
        messages = state.get("messages", [])
        
        # Check if this is the conversation start
        is_conversation_start = (
            len(messages) == 1 and 
            hasattr(messages[0], 'content') and 
            messages[0].content == "[CONVERSATION_START]"
        )
        
        # Try cache first for non-conversation-start messages
        cache_key = None
        if not is_conversation_start and len(messages) > 0:
            cache_key = self._get_cache_key(messages)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                # Check if there's a proper API response in the recent messages
                api_call_successful = self._check_for_api_response(messages)
                return {
                    "messages": [cached_response],
                    "api_call_successful": api_call_successful
                }
        
        # Create a proper state with all necessary context
        enhanced_state = {
            "messages": messages,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        result = await self.runnable.ainvoke(enhanced_state)
        
        # Cache the response if we have a cache key
        if cache_key and not is_conversation_start:
            self._cache_response(cache_key, result)
        
        # Check if there's a proper API response in the recent messages
        api_call_successful = self._check_for_api_response(messages)
        
        return {
            "messages": [result],
            "api_call_successful": api_call_successful
        }
    
    def _check_for_api_response(self, messages):
        """Check if the recent messages contain a successful API tool response."""
        # Look through recent messages for tool messages containing API responses
        for message in reversed(messages[-10:]):  # Check last 10 messages
            if hasattr(message, 'type') and message.type == 'tool':
                # Check if this is a response from get_preliminary_estimate tool
                if hasattr(message, 'name') and message.name == 'get_preliminary_estimate':
                    try:
                        # If the content contains response data (not an error), consider it successful
                        if message.content and not message.content.startswith('Error'):
                            return True
                    except:
                        continue
        return False

all_tools = [get_preliminary_estimate]
primary_assistant_chain = primary_assistant_prompt | llm_agent.bind_tools(all_tools)
agent = Agent(primary_assistant_chain)

class Extractor:
    def __init__(self, tools):
        self.llm_extractor = llm_extractor
        self.runnable = create_extractor(self.llm_extractor, tools=tools, enable_inserts=True)

    async def __call__(self, state: ConvoState, config: RunnableConfig):
        # Store current payload for comparison
        payload_before = state.get("payload")
        
        # Prepare existing data for trustcall's patch operations
        existing_data = {}
        if payload_before:
            # Convert existing payload to dict for trustcall
            existing_data = {"FNOLPayload": payload_before.model_dump()}
        
        # Prepare the input for trustcall with existing data
        recent_messages = state["messages"][-5:] 
        trustcall_input = {"messages": recent_messages}

        # Add existing data if we have it
        if existing_data:
            trustcall_input["existing"] = existing_data
        
        # Invoke trustcall extractor
        result = await self.runnable.ainvoke(trustcall_input)
        
        # print('\n Trustcall Result: ', result)
        # print('\nResponse metadata: ', result.get("response_metadata", []))
        
        updated_payload = None
        patches_applied = []
        
        if result.get("responses"):
            updated_payload = result["responses"][0]
            # Track patch information if available
            response_metadata = result.get("response_metadata", [])
            for meta in response_metadata:
                if "patches" in meta:
                    patches_applied.extend(meta["patches"])
        
        # Check payload completeness and update form completion status
        temp_state = {**state, "payload": updated_payload}
        is_complete = check_payload_completeness(temp_state)

        print('\nIs complete: ', is_complete, '\n')

        print('\nPayload: ', updated_payload, '\n')

        return {
            "payload": updated_payload,
            "is_form_complete": is_complete,
        }
    
extractor = Extractor(tools=[FNOLPayload])
