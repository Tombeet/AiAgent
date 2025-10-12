import streamlit as st
import os
import time

from main import agent_executor, parser
from tools import capture_screenshot

st.set_page_config(page_title="AI Agent Chat", page_icon="💬")
st.title("AI Agent Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "latest_output" not in st.session_state:
    st.session_state.latest_output = ""

user_input = st.text_input("What can I help you with?")
start_button = st.button("Send")

# Placeholder for screenshots
screenshot_display = st.empty()

def run_agent(query):
    try:
        response = agent_executor.invoke({"query": query})
        output = response.get("output", "")

        try:
            structured = parser.parse(output)
            pretty = f"""
{structured.message}

Tools Used:
- {'\n- '.join(structured.tools_used)}

Evidence:
- {'\n- '.join(structured.evidence)}

Next Actions:
- {'\n- '.join(structured.next_actions)}

Completed Steps:
- {'\n- '.join(structured.completed_steps)}

Collected Data:
- {chr(10).join([f"{k}: {v}" for k, v in structured.data_collected.items()])}
"""
            return pretty.strip()
        except Exception:
            return output
    except Exception as e:
        return f"Agent failed: {e}"

# --- Main run logic ---
if start_button and user_input.strip():
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run agent (no threading)
    output = run_agent(user_input)
    st.session_state.latest_output = output

    # Capture screenshot after agent run
    try:
        path = "latest_screenshot.png"
        if os.path.exists(path):
            os.remove(path)
        capture_screenshot(path)
        screenshot_display.image(path, caption="Medplum View After Automation", use_container_width=True)
    except Exception as e:
        screenshot_display.warning(f"Could not capture screenshot: {e}")

    # Display final output
    with st.chat_message("assistant"):
        st.text(output)
        st.session_state.messages.append({"role": "assistant", "content": output})

# Show full chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
