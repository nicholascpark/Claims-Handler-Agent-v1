from langchain_core.runnables import Runnable, RunnableConfig
from src.schema import FNOLPayload
from config.settings import settings
from langchain_openai import ChatOpenAI
from trustcall import create_extractor
from src.state import ConvoState
from dotenv import load_dotenv
from src.prompts import primary_assistant_prompt
from src.tools import get_preliminary_estimate
from src.utils import check_payload_completeness
import httpx
import ssl

load_dotenv()

# Create custom httpx client with SSL verification disabled for corporate networks
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

custom_httpx_client = httpx.Client(
    verify=False,
    timeout=httpx.Timeout(60.0)
)

# Configure ChatOpenAI clients with SSL workaround
llm_agent = ChatOpenAI(
    model=settings.MODEL_NAME, 
    temperature=settings.TEMPERATURE,
    http_client=custom_httpx_client
)
llm_extractor = ChatOpenAI(
    model=settings.MODEL_NAME, 
    temperature=settings.TEMPERATURE,
    http_client=custom_httpx_client
)

class Agent:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: ConvoState, config: RunnableConfig):
        while True:
            result = self.runnable.invoke(state)
            # print(result.tool_calls)
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        
        # Check if there's a proper API response in the recent messages
        api_call_successful = self._check_for_api_response(state["messages"])
        
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

    def __call__(self, state: ConvoState, config: RunnableConfig):
        # Store current payload for comparison
        payload_before = state.get("payload")
        
        # Prepare existing data for trustcall's patch operations
        existing_data = {}
        if payload_before:
            # Convert existing payload to dict for trustcall
            existing_data = {"FNOLPayload": payload_before.model_dump()}
        
        # Prepare the input for trustcall with existing data
        trustcall_input = {
            "messages": state["messages"],
        }
        
        # Add existing data if we have it
        if existing_data:
            trustcall_input["existing"] = existing_data
        
        # Invoke trustcall extractor
        result = self.runnable.invoke(trustcall_input)
        
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
