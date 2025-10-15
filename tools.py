# tools.py — Fully Autonomous Web Automation Agent
# Primitive tools only - agent figures out ALL workflows
from dateutil import parser as date_parser
import os, re, asyncio, sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from langchain.tools import tool

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()

BASE_URL = os.getenv("MEDPLUM_BASE_URL", "https://app.medplum.com")
MEDPLUM_USER = os.getenv("MEDPLUM_USER", "")
MEDPLUM_PASS = os.getenv("MEDPLUM_PASS", "")

print("=" * 60)
print("🤖 AUTONOMOUS AGENT - PRIMITIVE TOOLS MODE")
print("=" * 60)
print(f"BASE_URL: {BASE_URL}")
print(f"Credentials: {'✅ Loaded' if MEDPLUM_USER and MEDPLUM_PASS else '❌ Missing'}")
print("=" * 60)

# Global browser state
_pw = _browser = _context = _page = None

def ensure_browser():
    """Initialize browser if not already running"""
    global _pw, _browser, _context, _page
    if _page:
        try:
            # Test if page is still responsive
            _page.url
            return _page
        except Exception as e:
            # Page is dead, force full cleanup
            print(f"⚠️ Browser dead ({type(e).__name__}), creating new one...")
            try:
                cleanup_browser()
            except:
                pass
            # Force reset globals even if cleanup fails
            _pw = _browser = _context = _page = None
    
    # Create fresh browser
    print("🌐 Starting new browser...")
    try:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(headless=False, args=['--start-maximized'])
        _context = _browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        _page = _context.new_page()
        _page.set_default_timeout(30000)
        _page.set_default_navigation_timeout(60000)
        print("✅ Browser ready!")
        return _page
    except Exception as e:
        print(f"❌ Failed to create browser: {e}")
        raise


def cleanup_browser():
    """Clean up browser resources"""
    global _pw, _browser, _context, _page
    try:
        if _page:
            _page.close()
        if _context:
            _context.close()
        if _browser:
            _browser.close()
        if _pw:
            _pw.stop()
    except:
        pass
    finally:
        _pw = _browser = _context = _page = None


# ============================================================================
# PRIMITIVE TOOLS - Building blocks for ANY workflow
# ============================================================================

@tool
def goto_url(url: str) -> str:
    """
    Navigate to any URL. Use this to go to specific pages.
    
    Examples:
        goto_url('https://app.medplum.com/signin')
        goto_url('https://app.medplum.com/Patient')
    """
    try:
        p = ensure_browser()
        print(f"📍 Navigating to: {url}")
        p.goto(url, wait_until='domcontentloaded')
        p.wait_for_timeout(2000)
        p.wait_for_load_state('networkidle', timeout=10000)
        
        final_url = p.url
        print(f"   ✅ Now at: {final_url}")
        return f"success:navigated_to:{final_url}"
    except Exception as e:
        error_msg = f"error:{str(e)}"
        print(f"   ❌ Error: {error_msg}")
        # Force cleanup on critical errors
        if "thread" in str(e).lower() or "closed" in str(e).lower():
            try:
                cleanup_browser()
                global _pw, _browser, _context, _page
                _pw = _browser = _context = _page = None
            except:
                pass
        return error_msg


