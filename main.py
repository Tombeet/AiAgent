"""
Autonomous AI Agent for Medplum EMR System
Uses primitive tools to figure out workflows dynamically
"""

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from tools import (
    goto_url, read_page, click, type_in_field, 
    wait_for, get_secret, screenshot, 
    get_current_location, validate_claim_advanced
)
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Primitive tools - building blocks only
tools = [
    goto_url,
    read_page, 
    click,
    type_in_field,
    wait_for,
    get_secret,
    screenshot,
    get_current_location,
    validate_claim_advanced
]

# Minimal autonomous prompt - no hand-holding
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an autonomous AI agent working with Medplum EMR system at https://app.medplum.com.

You have 9 primitive tools to accomplish any task:
1. goto_url(url) - Navigate anywhere
2. read_page() - See what's on the page  
3. click(target) - Click anything
4. type_in_field(field, value) - Fill any field
5. wait_for(condition) - Wait for loading
6. get_secret(key) - Get credentials (MEDPLUM_USER, MEDPLUM_PASS)
7. screenshot(filename) - Capture evidence
8. get_current_location() - Know where you are
9. validate_claim_advanced(claim) - Verify with AI vision

YOUR JOB: Figure out how to accomplish tasks by observing and adapting.

CORE PRINCIPLES:
1. Always read_page() to observe before acting
2. Think step-by-step - break tasks into small steps
3. Adapt to what you see - don't assume structure
4. Verify your work with screenshots and validation
5. If something fails, observe and try a different approach

You must login before doing any EMR tasks. Medplum uses two-step login (email first, then password).

When users ask you to create/find/update resources, ask them for any missing information you need. Be conversational and helpful.
"""
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=30
)

def run_query(query: str) -> str:
    """Run a query through the autonomous agent"""
    try:
        result = agent_executor.invoke({"input": query})
        return result.get("output", "No response")
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 AUTONOMOUS AGENT - MINIMAL GUIDANCE MODE")
    print("="*60)
    print("BASE_URL: https://app.medplum.com")
    print(f"Credentials: {'✅ Loaded' if os.getenv('MEDPLUM_USER') else '❌ Missing'}")
    print("="*60)
    print(f"\n✅ Loaded {len(tools)} primitive tools")
    print("🤖 Agent will figure out workflows by observing!")
    print()