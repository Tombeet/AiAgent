import streamlit as st
import os
from main import agent_executor, parser
from tools import screenshot  # Changed from capture_screenshot

st.set_page_config(page_title="AI Agent Chat", page_icon="🤖")
st.title("🤖 Autonomous AI Agent")

# Sidebar with controls
with st.sidebar:
    st.header("Controls")
    
    if st.button("🔒 Close Browser", help="Close the browser to free resources"):
        try:
            from tools import cleanup_browser
            cleanup_browser()
            st.success("Browser closed successfully!")
        except Exception as e:
            st.error(f"Error closing browser: {e}")
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This is a **fully autonomous agent** that:
    - 🧠 Thinks and adapts
    - 👀 Observes pages before acting
    - 🔄 Handles multi-turn conversations
    - 📸 Captures evidence
    
    The browser stays open across messages for faster responses.
    """)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Display screenshot if it exists
        if msg["role"] == "assistant" and "screenshot" in msg:
            if os.path.exists(msg["screenshot"]):
                st.image(msg["screenshot"], caption="Agent Evidence", use_container_width=True)

# Chat input
user_input = st.chat_input("What can I help you with?")

def run_agent(query):
    """Run autonomous agent and capture screenshot"""
    try:
        # ✅ Use "query" to match the autonomous agent's prompt template
        response = agent_executor.invoke({"query": query})
        output = response.get("output", "")
        
        # Try to parse structured output
        try:
            structured = parser.parse(output)
            final_output = f"""
{structured.message}

**Status:** {structured.status}

**Tools Used:**
{chr(10).join(['- ' + t for t in structured.tools_used])}

**Evidence:**
{chr(10).join(['- ' + e for e in structured.evidence])}

**Completed Steps:**
{chr(10).join(['- ' + s for s in structured.completed_steps])}

**Data Collected:**
{chr(10).join([f'- {k}: {v}' for k, v in structured.data_collected.items()])}
""".strip()
        except Exception:
            # Not structured output - just conversational response
            final_output = output
        
        # Capture screenshot using autonomous tool
        screenshot_path = f"screenshots/screenshot_{len(st.session_state.messages)}.png"
        os.makedirs("screenshots", exist_ok=True)
        
        # Take screenshot using the autonomous screenshot tool
        try:
            screenshot_result = screenshot(screenshot_path)
            
            # Check if screenshot was successful
            if "success" in screenshot_result and os.path.exists(screenshot_path):
                result = (final_output, screenshot_path)
            else:
                result = (final_output, None)
        except:
            # Screenshot failed - that's okay
            result = (final_output, None)
        
        # ⚠️ DON'T clean up browser here - let it stay alive for multi-turn conversations
        # Browser will auto-recover if it dies (ensure_browser checks health)
        
        return result
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Agent failed: {str(e)}\n\n{traceback.format_exc()}"
        
        # Only clean up browser on critical errors
        try:
            from tools import cleanup_browser
            cleanup_browser()
        except:
            pass
        
        return error_msg, None

# Process new input
if user_input:
    # Add and display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Run agent with spinner
    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking..."):
            output, screenshot_path = run_agent(user_input)
        
        # Display response
        st.markdown(output)
        
        # Display and save screenshot
        if screenshot_path and os.path.exists(screenshot_path):
            st.image(screenshot_path, caption="Agent Evidence", use_container_width=True)
            # Save message with screenshot
            st.session_state.messages.append({
                "role": "assistant", 
                "content": output,
                "screenshot": screenshot_path
            })
        else:
            st.session_state.messages.append({
                "role": "assistant", 
                "content": output
            })