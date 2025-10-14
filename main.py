# main.py - Fully Autonomous Agent
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory

from tools import TOOLS

load_dotenv()

# Structured output model
class AutomationResult(BaseModel):
    status: str  # "in_progress", "completed", "error"
    message: str
    tools_used: list[str]
    evidence: list[str]
    next_actions: list[str]
    completed_steps: list[str] = []
    data_collected: dict = {}

parser = PydanticOutputParser(pydantic_object=AutomationResult)

llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

# Autonomous agent prompt
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an autonomous EMR system agent with the ability to think and adapt.

YOUR CAPABILITIES:
You have 9 primitive tools - building blocks to accomplish ANY task:
1. goto_url(url) - Navigate anywhere
2. read_page() - Observe what's on the page
3. click(target) - Click anything
4. type_in_field(field, value) - Fill any field
5. wait_for(condition, seconds) - Wait for loading
6. get_secret(key) - Get credentials
7. screenshot(filename) - Capture evidence
8. get_current_location() - Know where you are
9. validate_claim_advanced(claim) - Verify with AI vision

YOUR MISSION:
Figure out workflows by OBSERVING and ADAPTING. You are NOT given pre-built workflows.

CORE PRINCIPLES:

1. OBSERVE FIRST, ACT SECOND
   - Always call read_page() when arriving at a new page
   - Always call read_page() after clicking something that might change the page
   - Never assume what's on a page - always observe

2. THINK STEP-BY-STEP
   - Break complex tasks into small steps
   - Verify each step worked before moving to the next
   - Example workflow you should figure out:
     
     To login:
     Step 1: goto_url('https://app.medplum.com/signin')
     Step 2: read_page() to see what fields exist
     Step 3: get_secret('MEDPLUM_USER') to get email
     Step 4: type_in_field('email', 'the_email_value')
     Step 5: read_page() to see if anything changed
     Step 6: click('Next') if there's a Next button
     Step 7: wait_for('page_load')
     Step 8: read_page() to see the new page
     Step 9: get_secret('MEDPLUM_PASS') to get password
     Step 10: type_in_field('password', 'the_password_value')
     Step 11: click('Sign in')
     Step 12: wait_for('page_load')
     Step 13: read_page() to verify login succeeded
     
     To create a patient:
     Step 1: Ensure you're logged in
     Step 2: goto_url('https://app.medplum.com/Patient')
     Step 3: read_page() to see what's available
     Step 4: Look for creation buttons (New, Create, Add)
     Step 5: click('New...')  # Or whatever button you found
     Step 6: wait_for('page_load')
     Step 7: read_page() to see the form fields
     Step 8: type_in_field('given', 'FirstName')
     Step 9: type_in_field('family', 'LastName')
     Step 10: Fill other fields if requested (birthDate, gender, etc)
     Step 11: read_page() to find save button
     Step 12: click('Save')
     Step 13: wait_for('page_load')
     Step 14: get_current_location() to see if URL changed to patient page
     Step 15: screenshot('patient_created.png')
     Step 16: validate_claim_advanced('Patient was created')

3. ADAPT TO WHAT YOU SEE
   - If a button doesn't exist, look for alternatives
   - If a field has a different name, adapt
   - If something fails, read_page() to understand why
   - Learn from the page structure

4. HANDLE FAILURES GRACEFULLY
   - If click fails: read_page() to see what's actually there
   - If field not found: read_page() to see what fields exist
   - If stuck: goto_url() to reset and try again
   - If repeated failures: explain what went wrong

5. VALIDATE YOUR WORK
   - After completing a task, take screenshot()
   - Use validate_claim_advanced() to verify success
   - Check get_current_location() to confirm state changes

AUTHENTICATION:
- You MUST login before doing any EMR tasks
- Use get_secret() to retrieve credentials
- Medplum uses two-step login: email first, then password
- Never hard-code credentials

RESPONSE FORMAT:
- When gathering info or clarifying: Respond conversationally
- When task is complete: Use JSON schema (provided below)

{format_instructions}

REMEMBER: You are AUTONOMOUS. Figure out the workflow by observing!
"""
    ),
    ("placeholder", "{chat_history}"),
    ("human", "{query}"),
    ("placeholder", "{agent_scratchpad}"),
]).partial(format_instructions=parser.get_format_instructions())

# Create agent
agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=TOOLS)

agent_executor = AgentExecutor(
    agent=agent,
    tools=TOOLS,
    verbose=True,
    memory=ConversationBufferMemory(memory_key="chat_history", return_messages=True),
    max_iterations=50,  # More iterations for autonomous thinking
    max_execution_time=300,
)

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🤖 AUTONOMOUS EMR AGENT")
    print("=" * 70)
    print("This agent figures out workflows by itself!")
    print("Try: 'Create a patient named Jimmy Smith'")
    print("     'Login to Medplum'")
    print("     'Search for patients named John'")
    print("=" * 70 + "\n")
    
    while True:
        query = input("\n> How can I help you? ").strip()
        
        if not query or query.lower() in ['exit', 'quit', 'bye']:
            print("👋 Session ended.")
            break
        
        try:
            result = agent_executor.invoke({"query": query})
            
            # Try to parse as structured output
            try:
                structured = parser.parse(result["output"])
                
                print(f"\n✅ {structured.message}")
                print(f"\nSTATUS: {structured.status}")
                print(f"TOOLS USED: {', '.join(structured.tools_used)}")
                print(f"EVIDENCE: {', '.join(structured.evidence)}")
                
                if structured.status.lower() in ["completed", "success"]:
                    print("\n✅ Task completed!")
                
            except:
                # Conversational response
                print(f"\n{result['output']}")
                
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("You can try again or type 'exit' to quit.")