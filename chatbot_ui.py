import streamlit as st
import os
from main import agent_executor, parser
from tools import capture_screenshot

st.set_page_config(page_title="AI Agent Chat", page_icon="🤖")
st.title("AI Agent Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history first
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Display screenshot if it exists
        if msg["role"] == "assistant" and "screenshot" in msg:
            if os.path.exists(msg["screenshot"]):
                st.image(msg["screenshot"], caption="Medplum View After Automation", use_container_width=True)

# Chat input
user_input = st.chat_input("What can I help you with?")

def run_agent(query):
    """Run agent and capture screenshot"""
    try:
        # ✅ FIXED: Use "input" instead of "query" to match prompt template
        response = agent_executor.invoke({"input": query})
        output = response.get("output", "")
        
        # Try to parse structured output
        try:
            structured = parser.parse(output)
            final_output = f"""
{structured.message}

**Evidence:**
{chr(10).join(['- ' + e for e in structured.evidence])}

**Next Actions:**
{chr(10).join(['- ' + a for a in structured.next_actions])}

**Completed Steps:**
{chr(10).join(['- ' + s for s in structured.completed_steps])}

**Collected Data:**
{chr(10).join([f'- {k}: {v}' for k, v in structured.data_collected.items()])}
""".strip()
        except Exception:
            final_output = output
        
        # Capture screenshot
        screenshot_path = f"screenshots/screenshot_{len(st.session_state.messages)}.png"
        os.makedirs("screenshots", exist_ok=True)
        
        # Take screenshot using the tool
        screenshot_result = capture_screenshot(screenshot_path)
        
        # Check if screenshot was successful
        if "success" in screenshot_result and os.path.exists(screenshot_path):
            return final_output, screenshot_path
        else:
            return final_output, None
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Agent failed: {str(e)}\n\n{traceback.format_exc()}"
        return error_msg, None

# Process new input
if user_input:
    # Add and display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Run agent with spinner
    with st.chat_message("assistant"):
        with st.spinner("🤖 Processing..."):
            output, screenshot_path = run_agent(user_input)
        
        # Display response
        st.markdown(output)
        
        # Display and save screenshot
        if screenshot_path and os.path.exists(screenshot_path):
            st.image(screenshot_path, caption="Medplum View After Automation", use_container_width=True)
            # Save message with screenshot
            st.session_state.messages.append({
                "role": "assistant", 
                "content": output,
                "screenshot": screenshot_path
            })
        else:
            st.warning("⚠️ No screenshot captured")
            st.session_state.messages.append({
                "role": "assistant", 
                "content": output
            })