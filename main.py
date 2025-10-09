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
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# ---------- Prompt (matches your agent template) ----------
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an autonomous web-automation agent that is responsible for managing the Electronic Medical Records (EMR) System. "
            "Always carry out tasks using the admin account "
            "always wait for pages to load completely before taking actions"
            "Interact with the user to get context use the necessary tools to complete the task. "
            "If you cannot find the expected input fields or encounter errors,use the read_texts tool to gather page context and click_text tool re-try the task with other approaches. As last resort return to main/landing page and re try the process from there"
            "Prioritize Navigation after logging in by clicking visible buttons or links using the click_text tool if possible."
            "Return ONLY a JSON object matching this schema:\n{format_instructions}\n"
            
        
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
    max_iterations=100,
)

if __name__ == "__main__":
    while True:
        query = input("What can i help you with?\n> ").strip()
        if not query:
            break

        result = agent_executor.invoke({"query": query})
        
        # Try to parse as JSON, if fails, treat as conversation
        try:
            structured = parser.parse(result["output"])
            print("\n=== Result ===")
            print(structured.json(indent=2, ensure_ascii=False))
            if structured.status == "success":
                break
        except Exception:
            # If not JSON, it's a conversation response
            print("\n" + result["output"])
            continue
