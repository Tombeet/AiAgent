# tools.py — Enhanced web-automation tools for Medplum EMR
from dateutil import parser as date_parser
import os, re, asyncio, sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from langchain.tools import tool

# Fix for Windows: required to allow Playwright subprocesses
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()

BASE_URL = os.getenv("MEDPLUM_BASE_URL", "https://app.medplum.com")
MEDPLUM_USER = os.getenv("MEDPLUM_USER", "")
MEDPLUM_PASS = os.getenv("MEDPLUM_PASS", "")

# Debug output
print("=" * 60)
print("🔧 MEDPLUM CONFIGURATION")
print("=" * 60)
print(f"BASE_URL: {BASE_URL}")
print(f"USER: {MEDPLUM_USER}")
print(f"PASS: {'*' * len(MEDPLUM_PASS) if MEDPLUM_PASS else '❌ NOT SET!'}")
print("=" * 60)

# ---- shared browser session ----
_pw = _browser = _context = _page = None
_is_authenticated = False

def ensure_browser():
    """Initialize browser with better configuration"""
    global _pw, _browser, _context, _page
    if _page:
        return _page
    
    _pw = sync_playwright().start()
    _browser = _pw.chromium.launch(
        headless=False,
        args=['--start-maximized']
    )
    
    _context = _browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    _page = _context.new_page()
    _page.set_default_timeout(30000)
    _page.set_default_navigation_timeout(60000)
    
    return _page

def close_browser_internal():
    """Internal function to close browser - NOT a tool"""
    global _pw, _browser, _context, _page, _is_authenticated
    try:
        if _page:
            _page.close()
        if _context:
            _context.close()
        if _browser:
            _browser.close()
        if _pw:
            _pw.stop()
    finally:
        _pw = _browser = _context = _page = None
        _is_authenticated = False


@tool
def medplum_login() -> str:
    """
    Authenticate to Medplum using credentials from .env file.
    Medplum uses TWO-STEP login: email then password.
    """
    global _is_authenticated
    p = ensure_browser()
    
    if _is_authenticated:
        return "login:already_authenticated"
    
    if not MEDPLUM_USER or not MEDPLUM_PASS:
        return "login:missing_credentials"
    
    try:
        print("\n🔐 Starting Medplum login (two-step)...")
        
        # Navigate to login
        p.goto(f"{BASE_URL}/signin", wait_until='domcontentloaded')
        p.wait_for_timeout(3000)
        
        current_url = p.url
        print(f"   📍 URL: {current_url}")
        
        # Check if already logged in
        if "/signin" not in current_url.lower():
            _is_authenticated = True
            print("   ✅ Already logged in!")
            return f"login:already_logged_in:{current_url}"
        
        # STEP 1: Enter email and click Next
        print("   📧 STEP 1: Entering email...")
        
        email_field = p.locator("input[name='email'], input[type='email']")
        if email_field.count() == 0:
            p.screenshot(path="login_no_email.png")
            return "login:email_field_not_found"
        
        email_field.first.click()
        email_field.first.fill(MEDPLUM_USER)
        print(f"      Email: {MEDPLUM_USER}")
        p.wait_for_timeout(500)
        
        # Click Next
        print("   🖱️ Clicking Next...")
        next_button = p.locator("button:has-text('Next'), button[type='submit']")
        if next_button.count() == 0:
            return "login:next_button_not_found"
        
        next_button.first.click()
        p.wait_for_timeout(3000)
        
        # STEP 2: Enter password and click Sign in
        print("   🔑 STEP 2: Entering password...")
        
        # Wait for password field
        try:
            p.wait_for_selector("input[type='password']", timeout=10000, state='visible')
        except:
            error = p.locator("[role='alert'], .error")
            if error.count() > 0:
                try:
                    error_text = error.first.inner_text(timeout=1000)
                    print(f"   ❌ Error: {error_text}")
                    return f"login:email_error:{error_text}"
                except:
                    pass
            p.screenshot(path="login_no_password.png")
            return "login:password_field_not_found"
        
        password_field = p.locator("input[type='password']")
        if password_field.count() == 0:
            return "login:password_field_missing"
        
        password_field.first.click()
        password_field.first.fill(MEDPLUM_PASS)
        print(f"      Password: {'*' * len(MEDPLUM_PASS)}")
        p.wait_for_timeout(500)
        
        # Click Sign in
        print("   🖱️ Clicking Sign in...")
        sign_in = p.locator("button:has-text('Sign in'), button:has-text('Sign In'), button[type='submit']")
        if sign_in.count() == 0:
            return "login:signin_button_not_found"
        
        sign_in.first.click()
        
        # Wait for login to complete
        print("   ⏳ Waiting for login...")
        try:
            p.wait_for_url(lambda url: "/signin" not in url.lower(), timeout=15000)
            p.wait_for_load_state('networkidle', timeout=5000)
            
            _is_authenticated = True
            final_url = p.url
            print(f"   ✅ Login successful!")
            print(f"   📍 Now at: {final_url}")
            return f"login:success:{final_url}"
            
        except:
            error = p.locator("[role='alert'], .error")
            if error.count() > 0:
                try:
                    error_text = error.first.inner_text(timeout=1000)
                    print(f"   ❌ Error: {error_text}")
                    return f"login:failed:{error_text}"
                except:
                    pass
            
            if "/signin" in p.url.lower():
                print("   ❌ Still on signin - wrong credentials")
                p.screenshot(path="login_failed.png")
                return "login:failed_wrong_credentials"
            
            return "login:timeout"
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        p.screenshot(path="login_exception.png")
        return f"login:error:{str(e)}"


