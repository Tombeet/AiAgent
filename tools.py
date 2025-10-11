# tools.py — small, generic web-automation tools (no Medplum-specific paths)
from dateutil import parser as date_parser  # pip install python-dateutil
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
def nav(_: str = "") -> str:
    """Navigate to the EMR system base URL only. Ignores any path argument."""
    p = ensure_browser()
    url = BASE_URL
    p.goto(url)
    p.wait_for_load_state("domcontentloaded")
    return f"navigated:{p.url}"

@tool
def read_texts(_: str = "") -> str:
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
    # Try by CSS class if text/label/title not found
    icon_loc = p.locator(f".{safe_text}")
    if icon_loc.count():
        icon_loc.first.click()
        p.wait_for_load_state('networkidle')
        return "click:ok"
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
    
    tag = loc.first.evaluate("e => e.tagName.toLowerCase()")
    input_type = loc.first.get_attribute("type") or ""

    # Auto-convert human-readable dates for date inputs
    if input_type == "date":
        try:
            parsed_date = date_parser.parse(value)
            value = parsed_date.strftime("%Y-%m-%d")
        except Exception:
            return "fill:invalid_date_format"

        
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
        p.wait_for_timeout(500)  # Wait for any dropdown options to appear

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
def click_dropdown_after_fill(kv: str, option_text: str) -> str:
    """
    Fill an input or textarea by name or placeholder, then click the dropdown to show options and select an option.
    Format: key=value (e.g., Search=your search query).
    """
    p = ensure_browser()
    m = re.match(r"\s*(.+?)\s*=\s*(.*)\s*", kv)
    if not m:
        return "fill:bad_format"
    key, value = m.group(1), m.group(2)
    
    # Try by name
    loc = p.locator(f"input[name='{key}'], textarea[name='{key}']")
    if not loc.count():
        # Try by placeholder
        loc = p.locator(f"input[placeholder='{key}'], textarea[placeholder='{key}']")
    if not loc.count():
        return "click_dropdown:not_found"
    
    # Fill the input field
    loc.first.fill(value)
    loc.first.focus()
    
    # Click the dropdown to show options
    loc.first.click()
    
    # Wait for the dropdown options to be visible
    option_locator = p.locator(f"div[role='option']:has-text('{option_text}')")  # Adjust this selector based on your dropdown structure
    option_locator.wait_for(state='visible', timeout=5000)  # Adjust timeout as needed
    
    # Click the desired option in the dropdown
    if option_locator.count():
        option_locator.first.click()
        return "option_selected:ok"
    
    return "option_selected:not_found"

def capture_screenshot(path: str = "latest_screenshot.png") -> str:
    p = ensure_browser()
    p.screenshot(path=path)
    return path


# export list for main
#TOOLS = [nav, read_texts, click_text, fill_name, submit, get_secret, close, admin_login]
TOOLS = [nav, read_texts, click_text, fill_field,get_secret, click_dropdown_after_fill]