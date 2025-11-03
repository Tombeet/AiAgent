import streamlit as st  # Streamlit library for building the web UI
import re  # Regular expressions for parsing output
import os  # OS operations, e.g., checking if screenshot files exist
from api_client import run_agent_via_api  # Function to send user queries to the backend agent

# --- NEW: Get API_BASE_URL for building image URLs ---
API_BASE_URL = "http://localhost:8000"  # MODIFIED
#API_BASE_URL = os.environ["API_BASE_URL"].rstrip("/")

# Function to send a user query to the backend agent and return the response and screenshot path
def run_agent(query):
    """Send query to background service and return response and evidence."""
    try:
        session_id = st.session_state["session_id"]  # Get the current session ID from Streamlit session state
        response = run_agent_via_api(session_id, query)  # Send the query to the backend server via API
        if response.get("status") == "success":  # If the backend responded with success
            output = response.get("output", "")  # Get the output message from the response
            screenshot_path = response.get("screenshot_path")  # Get the screenshot path if provided
            # MODIFIED: If screenshot_path is a relative URL, build the full URL
            if screenshot_path and not screenshot_path.startswith("http"):
                screenshot_path = f"{API_BASE_URL}{screenshot_path}"
            return output, screenshot_path  # Return both output and screenshot path
        else:
            # If the backend returned an error, return an error message
            return f"❌ Agent failed: {response.get('error', 'Unknown error')}", None
    except Exception as e:
        # If an exception occurred, return a detailed error message with traceback
        import traceback
        error_msg = f"❌ Agent failed: {str(e)}\n\n{traceback.format_exc()}"
        return error_msg, None

# Set up the Streamlit web page configuration (title and icon in browser tab)
st.set_page_config(page_title="AI Agent Chat", page_icon="🤖")

# Display the main title at the top of the app
st.title("🤖 Autonomous AI Agent")


# Initialize the chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the chat history (all previous messages)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "screenshot" in msg and msg["screenshot"]:
            st.image(msg["screenshot"], caption="Agent Evidence", use_container_width=True)

# Show a chat input box at the bottom for the user to type a message
user_input = st.chat_input("What can I help you with?")

# Generate or get a unique session_id for the user
if "session_id" not in st.session_state:
    import uuid  # Import uuid only if needed
    st.session_state["session_id"] = str(uuid.uuid4())  # Assign a new UUID as session ID

# If the user submitted a new message
if user_input:
    # Add the user message to the chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)  # Display the user message in a chat bubble
    
    # Prepare to display the assistant's response
    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking..."):
            
            # Send the user input to the backend agent and get the response and screenshot path
            output, screenshot_path = run_agent(user_input)
            
            # MODIFIED: If no screenshot path, try to extract from Markdown and build full URL
            if not screenshot_path:
                m = re.search(r'!\[.*?\]\((.*?)\)', output)
                if m:
                    possible_path = m.group(1)
                    filename = os.path.basename(possible_path)
                    # MODIFIED: Build full URL for image
                    screenshot_path = f"{API_BASE_URL}/api/screenshots/{filename}"

        # Display the agent's response in the assistant chat bubble
        st.markdown(output)
        
        # If a screenshot exists, display it and save the message with screenshot
        if screenshot_path:
            st.image(screenshot_path, caption="Agent Evidence", use_container_width=True)
            st.session_state.messages.append({
                "role": "assistant",
                "content": output,
                "screenshot": screenshot_path
            })
        else:
            # Otherwise, just save the assistant message without screenshot
            st.session_state.messages.append({
                "role": "assistant", 
                "content": output
            })