@tool
def navigate_to_resource(resource_type: str, resource_id: str = "") -> str:
    """
    Navigate directly to a Medplum resource page.
    Examples: navigate_to_resource('Patient') or navigate_to_resource('Patient', 'abc-123')
    """
    p = ensure_browser()
    
    # Auto-login if needed
    if not _is_authenticated:
        result = medplum_login()
        if "success" not in result and "already" not in result:
            return f"nav:login_failed:{result}"
    
    try:
        url = f"{BASE_URL}/{resource_type}"
        if resource_id:
            url += f"/{resource_id}"
        
        p.goto(url, wait_until='domcontentloaded')
        p.wait_for_timeout(2000)
        p.wait_for_load_state('networkidle', timeout=10000)
        
        return f"nav:success:{p.url}"
    except Exception as e:
        return f"nav:error:{str(e)}"


@tool
def read_texts() -> str:
    """
    Return page title, URL, main content, buttons, and form fields.
    Use this to understand what's currently on the page.
    """
    p = ensure_browser()
    
    try:
        title = p.title()
        url = p.url
        
        # Get main content
        main_content = ""
        for selector in ["main", "[role='main']", ".content", "#content"]:
            try:
                loc = p.locator(selector)
                if loc.count():
                    main_content = loc.first.inner_text(timeout=2000)[:2000]
                    break
            except:
                continue
        
        if not main_content:
            main_content = p.locator("body").inner_text()[:2000]
        
        # Get buttons/links
        btns = []
        for el in p.locator("button, a, [role='button']").all()[:50]:
            try:
                text = el.inner_text(timeout=150).strip()
                if text and len(text) < 100:
                    btns.append(text)
            except:
                pass
        
        # Get form fields
        inputs = []
        for el in p.locator("input, textarea, select").all()[:50]:
            try:
                name = el.get_attribute("name") or ""
                placeholder = el.get_attribute("placeholder") or ""
                field_type = el.get_attribute("type") or "text"
                
                # Try to find label
                label = ""
                field_id = el.get_attribute("id")
                if field_id:
                    label_el = p.locator(f"label[for='{field_id}']")
                    if label_el.count():
                        label = label_el.first.inner_text(timeout=100).strip()
                
                inputs.append({
                    "type": field_type,
                    "name": name,
                    "placeholder": placeholder,
                    "label": label
                })
            except:
                pass
        
        # Extract resource info from URL
        resource_match = re.search(r'/([A-Z][a-zA-Z]+)/([a-f0-9-]+)', url)
        resource_info = ""
        if resource_match:
            resource_info = f"\nRESOURCE: {resource_match.group(1)}/{resource_match.group(2)}"
        
        return f"""TITLE: {title}
URL: {url}{resource_info}

MAIN_CONTENT:
{main_content}

BUTTONS/LINKS: {btns}

FORM_FIELDS: {inputs}
"""
    except Exception as e:
        return f"read_error:{str(e)}"