@tool
def read_page() -> str:
    """
    Observe the current page - see what's available.
    Returns: page title, URL, visible text, buttons, links, and form fields.
    
    ALWAYS call this when:
    - You arrive at a new page
    - After clicking something
    - When unsure what to do next
    - To verify page state
    """
    try:
        p = ensure_browser()
        
        title = p.title()
        url = p.url
        
        # Get main visible content
        main_content = ""
        for selector in ["main", "[role='main']", "body"]:
            try:
                loc = p.locator(selector)
                if loc.count():
                    main_content = loc.first.inner_text(timeout=2000)[:1500]
                    break
            except:
                continue
        
        # Get all buttons
        buttons = []
        for el in p.locator("button, [role='button']").all()[:30]:
            try:
                text = el.inner_text(timeout=100).strip()
                if text and len(text) < 80:
                    buttons.append(text)
            except:
                pass
        
        # Get all links
        links = []
        for el in p.locator("a[href]").all()[:30]:
            try:
                text = el.inner_text(timeout=100).strip()
                href = el.get_attribute("href") or ""
                if text and len(text) < 80:
                    links.append(f"{text} -> {href}")
            except:
                pass
        
        # Get all input fields
        fields = []
        for el in p.locator("input, textarea, select").all()[:30]:
            try:
                name = el.get_attribute("name") or ""
                placeholder = el.get_attribute("placeholder") or ""
                field_type = el.get_attribute("type") or "text"
                field_id = el.get_attribute("id") or ""
                
                # Try to find associated label
                label = ""
                if field_id:
                    label_el = p.locator(f"label[for='{field_id}']")
                    if label_el.count():
                        label = label_el.first.inner_text(timeout=100).strip()
                
                field_info = {
                    "type": field_type,
                    "name": name,
                    "id": field_id,
                    "placeholder": placeholder,
                    "label": label
                }
                fields.append(field_info)
            except:
                pass
        
        return f"""PAGE OBSERVATION:
Title: {title}
URL: {url}

VISIBLE TEXT (first 1500 chars):
{main_content}

BUTTONS ({len(buttons)} found):
{buttons}

LINKS ({len(links)} found):
{links[:10]}

FORM FIELDS ({len(fields)} found):
{fields}
"""
    except Exception as e:
        error_msg = f"error_reading_page:{str(e)}"
        # Force cleanup on thread errors
        if "thread" in str(e).lower() or "closed" in str(e).lower():
            try:
                cleanup_browser()
                global _pw, _browser, _context, _page
                _pw = _browser = _context = _page = None
            except:
                pass
        return error_msg


@tool
def click(target: str) -> str:
    """
    Click any element by visible text or selector.
    
    Args:
        target: What to click - button text, link text, or CSS selector
    
    Examples:
        click('Next')
        click('Sign in')
        click('New...')
        click('Save')
        click('button[type="submit"]')
    """
    p = ensure_browser()
    safe_target = target.replace("\n", " ").strip()
    
    print(f"🖱️ Clicking: {safe_target}")
    
    # Try multiple strategies
    selectors = [
        f"button:has-text('{safe_target}')",
        f"a:has-text('{safe_target}')",
        f"[role='button']:has-text('{safe_target}')",
        f"input[value='{safe_target}']",
        f"[aria-label*='{safe_target}' i]",
        safe_target,  # Direct selector
    ]
    
    for selector in selectors:
        try:
            loc = p.locator(selector)
            if loc.count() > 0:
                loc.first.scroll_into_view_if_needed()
                loc.first.click(timeout=5000)
                p.wait_for_load_state('networkidle', timeout=10000)
                print(f"   ✅ Clicked: {safe_target}")
                return f"success:clicked:{safe_target}"
        except:
            continue
    
    print(f"   ❌ Not found: {safe_target}")
    return f"not_found:{safe_target}"


