"""
Simple Streamlit UI for Autonomous Agent
"""

import streamlit as st
import os
from main import agent_executor

st.set_page_config(page_title="AI Agent", page_icon="🤖")
st.title("🤖 Autonomous EMR Agent")

# Simple sidebar
with st.sidebar:
    st.header("About")
    st.markdown("""
    Autonomous AI agent with primitive tools.
    
    Figures out workflows by observing and adapting.
    """)
    
    if st.button("🔒 Close Browser"):
        try:
            from tools import cleanup_browser
            cleanup_browser()
            st.success("Browser closed")
        except Exception as e:
            st.error(f"Error: {e}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "screenshot" in message and message["screenshot"]:
            if os.path.exists(message["screenshot"]):
                st.image(message["screenshot"], width=400)

# Chat input
if prompt := st.chat_input("What would you like me to do?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = agent_executor.invoke({"input": prompt})
                output = response.get("output", "No response")
                st.markdown(output)
                
                # Try to find and display latest screenshot
                screenshot_path = None
                screenshots_dir = "screenshots"
                if os.path.exists(screenshots_dir):
                    screenshots = sorted(
                        [f for f in os.listdir(screenshots_dir) if f.endswith('.png')],
                        key=lambda x: os.path.getmtime(os.path.join(screenshots_dir, x)),
                        reverse=True
                    )
                    if screenshots:
                        screenshot_path = os.path.join(screenshots_dir, screenshots[0])
                        st.image(screenshot_path, width=400)
                
                # Add to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": output,
                    "screenshot": screenshot_path
                })
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "screenshot": None
                })