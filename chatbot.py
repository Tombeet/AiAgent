import streamlit as st
import re
import os
from api_client import run_agent_via_api

def run_agent(query):
    """Send query to background service and return response and evidence."""
    try:
        session_id = st.session_state["session_id"]
        response = run_agent_via_api(session_id, query)
        if response.get("status") == "success":
            output = response.get("output", "")
            screenshot_path = response.get("screenshot_path")  # <-- get from API response
            return output, screenshot_path
        else:
            return f"❌ Agent failed: {response.get('error', 'Unknown error')}", None
    except Exception as e:
        import traceback
        error_msg = f"❌ Agent failed: {str(e)}\n\n{traceback.format_exc()}"
        return error_msg, None

# Streamlit UI/front 
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


# Generate or get a session_id for the user (per browser session)
if "session_id" not in st.session_state:
    import uuid
    st.session_state["session_id"] = str(uuid.uuid4())


# Process new input
if user_input:
    # Add and display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Run agent with spinner
    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking..."):
            # Generate or get a session_id for the user (per browser session)
            if "session_id" not in st.session_state:
                import uuid
                st.session_state["session_id"] = str(uuid.uuid4())
            
            # Send user input to agent and get response
            output, screenshot_path = run_agent(user_input)
            
            # Try to extract screenshot path from Markdown if not returned directly
            if not screenshot_path:
                m = re.search(r'!\[.*?\]\((.*?)\)', output)
                if m:
                    possible_path = m.group(1)
                    if os.path.exists(possible_path):
                        screenshot_path = possible_path

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