@tool
def type_in_field(field_identifier: str, value: str) -> str:
    """
    Type text into any input field.
    
    Args:
        field_identifier: Field name, placeholder, label, or id
        value: Text to type
    
    Examples:
        type_in_field('email', 'admin@example.com')
        type_in_field('password', 'secret123')
        type_in_field('given', 'John')
        type_in_field('family', 'Doe')
        type_in_field('birthDate', '1990-01-15')
    """
    p = ensure_browser()
    
    print(f"⌨️ Typing in '{field_identifier}': {value[:20]}...")
    
    # Try multiple strategies to find the field
    selectors = [
        f"input[name='{field_identifier}']",
        f"textarea[name='{field_identifier}']",
        f"select[name='{field_identifier}']",
        f"input[id='{field_identifier}']",
        f"input[placeholder*='{field_identifier}' i]",
        f"textarea[placeholder*='{field_identifier}' i]",
    ]
    
    # Also try finding by label
    label_loc = p.locator(f"label:has-text('{field_identifier}')")
    if label_loc.count():
        for_attr = label_loc.first.get_attribute("for")
        if for_attr:
            selectors.append(f"#{for_attr}")
    
    # Find the field
    field = None
    for selector in selectors:
        try:
            temp = p.locator(selector)
            if temp.count():
                field = temp
                break
        except:
            continue
    
    if not field or not field.count():
        print(f"   ❌ Field not found: {field_identifier}")
        return f"field_not_found:{field_identifier}"
    
    try:
        # Get field info
        tag = field.first.evaluate("e => e.tagName.toLowerCase()")
        field_type = field.first.get_attribute("type") or "text"
        
        # Handle date fields specially
        if field_type == "date":
            try:
                parsed_date = date_parser.parse(value)
                value = parsed_date.strftime("%Y-%m-%d")
            except:
                pass
        
        # Handle select dropdowns
        if tag == "select":
            try:
                field.first.select_option(label=value)
            except:
                field.first.select_option(value=value)
            print(f"   ✅ Selected: {value}")
            return f"success:selected:{field_identifier}={value}"
        
        # Handle regular inputs
        field.first.scroll_into_view_if_needed()
        field.first.click()
        field.first.fill(value)
        
        # Check for autocomplete suggestions
        if tag in ["input", "textarea"]:
            field.first.focus()
            p.wait_for_timeout(1000)
            
            # Look for suggestions dropdown
            suggestion_selectors = [
                f"[role='option']:has-text('{value}')",
                f"li:has-text('{value}')",
                f".dropdown-item:has-text('{value}')",
            ]
            
            for selector in suggestion_selectors:
                try:
                    suggestion = p.locator(selector)
                    if suggestion.count() > 0:
                        suggestion.first.click()
                        p.wait_for_timeout(500)
                        print(f"   ✅ Selected suggestion")
                        return f"success:filled_with_suggestion:{field_identifier}"
                except:
                    continue
        
        print(f"   ✅ Typed: {value}")
        return f"success:typed:{field_identifier}={value}"
        
    except Exception as e:
        return f"error:{str(e)}"


@tool
def wait_for(condition: str, seconds: int = 5) -> str:
    """
    Wait for page to load or element to appear.
    
    Args:
        condition: What to wait for - 'page_load', 'element:selector', or just wait N seconds
        seconds: How many seconds to wait (default 5)
    
    Examples:
        wait_for('page_load')
        wait_for('element:button:has-text("Save")')
        wait_for('network_idle')
    """
    p = ensure_browser()
    
    print(f"⏳ Waiting for: {condition} ({seconds}s)")
    
    try:
        if condition == "page_load" or condition == "network_idle":
            p.wait_for_load_state('networkidle', timeout=seconds * 1000)
            return f"success:page_loaded"
        
        elif condition.startswith("element:"):
            selector = condition.replace("element:", "")
            p.wait_for_selector(selector, timeout=seconds * 1000, state='visible')
            return f"success:element_appeared:{selector}"
        
        else:
            # Just wait N seconds
            p.wait_for_timeout(seconds * 1000)
            return f"success:waited_{seconds}s"
            
    except PlaywrightTimeout:
        return f"timeout:condition_not_met:{condition}"
    except Exception as e:
        return f"error:{str(e)}"


@tool
def get_secret(key: str) -> str:
    """
    Get credentials from environment variables.
    Only returns MEDPLUM_USER and MEDPLUM_PASS.
    
    Use this to get login credentials when needed.
    
    Examples:
        get_secret('MEDPLUM_USER')
        get_secret('MEDPLUM_PASS')
    """
    key = key.strip().upper()
    if key not in {"MEDPLUM_USER", "MEDPLUM_PASS"}:
        return "error:secret_not_allowed"
    
    val = os.getenv(key, "")
    if not val:
        return f"error:{key}_not_set"
    
    return f"success:{key}={val}"