@tool
def click_text(text: str) -> str:
    """
    Click element by visible text, aria-label, title, or placeholder.
    Example: click_text('Save') or click_text('New Patient')
    """
    p = ensure_browser()
    safe_text = text.replace("\n", " ").replace("\r", " ").strip()
    
    # Multiple selector strategies
    selectors = [
        f"button:has-text('{safe_text}')",
        f"a:has-text('{safe_text}')",
        f"[role='button']:has-text('{safe_text}')",
        f"[aria-label*='{safe_text}' i]",
        f"[title*='{safe_text}' i]",
        f"input[placeholder*='{safe_text}' i]",
        f"img[alt*='{safe_text}' i]",
    ]
    
    for selector in selectors:
        try:
            loc = p.locator(selector)
            if loc.count() > 0:
                loc.first.scroll_into_view_if_needed()
                loc.first.click(timeout=5000)
                p.wait_for_load_state('networkidle', timeout=10000)
                return f"click:success:{safe_text}"
        except:
            continue
    
    # Try CSS class as fallback
    if safe_text and safe_text[0].isalpha() and not ' ' in safe_text:
        try:
            loc = p.locator(f".{safe_text}")
            if loc.count():
                loc.first.click()
                p.wait_for_load_state('networkidle')
                return f"click:success_class:{safe_text}"
        except:
            pass
    
    return f"click:not_found:{safe_text}"


@tool
def fill_field(kv: str) -> str:
    """
    Fill input/textarea/select by name, placeholder, or label.
    Format: key=value
    Example: fill_field('given name=John') or fill_field('birthDate=1990-01-15')
    """
    p = ensure_browser()
    
    m = re.match(r"\s*(.+?)\s*=\s*(.*)\s*", kv)
    if not m:
        return "fill:bad_format"
    
    key, value = m.group(1), m.group(2)
    
    # Try multiple selectors
    selectors = [
        f"input[name='{key}']",
        f"textarea[name='{key}']",
        f"select[name='{key}']",
        f"input[placeholder*='{key}' i]",
        f"textarea[placeholder*='{key}' i]",
    ]
    
    # Try finding by label
    label_loc = p.locator(f"label:has-text('{key}')")
    if label_loc.count():
        for_attr = label_loc.first.get_attribute("for")
        if for_attr:
            selectors.append(f"#{for_attr}")
    
    loc = None
    for selector in selectors:
        try:
            temp = p.locator(selector)
            if temp.count():
                loc = temp
                break
        except:
            continue
    
    if not loc or not loc.count():
        return f"fill:not_found:{key}"
    
    try:
        tag = loc.first.evaluate("e => e.tagName.toLowerCase()")
        input_type = loc.first.get_attribute("type") or "text"
        
        # Handle date inputs
        if input_type == "date":
            try:
                parsed_date = date_parser.parse(value)
                value = parsed_date.strftime("%Y-%m-%d")
            except:
                return f"fill:invalid_date:{value}"
        
        # Handle select dropdowns
        if tag == "select":
            try:
                loc.first.select_option(label=value)
            except:
                loc.first.select_option(value=value)
            return f"fill:success:{key}={value}"
        
        # Handle regular inputs
        loc.first.scroll_into_view_if_needed()
        loc.first.click()
        loc.first.fill(value)
        
        # Handle autocomplete dropdowns
        if tag in ["input", "textarea"]:
            loc.first.focus()
            p.wait_for_timeout(1500)
            
            # Try finding suggestions
            suggestion_selectors = [
                f"[role='option']:has-text('{value}')",
                f"div:has-text('{value}')",
                f".suggestion:has-text('{value}')",
                f".dropdown-item:has-text('{value}')",
                f"li:has-text('{value}')",
            ]
            
            for selector in suggestion_selectors:
                try:
                    suggestion = p.locator(selector)
                    if suggestion.count() > 0:
                        suggestion_text = suggestion.first.inner_text()
                        suggestion.first.click()
                        p.wait_for_timeout(500)
                        return f"fill:ok_suggestion:{suggestion_text}"
                except:
                    continue
            
            return "fill:ok_no_suggestions"
        
        return f"fill:success:{key}={value}"
        
    except Exception as e:
        return f"fill:error:{str(e)}"


@tool
def get_secret(key: str) -> str:
    """Return env secrets for MEDPLUM_USER or MEDPLUM_PASS."""
    key = key.strip().upper()
    if key not in {"MEDPLUM_USER", "MEDPLUM_PASS"}:
        return "secret:not_allowed"
    val = os.getenv(key, "")
    return f"{key}={val}"


