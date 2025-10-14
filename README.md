# 🤖 FULLY AUTONOMOUS EMR AGENT

## What This Is

A **truly autonomous AI agent** that figures out workflows by itself. No pre-programmed tasks - just primitive tools and intelligence!

---

## 🎯 Philosophy

### Before (Micro-managed):
```python
create_patient()  # Does everything
medplum_login()   # Hard-coded workflow
```
❌ Agent just follows scripts
❌ Can't adapt to changes
❌ Need to code every new task

### Now (Autonomous):
```python
goto_url()        # Go anywhere
read_page()       # Observe
click()           # Act
type_in_field()   # Input
```
✅ Agent thinks and adapts
✅ Handles ANY workflow
✅ Learns from environment

---

## 🛠️ The 9 Primitive Tools

Your agent has only **building blocks** - it figures out how to combine them:

### 1. `goto_url(url)`
Navigate to any page
```python
goto_url('https://app.medplum.com/signin')
goto_url('https://app.medplum.com/Patient')
```

### 2. `read_page()`
**MOST IMPORTANT** - Observe the current page
- See all buttons, links, form fields
- Understand page structure
- Know what actions are available

The agent should call this:
- After navigating
- After clicking
- When unsure what to do
- To verify state

### 3. `click(target)`
Click anything by text or selector
```python
click('Next')
click('Sign in')
click('New...')
click('Save')
```

### 4. `type_in_field(field, value)`
Fill any input field
```python
type_in_field('email', 'user@example.com')
type_in_field('given', 'Jimmy')
type_in_field('family', 'Smith')
type_in_field('birthDate', '1990-01-15')
```

### 5. `wait_for(condition, seconds)`
Wait for page to load or element to appear
```python
wait_for('page_load')
wait_for('network_idle')
wait_for('element:button[type="submit"]')
```

### 6. `get_secret(key)`
Get credentials from environment
```python
get_secret('MEDPLUM_USER')   # Returns email
get_secret('MEDPLUM_PASS')   # Returns password
```

### 7. `screenshot(filename)`
Capture evidence
```python
screenshot('after_login.png')
screenshot('patient_created.png')
```

### 8. `get_current_location()`
Know where you are
```python
get_current_location()  # Returns current URL
```

### 9. `validate_claim_advanced(claim)`
Use AI vision to verify success
```python
validate_claim_advanced('Patient Jimmy Smith was created successfully')
```

---

## 🚀 Installation

```bash
cd /Users/anshul/Documents/GitHub/AiAgent

# Replace files
cp tools_autonomous.py tools.py
cp main_autonomous.py main.py

# Run it
python main.py
```

---

## 💡 What The Agent Can Do

The agent **figures out ANY workflow** by observing and adapting!

### ✅ Patient Management
```
"Create a patient named Jimmy Smith born March 15, 1990"
"Search for patients named John"
"Find patient with ID abc-123"
"Update patient Jimmy Smith's phone number"
"List all patients with diabetes"
```

### ✅ Authentication
```
"Login to Medplum"
"Check if I'm logged in"
"Go to the signin page"
```

### ✅ Resource Navigation
```
"Go to the Practitioner page"
"Navigate to Observations"
"Show me all Appointments"
"Find the Medications resource"
```

### ✅ Data Entry
```
"Create a new practitioner named Dr. Sarah Johnson"
"Add an appointment for tomorrow at 3pm"
"Record a blood pressure observation for patient abc-123"
```

### ✅ Search & Retrieval
```
"Find all patients born in 1990"
"Search for appointments this week"
"Show me patients with last name starting with S"
```

### ✅ Complex Multi-Step Tasks
```
"Create a patient, then schedule them an appointment for tomorrow"
"Find patient John Doe and update his address to 123 Main St"
"Search for Dr. Smith and see all their appointments"
```

### ✅ Data Analysis
```
"How many patients are in the system?"
"List all patients and their birth dates"
"What resources are available in this EMR?"
```

### ✅ Validation & Verification
```
"Verify that patient Jimmy Smith was created"
"Check if the appointment was scheduled successfully"
"Confirm the medication was added"
```

---

## 🧠 How The Agent Thinks

### Example: Creating a Patient

**You ask:** "Create a patient named Jimmy Smith"

