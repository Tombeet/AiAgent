# tools.py — small, generic web-automation tools (no Medplum-specific paths)

import os, re, asyncio, sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from langchain.tools import tool

# Fix for Windows: required to allow Playwright subprocesses
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()

BASE_URL = "http://localhost:3000"  # Add this near the top with other configurations

# ---- shared browser session ----
_pw = _browser = _page = None

def ensure_browser():
    global _pw, _browser, _page
    if _page:
        return _page
    _pw = sync_playwright().start()
    _browser = _pw.chromium.launch(headless=False)
    _page = _browser.new_page()
    return _page

def close_browser():
    global _pw, _browser, _page
    try:
        if _browser:
            _browser.close()
    finally:
        _pw = _browser = _page = None


@tool
def read_texts() -> str:
    """Return page title/url, sample of visible button/link texts, and input name/placeholders."""
    p = ensure_browser()
    btns = []
    for el in p.locator("button, a, [role='button']").all()[:100]:
        try:
            t = (el.inner_text(timeout=150) or "").strip()
            if t:
                btns.append(t)
        except Exception:
            pass
    inputs = []
    for el in p.locator("input, textarea, select").all()[:100]:
        try:
            name = el.get_attribute("name") or ""
            ph = el.get_attribute("placeholder") or ""
            if name or ph:
                inputs.append({"name": name, "placeholder": ph})
        except Exception:
            pass
    return (
        f"TITLE: {p.title()}\nURL: {p.url}\n"
        f"BUTTONS/LINKS: {btns}\n"
        f"INPUTS(name/placeholder): {inputs}"
    )

@tool
def click_text(text: str) -> str:
    """
    Click a button/link/icon/input by visible text, aria-label, title, placeholder, alt, or CSS class (case-insensitive substring).
    """
    p = ensure_browser()
    # Sanitize text for selector
    safe_text = text.replace("\n", " ").replace("\r", " ").strip()
    # Try text, aria-label, title, placeholder, alt
    loc = p.locator(
        f"button:has-text('{safe_text}'), a:has-text('{safe_text}'), [role='button']:has-text('{safe_text}'), "
        f"[aria-label*='{safe_text}'], [title*='{safe_text}'], input[placeholder*='{safe_text}'], input[aria-label*='{safe_text}'], img[alt*='{safe_text}']"
    )
    if loc.count():
        loc.first.click()
        p.wait_for_load_state('networkidle')
        return "click:ok"
    
    # Only try CSS class if text looks like a valid CSS class (no numbers at start, no hyphens at start)
    if safe_text and not safe_text[0].isdigit() and not safe_text.startswith('-'):
        try:
            icon_loc = p.locator(f".{safe_text}")
            if icon_loc.count():
                icon_loc.first.click()
                p.wait_for_load_state('networkidle')
                return "click:ok"
        except Exception:
            pass  # Invalid CSS selector, skip
    
    return "click:not_found"

@tool
def fill_field(kv: str) -> str:
    """
    Fill an input/textarea/select by name or placeholder. If not found, and only one select is visible, tries that.
    Format: key=value (e.g., email=alice@example.com or placeholder=Search=John).
    """
    p = ensure_browser()
    m = re.match(r"\s*(.+?)\s*=\s*(.*)\s*", kv)
    if not m:
        return "fill:bad_format"
    key, value = m.group(1), m.group(2)
    
    # Try by name
    loc = p.locator(f"input[name='{key}'], textarea[name='{key}'], select[name='{key}']")
    if not loc.count():
        # Try by placeholder
        loc = p.locator(f"input[placeholder='{key}'], textarea[placeholder='{key}']")
    if not loc.count():
        return "fill:not_found"
    
    # Check if the found element is a dropdown
    if loc.first.evaluate("e => e.tagName.toLowerCase()") == "select":
        try:
            loc.first.select_option(label=value)  # Try to select by label
        except Exception:
            loc.first.select_option(value)  # Fallback to select by value
    else:
        # Fill the input field
        loc.first.fill(value)
    
    # Additional handling for dropdowns that are not standard selects
    if loc.first.evaluate("e => e.tagName.toLowerCase()") in ["input", "textarea"]:
        loc.first.focus()  # Focus to trigger any dropdowns
        p.wait_for_timeout(1500)  # Increased wait time for dropdown options to appear
        
        # Try to find and click dropdown suggestions containing the search term
        suggestion_selectors = [
            f"div:has-text('{value}')",  # Generic div containing the text
            f"[role='option']:has-text('{value}')",  # ARIA option role
            f".suggestion:has-text('{value}')",  # Common CSS class
            f".dropdown-item:has-text('{value}')",  # Bootstrap-style
            f"li:has-text('{value}')",  # List item
            f".autocomplete-suggestion:has-text('{value}')",  # Autocomplete style
        ]
        
        for selector in suggestion_selectors:
            suggestion_loc = p.locator(selector)
            if suggestion_loc.count() > 0:
                try:
                    # Get the suggestion text before clicking
                    suggestion_text = suggestion_loc.first.inner_text()
                    suggestion_loc.first.click()
                    p.wait_for_timeout(500)  # Wait for navigation/update
                    return f"fill:ok_suggestion_selected:{suggestion_text}"
                except Exception as e:
                    continue  # Try next selector
        
        # If no suggestions found, return that field was filled but no suggestions
        return "fill:ok_but_no_suggestions"

    return "fill:ok"