@tool
def smart_search(search_term: str) -> str:
    """
    Search using any available search mechanism on the page.
    Example: smart_search('John Smith')
    """
    p = ensure_browser()
    
    search_selectors = [
        "input[placeholder*='Search' i]",
        "input[type='search']",
        "input[name*='search' i]",
        "input[aria-label*='search' i]",
        "[role='searchbox']",
    ]
    
    for selector in search_selectors:
        try:
            field = p.locator(selector)
            if field.count() > 0:
                field.first.scroll_into_view_if_needed()
                field.first.click()
                field.first.fill(search_term)
                field.first.press("Enter")
                p.wait_for_timeout(2000)
                p.wait_for_load_state('networkidle', timeout=10000)
                return f"search:success:{search_term}"
        except:
            continue
    
    # Fallback
    try:
        result = fill_field(f"Search={search_term}")
        if "ok" in result or "success" in result:
            return f"search:fallback_success:{search_term}"
    except:
        pass
    
    return f"search:failed:{search_term}"


@tool
def navigate_to_main_page() -> str:
    """Navigate to Medplum home/dashboard page."""
    p = ensure_browser()
    
    # Auto-login if needed
    if not _is_authenticated:
        result = medplum_login()
        if "success" not in result and "already" not in result:
            return f"nav_home:login_failed:{result}"
    
    try:
        # Try clicking home
        home_selectors = [
            "a[href='/']",
            ".logo",
            ".navbar-brand",
            "[aria-label*='home' i]",
        ]
        
        for selector in home_selectors:
            try:
                loc = p.locator(selector)
                if loc.count():
                    loc.first.click()
                    p.wait_for_load_state('networkidle')
                    return f"nav_home:success:{p.url}"
            except:
                continue
        
        # Fallback to direct navigation
        p.goto(BASE_URL, wait_until='domcontentloaded')
        p.wait_for_timeout(2000)
        return f"nav_home:success_url:{p.url}"
        
    except Exception as e:
        return f"nav_home:error:{str(e)}"


@tool
def capture_screenshot(path: str = "latest_screenshot.png") -> str:
    """
    Capture screenshot of the current page as evidence.
    Example: capture_screenshot('patient_created.png')
    """
    p = ensure_browser()
    
    try:
        # Wait for page to settle
        try:
            p.wait_for_load_state('networkidle', timeout=5000)
        except:
            pass
        
        p.wait_for_timeout(1000)
        
        # Take screenshot
        p.screenshot(path=path, timeout=30000)
        
        if os.path.exists(path):
            size = os.path.getsize(path)
            return f"screenshot:success:{path}:{size}bytes"
        return f"screenshot:failed:file_not_created"
        
    except PlaywrightTimeout:
        return f"screenshot:timeout:{path}"
    except Exception as e:
        return f"screenshot:error:{str(e)}"


@tool
def get_current_url() -> str:
    """Get current page URL - useful for extracting resource IDs."""
    p = ensure_browser()
    return p.url


@tool
def wait_for_element(selector: str, timeout_ms: int = 10000) -> str:
    """
    Wait for element to appear - useful for dynamic content.
    Example: wait_for_element('button:has-text("Save")')
    """
    p = ensure_browser()
    try:
        p.wait_for_selector(selector, timeout=timeout_ms, state='visible')
        return f"wait:success:{selector}"
    except PlaywrightTimeout:
        return f"wait:timeout:{selector}"
    except Exception as e:
        return f"wait:error:{str(e)}"


@tool 
def validate_claim_advanced(claim: str, context: str = "") -> str:
    """
    Validate claims using vision model to analyze screenshots.
    Example: validate_claim_advanced('Patient John Doe was created successfully')
    """
    from langchain_openai import ChatOpenAI
    import base64
    import time
    
    screenshot_path = f"validation_{int(time.time())}.png"
    screenshot_result = capture_screenshot(screenshot_path)
    
    if "failed" in screenshot_result or "timeout" in screenshot_result:
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
    
    current_url = get_current_url()
    
    validation_prompt = [
        {
            "role": "user", 
            "content": [
                {
                    "type": "text",
                    "text": f"""You are a strict fact-checker analyzing a Medplum EMR screenshot.

CLAIM: {claim}
CONTEXT: {context}
CURRENT URL: {current_url}

Respond with EXACTLY:

VALIDATED: [Specific visual evidence]
OR
NOT_VALIDATED: [What's missing]

Look for: patient names, resource IDs in URL, success messages, form states, page titles.
Only validate with clear visual proof.
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
        print(f"🔍 Validation screenshot: {screenshot_path}")
        return result.content
    except Exception as e:
        return f"VALIDATION_ERROR: Vision model failed: {str(e)}"


# Export tools
TOOLS = [
    medplum_login,
    navigate_to_resource,
    read_texts,
    click_text,
    fill_field,
    get_secret,
    smart_search,
    navigate_to_main_page,
    capture_screenshot,
    get_current_url,
    wait_for_element,
    validate_claim_advanced,
]