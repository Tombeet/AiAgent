# tools.py — small, generic web-automation tools (no Medplum-specific paths)

import os, re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from langchain.tools import tool

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

# Multi-step login tool for admin
'''@tool
def admin_login(_: str = "") -> str:
    """Perform admin login: fill email, click Next, fill password, submit."""
    p = ensure_browser()
    import time
    from dotenv import load_dotenv
    load_dotenv()
    email = os.getenv("MEDPLUM_USER", "")
    password = os.getenv("MEDPLUM_PASS", "")
    if not email or not password:
        return "login:error:missing_credentials"
    # Fill email
    email_input = p.locator("input[name='email']")
    if not email_input.count():
        return "login:error:email_field_not_found"
    email_input.first.fill(email)
    # Click Next
    next_btn = p.locator("button:has-text('Next')")
    if not next_btn.count():
        return "login:error:next_button_not_found"
    next_btn.first.click()
    # Wait for password field
    for _ in range(10):
        password_input = p.locator("input[name='password']")
        if password_input.count():
            break
        time.sleep(0.3)
    else:
        return "login:error:password_field_not_found"
    password_input.first.fill(password)
    # Submit
    submit_btn = p.locator("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')")
    if not submit_btn.count():
        return "login:error:submit_button_not_found"
    submit_btn.first.click()
    p.wait_for_load_state("networkidle")
    return "login:ok"
'''
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
    Click a button/link or icon by visible text, aria-label, title, or CSS class (case-insensitive substring).
    """
    p = ensure_browser()
    # Try text, aria-label, and title first
    loc = p.locator(
        f"button:has-text('{text}'), a:has-text('{text}'), [role='button']:has-text('{text}'), "
        f"[aria-label*='{text}'], [title*='{text}']"
    )
    if loc.count():
        loc.first.click()
        p.wait_for_load_state('networkidle')
        return "click:ok"
    # Try by CSS class if text/label/title not found
    icon_loc = p.locator(f".{text}")
    if icon_loc.count():
        icon_loc.first.click()
        p.wait_for_load_state('networkidle')
        return "click:ok"
    return "click:not_found"

@tool
def fill_name(kv: str) -> str:
    """Fill by input name. Format: name=value (e.g., email=alice@example.com)."""
    p = ensure_browser()
    m = re.match(r"\s*(.+?)\s*=\s*(.*)\s*", kv)
    if not m:
        return "fill:bad_format"
    name, value = m.group(1), m.group(2)
    loc = p.locator(f"input[name='{name}'], textarea[name='{name}'], select[name='{name}']")
    if not loc.count():
        return "fill:not_found"
    # Check if the field is disabled
    if loc.first.get_attribute("disabled") is not None:
        return "fill:field_disabled"
    tag = loc.first.evaluate("e => e.tagName.toLowerCase()")
    if tag == "select":
        try:
            loc.first.select_option(label=value)
        except Exception:
            loc.first.select_option(value)
    else:
        loc.first.fill(value)
    return "fill:ok"

'''@tool
def submit(_: str = "") -> str:
    """Click submit or common primary action button."""
    p = ensure_browser()
    loc = p.locator("button[type='submit']")
    if not loc.count():
        loc = p.locator(
            "button:has-text('Create'), button:has-text('Save'), "
            "button:has-text('Submit'), button:has-text('Next'), button:has-text('Continue')"
        )
    if not loc.count():
        return "submit:not_found"
    loc.first.click()
    p.wait_for_load_state("networkidle")
    return "submit:ok"
'''
@tool
def get_secret(key: str) -> str:
    """Return env secrets for MEDPLUM_USER or MEDPLUM_PASS. Format 'KEY=value' or 'KEY=' if missing."""
    key = key.strip().upper()
    if key not in {"MEDPLUM_USER", "MEDPLUM_PASS"}:
        return "secret:not_allowed"
    val = os.getenv(key, "")
    return f"{key}={val}"

'''@tool
def close(_: str = "") -> str:
    """Close the browser."""
    close_browser()
    return "closed"
'''
# export list for main
#TOOLS = [nav, read_texts, click_text, fill_name, submit, get_secret, close, admin_login]
TOOLS = [nav, read_texts, click_text, fill_name,get_secret]