@tool
def get_secret(key: str) -> str:
    """Return env secrets for MEDPLUM_USER or MEDPLUM_PASS. Format 'KEY=value' or 'KEY=' if missing."""
    key = key.strip().upper()
    if key not in {"MEDPLUM_USER", "MEDPLUM_PASS"}:
        return "secret:not_allowed"
    val = os.getenv(key, "")
    return f"{key}={val}"


@tool
def smart_search(search_term: str) -> str:
    """Intelligently search using any available search mechanism on the current page."""
    p = ensure_browser()
    
    # Find search inputs by attributes (more reliable than text-based clicking)
    search_selectors = [
        "input[placeholder*='Search']",  # Your EMR case
        "input[placeholder*='search' i]",
        "input[type='search']",
        "input[name*='search' i]"
    ]
    
    for selector in search_selectors:
        try:
            search_field = p.locator(selector)
            if search_field.count() > 0:
                search_field.first.click()
                search_field.first.fill(search_term)
                search_field.first.press("Enter")
                p.wait_for_timeout(2000)
                return f"search_success:{search_term}"
        except Exception:
            continue
    
    # Fallback to existing method
    try:
        result = fill_field(f"Search={search_term}")
        if "ok" in result:
            return f"search_fallback_success:{search_term}"
    except Exception:
        pass
    
    return "search_failed"


@tool
def navigate_to_main_page() -> str:
    """navigate to main page or reset location to main/landing page before starting a new task."""
    p = ensure_browser()
    
    # Try to find common home navigation elements
    home_selectors = [
        "a[href='/'], a[href='#/']",  # Home links
        ".logo, .brand, .navbar-brand",  # Logo elements  
        "[aria-label*='home' i], [title*='home' i]",  # Home buttons
        ".navbar-brand, .logo",  # Brand/logo in navbar
    ]
    
    for selector in home_selectors:
        try:
            loc = p.locator(selector)
            if loc.count() > 0:
                loc.first.click()
                p.wait_for_load_state('networkidle')
                return f"reset_via_click:{p.url}"
        except Exception:
            continue
    
    # Fallback: navigate to base URL if no home elements found
    try:
        p.goto(BASE_URL)
        p.wait_for_load_state('networkidle')
        p.wait_for_timeout(2000)
        return f"reset_via_base_url:{p.url}"
    except Exception as e:
        return f"reset_failed:{str(e)}"

@tool
def capture_screenshot(path: str) -> str:
    """Capture a screenshot of the outcome of the request as evidence."""
    p = ensure_browser()
    try:
        # Add timeout and error handling
        p.screenshot(path=path, timeout=30000)  # Increased from 10s to 30s
        return path
    except Exception as e:
        if "timeout" in str(e).lower():
            return f"screenshot_timeout_skipped: {path}"
        else:
            return f"screenshot_failed: {str(e)}"

@tool 
def validate_claim_advanced(claim: str, context: str = "") -> str:
    """
    Advanced validation using vision model to analyze claims against current page state.
    Uses the capture_screenshot tool to get current browser state for validation.
    
    Args:
        claim: The specific claim to validate
        context: Additional context about what task is being performed
    
    Returns:
        Detailed validation result with visual evidence analysis
    """
    from langchain_openai import ChatOpenAI
    import base64
    
    # Use the existing capture_screenshot tool
    screenshot_path = f"validation_{hash(claim) % 10000}.png"
    screenshot_result = capture_screenshot(screenshot_path)
    
    # Check if screenshot was successful
    if "failed" in screenshot_result or "timeout" in screenshot_result:
        return f"VALIDATION_ERROR: {screenshot_result}"
    
    try:
        # Read and encode the screenshot
        with open(screenshot_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode()
            
    except Exception as e:
        return f"VALIDATION_ERROR: Could not read screenshot: {str(e)}"
    
    # Use vision-capable model for validation
    validation_llm = ChatOpenAI(
        model="gpt-4o",  # Vision-capable model
        temperature=0
    )
    
    validation_prompt = [
        {
            "role": "user", 
            "content": [
                {
                    "type": "text",
                    "text": f"""
You are a strict fact-checker analyzing a screenshot of an EMR system. Validate this claim against what you can actually see in the image.

CLAIM: {claim}
CONTEXT: {context}

Look carefully at the screenshot and respond with EXACTLY one of these formats:

VALIDATED: [Describe specific visual elements that prove the claim - e.g., "Patient name 'John Doe' visible in header", "URL shows /Patient/12345", "Success message displayed"]

NOT_VALIDATED: [Explain what visual evidence is missing or contradicts the claim]

Be extremely precise. Only validate if you can see clear visual evidence that supports the claim.
Focus on:
- Patient names in headers/titles/forms
- URLs showing patient IDs in address bar
- Success/error messages on the page
- Form completion states
- Page titles and navigation breadcrumbs
- Any confirmation dialogs or notifications

Current page URL: {ensure_browser().url}
"""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}"
                    }
                }
            ]
        }
    ]
    
    try:
        result = validation_llm.invoke(validation_prompt)
        
        # Keep screenshot for debugging (comment out the deletion)
        # try:
        #     os.remove(screenshot_path)
        # except:
        #     pass
        
        print(f"DEBUG: Screenshot saved as: {screenshot_path}")  # Add this line
        return result.content
        
    except Exception as e:
        return f"VALIDATION_ERROR: LLM validation failed: {str(e)}"

# export list for main
#TOOLS = [nav, read_texts, click_text, fill_name, submit, get_secret, close, admin_login]
TOOLS = [read_texts, click_text, fill_field, get_secret, smart_search, navigate_to_main_page,capture_screenshot, validate_claim_advanced]