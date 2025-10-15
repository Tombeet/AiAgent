import streamlit as st
import os
from main import agent_executor, parser
from tools import screenshot  # Changed from capture_screenshot

st.set_page_config(page_title="AI Agent Chat", page_icon="🤖")
st.title("🤖 Autonomous AI Agent")

# Sidebar with controls and helpful prompts
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
    
    st.markdown("### 💡 Quick Tips")
    
    with st.expander("📋 Creating a Patient", expanded=False):
        st.markdown("""
        **Provide all information at once:**
        
        ```
        Create patient John Doe
        Born: 1990-03-15
        Gender: Male
        Phone: +65 9123 4567
        Email: john@example.com
        ```
        
        **Required:**
        - Full name
        - Date of birth (YYYY-MM-DD)
        - Gender
        
        **Optional:**
        - Phone, Email
        """)
    
    with st.expander("📅 Booking Appointment", expanded=False):
        st.markdown("""
        **Provide all information at once:**
        
        ```
        Book appointment for Sarah Doe
        Date: 2025-12-29 at 3:30 PM
        Duration: 1 hour
        Reason: Annual checkup
        ```
        
        **Required:**
        - Patient name or ID
        - Date and time
        - Duration or end time
        
        **Optional:**
        - Reason, Doctor name
        """)
    
    with st.expander("🔍 Finding Patients", expanded=False):
        st.markdown("""
        **Provide at least one identifier:**
        
        ```
        Find patient named John Doe
        ```
        or
        ```
        Search for patient ID: abc-123
        ```
        or
        ```
        Find patient with DOB 1990-03-15
        ```
        
        **Need at least one:**
        - Name, Patient ID, DOB, Phone, or Email
        """)
    
    with st.expander("✏️ Updating Info", expanded=False):
        st.markdown("""
        **Provide complete update details:**
        
        ```
        Update phone number for John Doe
        New number: +65 8888 9999
        ```
        
        **Required:**
        - Patient name or ID
        - Field to update
        - New value
        """)
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This is a **fully autonomous agent** that:
    - 🧠 Thinks and adapts
    - 👀 Observes pages before acting
    - 🔄 Handles multi-turn conversations
    - 📸 Captures evidence
    
    **Pro tip:** Provide complete information in your first message to get faster results!
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
user_input = st.chat_input(
    "💬 Try: 'Create patient John Doe, born 1990-03-15, male' or 'Book appointment for Sarah on 2025-12-29 at 3pm'"
)

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