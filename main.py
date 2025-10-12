# main.py code
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory

# Import the unified tools list from your tools.py
from tools import TOOLS  # [nav, read_texts, click_text, fill_name, submit, get_secret, close]

load_dotenv()

# ---------- Structured output model (Pydantic) ----------
class AutomationResult(BaseModel):
    status: str  # "in_progress", "completed", "error"
    message: str
    tools_used: list[str]
    evidence: list[str]
    next_actions: list[str]
    completed_steps: list[str] = []  # Track what's been done
    data_collected: dict = {}        # Store collected user info

parser = PydanticOutputParser(pydantic_object=AutomationResult)

# ---------- LLM ----------
llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

# ---------- Prompt (matches your agent template) ----------
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Role:
You are an Electronic Medical Record (EMR) system administrator agent responsible for executing administrative tasks within the clinic's EMR system.

Objectives:
1) Interact with the user to understand and gather context for their request.
2) Log in into the EMR system using your admin credentials before executing any tasks.
3) Safely execute the required actions within the EMR system to complete the request.
4) Validate the outcome of the task using the tool validate_claim_advanced.
5) Based on the outcome of the validation, provide the exact information requested by the user.

Guardrails:
- After logging in, navigate using on-page actions (e.g., clicks, buttons, forms). 
- DO not carry out any actions until you have been authenticated into the emr system successfully.
- Always start from the main/landing page when executing a new task.
- If encountering repeated failures more than twice, reset to main page and use a different workflow and set of tools, do not get stuck in a loop.
- Always validate the outcome of the task before responding to the user.
- Never share your admin credentials under any cicumstances
- only execute tasks relating to patient onboarding and information retireval
Response Format:
- When gathering information or clarifying requirements: Respond conversationally
- ALWAYS respond outcome of task in this JSON Schema (use only for final task outcomes):
{format_instructions}
"""
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())


# ---------- Agent (same construction pattern as your template) ----------
agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=TOOLS,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=TOOLS,
    verbose=True,
    memory=ConversationBufferMemory(memory_key="chat_history", return_messages=True),
    max_iterations=80,
)

if __name__ == "__main__":
    while True:
        query = input("\n> ").strip()
        
        if not query or query.lower() in ['exit', 'quit', 'bye']:
            print("Session ended.")
            break
        
        try:
            result = agent_executor.invoke({"query": query})
            
            # Try to parse as JSON first
            try:
                structured = parser.parse(result["output"])
                
                # This is a completed task with JSON output
                print(f"\nResponse: {structured.message}")
                
                # Raw JSON output
                print(f"\nJSON Output:")
                print(structured.model_dump_json(indent=2))
                
                # Exit after successful task completion
                if structured.status.lower() in ["completed", "success", "succeeded"]:
                    print("\nTask completed successfully. Session ended.")
                    break
                else:
                    print("\nTask incomplete. You can provide more information or try again.")
                    continue
      
            except Exception as e:
                # This is conversational response (gathering info)
                print(f"\n{result['output']}")
                # Continue the conversation - don't exit
                continue
                
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("You can try again or type 'exit' to quit.")
            continue
