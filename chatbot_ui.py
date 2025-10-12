import streamlit as st
import os
import concurrent.futures

from main import agent_executor, parser
from tools import capture_screenshot

st.set_page_config(page_title="AI Agent Chat", page_icon="🤖")
st.title("AI Agent Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "latest_output" not in st.session_state:
    st.session_state.latest_output = ""

# Chat input field (bottom aligned)
user_input = st.chat_input("What can I help you with?")

def run_agent(query):
    try:
        response = agent_executor.invoke({"query": query})
        output = response.get("output", "")

        try:
            structured = parser.parse(output)
            pretty = f"""
{structured.message}

Evidence:
- {'\n- '.join(structured.evidence)}

Next Actions:
- {'\n- '.join(structured.next_actions)}

Completed Steps:
- {'\n- '.join(structured.completed_steps)}

Collected Data:
- {chr(10).join([f"{k}: {v}" for k, v in structured.data_collected.items()])}
"""
            final_output = pretty.strip()
        except Exception:
            final_output = output

        # Capture screenshot inside same thread
        screenshot_path = "latest_screenshot.png"
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
        capture_screenshot(screenshot_path)

        return final_output, screenshot_path

    except Exception as e:
        return f"Agent failed: {e}", None

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run agent and screenshot in thread
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_agent, user_input)
        output, screenshot_path = future.result()

    st.session_state.latest_output = output

    # Append assistant message (no direct rendering here)
    st.session_state.messages.append({"role": "assistant", "content": output})

    # Show screenshot if available
    if screenshot_path and os.path.exists(screenshot_path):
        st.image(screenshot_path, caption="Medplum View After Automation", use_container_width=True)
    else:
        st.warning("No screenshot captured or file missing.")

# Show entire chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
