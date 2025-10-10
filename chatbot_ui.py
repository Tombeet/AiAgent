import streamlit as st
from main import agent_executor, parser

st.set_page_config(page_title="AI Agent Chat", page_icon="💬")
st.title("AI Agent Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat input field
user_input = st.chat_input("What can I help you with?")

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Agent response block
    with st.chat_message("assistant"):
        response = agent_executor.invoke({"query": user_input})
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
            st.text(pretty.strip())
            st.session_state.messages.append({"role": "assistant", "content": pretty.strip()})
        except Exception:
            st.text(output)
            st.session_state.messages.append({"role": "assistant", "content": output})

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