**Agent thinks:**
```
1. "I need to create a patient. First, am I logged in?"
   → read_page() to check current state

2. "I'm not logged in. I see a signin page."
   → "I need to login first"
   → goto_url('https://app.medplum.com/signin')
   → read_page() to see login form

3. "I see an email field and a Next button"
   → get_secret('MEDPLUM_USER')
   → type_in_field('email', 'the_email')
   → click('Next')
   → wait_for('page_load')

4. "Now I see a password field"
   → get_secret('MEDPLUM_PASS')
   → type_in_field('password', 'the_password')
   → click('Sign in')
   → wait_for('page_load')

5. "I'm logged in! Now to create the patient."
   → goto_url('https://app.medplum.com/Patient')
   → read_page() to see what's available

6. "I see a 'New...' button"
   → click('New...')
   → wait_for('page_load')
   → read_page() to see the form

7. "I see 'given' and 'family' fields"
   → type_in_field('given', 'Jimmy')
   → type_in_field('family', 'Smith')
   → read_page() to find save button

8. "I see a 'Save' button"
   → click('Save')
   → wait_for('page_load')
   → get_current_location() to check URL changed

9. "URL changed to /Patient/abc-123 - success!"
   → screenshot('patient_created.png')
   → validate_claim_advanced('Patient Jimmy Smith was created')

10. "Validation confirms the patient exists!"
    → Return success message
```

---

## 🎓 Teaching The Agent New Workflows

The agent learns by **example patterns**. You can guide it:

### Natural Language Hints
```
"Login to Medplum, then create a patient named Sarah"
→ Agent figures out: login workflow + patient creation

"Go to Practitioners and click the first one"
→ Agent figures out: navigation + selection

"Search for patients and export the results"
→ Agent figures out: search + data export
```

### It Adapts Automatically
- If button text changes from "New..." to "Create", it adapts
- If fields have different names, it finds them
- If workflows change, it observes and adjusts

---

## 🔧 Advanced Features

### 1. Memory Across Conversations
The agent remembers context within a session:
```
You: "Create a patient named Jimmy"
Agent: [creates patient]

You: "Now schedule him an appointment"
Agent: [knows "him" = Jimmy, finds patient, creates appointment]
```

### 2. Error Recovery
If something fails, the agent:
- Calls `read_page()` to understand why
- Tries alternative approaches
- Resets if stuck (goto_url to start over)

### 3. Multi-Resource Operations
```
"Create a patient, then create a practitioner, then schedule an appointment between them"
```
Agent handles the entire workflow!

### 4. Conditional Logic
```
"If patient John Smith exists, update his phone. Otherwise, create him."
```
Agent observes, decides, acts.

---

## 📊 Comparison: Before vs After

### Task: Create a Patient

**Micro-managed (Before):**
```python
def create_patient(name):
    medplum_login()
    navigate_to_resource('Patient')
    click_text('New...')
    fill_field(f'given={name.split()[0]}')
    fill_field(f'family={name.split()[1]}')
    click_text('Save')
```
- 50+ lines of pre-programmed code
- Breaks if UI changes
- Need new function for each task

**Autonomous (Now):**
```python
# No code needed! Just tell it:
"Create a patient named Jimmy Smith"
```
- Agent figures it out
- Adapts to UI changes
- One system handles all tasks

---

## 🎯 Best Practices

### 1. Be Specific When Needed
```
✅ "Create a patient named Jimmy Smith born March 15, 1990, male"
✅ "Login to Medplum"
✅ "Search for patients with last name Smith"
```

### 2. Let Agent Ask Questions
```
You: "Create a patient"
Agent: "What's the patient's name?"
You: "Jimmy Smith"
Agent: [creates patient]
```

### 3. Give Context for Complex Tasks
```
✅ "I need to onboard a new patient. Create patient Jimmy Smith, 
    add his insurance info, and schedule his first appointment."
    
Agent: [figures out the multi-step workflow]
```

---

## 🚨 Limitations

### What It Can't Do:
- ❌ Execute arbitrary code
- ❌ Access external systems (only Medplum)
- ❌ Modify the agent's own code
- ❌ Remember across different chat sessions (yet)

### What It Struggles With:
- Very complex visual layouts (lots of nested menus)
- Tasks requiring domain knowledge not in the UI
- Workflows with CAPTCHA or 2FA

---

## 🎉 Why This Is Better

### Traditional Approach:
```
IF user says "create patient"
  THEN run create_patient_function()
  
IF user says "search patient"
  THEN run search_patient_function()
  
...need 50+ functions
```

### Autonomous Approach:
```
Agent observes what's on the page
Agent thinks about how to accomplish the goal
Agent acts using primitive tools
Agent adapts if something changes
```

**One intelligent agent vs 50+ hard-coded scripts!** 🚀

---

## 📦 Files

- [tools_autonomous.py](computer:///mnt/user-data/outputs/tools_autonomous.py) - Primitive tools only
- [main_autonomous.py](computer:///mnt/user-data/outputs/main_autonomous.py) - Autonomous reasoning engine

---

## 🎓 Next Steps

1. **Test basic workflows:**
   ```
   python main.py
   > Create a patient named Test User
   ```

2. **Try complex tasks:**
   ```
   > Login, create a patient, and take a screenshot
   ```

3. **Let it surprise you:**
   ```
   > What can you do in this EMR system?
   ```

The agent will **explore and figure it out!** 🤖✨