@tool
def screenshot(filename: str = "evidence.png") -> str:
    """
    Capture screenshot of current page as evidence.
    
    Args:
        filename: Name for the screenshot file
    
    Examples:
        screenshot('patient_created.png')
        screenshot('after_login.png')
    """
    p = ensure_browser()
    
    try:
        p.wait_for_load_state('networkidle', timeout=3000)
    except:
        pass
    
    try:
        p.wait_for_timeout(1000)
        p.screenshot(path=filename, timeout=30000)
        
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"📸 Screenshot saved: {filename} ({size} bytes)")
            return f"success:screenshot_saved:{filename}"
        
        return f"error:screenshot_not_created"
        
    except Exception as e:
        return f"error:{str(e)}"


@tool
def get_current_location() -> str:
    """
    Get the current page URL.
    Use this to verify where you are or extract IDs from URLs.
    """
    p = ensure_browser()
    url = p.url
    print(f"📍 Current location: {url}")
    return url


@tool
def validate_claim_advanced(claim: str, context: str = "") -> str:
    """
    Use AI vision to validate claims by analyzing a screenshot.
    Takes a screenshot and checks if the claim is visually verified.
    
    Args:
        claim: What you want to verify (e.g. 'Patient John Doe was created')
        context: Additional context about what you're checking
    
    Example:
        validate_claim_advanced('Patient Jimmy Smith was created successfully')
    """
    from langchain_openai import ChatOpenAI
    import base64
    import time
    
    screenshot_path = f"validation_{int(time.time())}.png"
    screenshot_result = screenshot(screenshot_path)
    
    if "error" in screenshot_result:
        return f"VALIDATION_ERROR: {screenshot_result}"
    
    if not os.path.exists(screenshot_path):
        return f"VALIDATION_ERROR: Screenshot not found"
    
    try:
        with open(screenshot_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"VALIDATION_ERROR: Could not read screenshot: {str(e)}"
    
    try:
        validation_llm = ChatOpenAI(model="gpt-4o", temperature=0)
    except Exception as e:
        return f"VALIDATION_ERROR: Could not init model: {str(e)}"
    
    # Get current URL directly from browser
    try:
        p = ensure_browser()
        current_url = p.url
    except:
        current_url = "unknown"
    
    validation_prompt = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""You are analyzing a screenshot from Medplum EMR system.

CLAIM TO VERIFY: {claim}
CONTEXT: {context}
CURRENT URL: {current_url}

Analyze the screenshot carefully and respond with EXACTLY:

VALIDATED: [Specific visual evidence that confirms the claim]
OR
NOT_VALIDATED: [What's missing or contradicts the claim]

Look for: patient names, resource IDs in URL, success messages, form data, page titles.
Only validate if you have clear visual proof.
"""
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_data}"}
                }
            ]
        }
    ]
    
    try:
        result = validation_llm.invoke(validation_prompt)
        print(f"🔍 Validation complete: {screenshot_path}")
        return result.content
    except Exception as e:
        return f"VALIDATION_ERROR: Vision model failed: {str(e)}"


@tool
def close_browser() -> str:
    """
    Close the browser and clean up resources.
    Use this when finishing a task or when browser has issues.
    """
    cleanup_browser()
    print("🔒 Browser closed")
    return "success:browser_closed"


# Export only primitive tools
TOOLS = [
    goto_url,
    read_page,
    click,
    type_in_field,
    wait_for,
    get_secret,
    screenshot,
    get_current_location,
    validate_claim_advanced,
    close_browser,  # NEW!
]

print(f"\n✅ Loaded {len(TOOLS)} primitive tools")
print("🤖 Agent will figure out ALL workflows autonomously!\n")