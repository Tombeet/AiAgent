# main_alternate.py - Using partial_variables approach
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

# Load environment variables
load_dotenv()

# Import tools correctly
from tools import TOOLS

# Define your output parser structure
class AgentResponse(BaseModel):
    """Structured response from the agent"""
    message: str = Field(description="Main response message")
    evidence: list[str] = Field(default_factory=list, description="Evidence collected")
    next_actions: list[str] = Field(default_factory=list, description="Next steps")
    completed_steps: list[str] = Field(default_factory=list, description="Completed actions")
    data_collected: dict = Field(default_factory=dict, description="Data gathered")

# Create parser
parser = PydanticOutputParser(pydantic_object=AgentResponse)

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=4000
)

# Create tool descriptions
tool_strings = "\n".join([f"{tool.name}: {tool.description}" for tool in TOOLS])
tool_names_str = ", ".join([tool.name for tool in TOOLS])

# Proper prompt template with correct variables
prompt_template = """You are an AI assistant that helps automate tasks in the Medplum EMR system.

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT WORKFLOW:
1. ALWAYS start with: medplum_login()
2. Navigate to resources: navigate_to_resource('Patient') or navigate_to_resource('Patient', 'id')
3. Read page context: read_texts()
4. Perform actions: click_text(), fill_field(), smart_search()
5. Validate: validate_claim_advanced()
6. Take evidence: capture_screenshot()

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

# OPTION 1: Use partial_variables (cleaner)
prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad"],
    partial_variables={
        "tools": tool_strings,
        "tool_names": tool_names_str
    },
    template=prompt_template,
)

# Create agent
agent = create_react_agent(
    llm=llm,
    tools=TOOLS,
    prompt=prompt
)

# Create agent executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=TOOLS,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=80,
    max_execution_time=300
)

# Test function
def test_agent():
    """Test the agent setup"""
    print("=" * 60)
    print("TESTING AGENT CONFIGURATION")
    print("=" * 60)
    print(f"Number of tools: {len(TOOLS)}")
    print(f"Tool names: {[tool.name for tool in TOOLS]}")
    print()
    
    try:
        print("Testing with simple query...")
        result = agent_executor.invoke({"input": "What tools do you have access to?"})
        print("\n✅ Agent Response:")
        print(result.get("output", "No output"))
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent()