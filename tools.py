# tools.py — small, generic web-automation tools (no Medplum-specific paths)

import os, re, asyncio, sys
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from langchain.tools import tool

# Fix for Windows: required to allow Playwright subprocesses
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()

BASE_URL = "https://app.medplum.com/"

# ---- shared browser session (async-safe singletons) ----
_pw = _browser = _page = None
_browser_lock = asyncio.Lock()


async def ensure_browser():
    """Ensure a single shared Playwright/browser/page is available (async-safe)."""
    global _pw, _browser, _page
    async with _browser_lock:
        if _page:
            return _page
        if _pw is None:
            _pw = await async_playwright().start()
        if _browser is None:
            _browser = await _pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
        if _page is None:
            _page = await _browser.new_page()
        return _page


async def close_browser():
    """Close and reset the shared browser/page."""
    global _pw, _browser, _page
    try:
        if _browser:
            await _browser.close()
        if _pw:
            await _pw.stop()
    finally:
        _pw = _browser = _page = None


async def recover_on_failure(action: str, error: Exception) -> str:
    """Recovery: observe minimal context after failure and return error with context."""
    try:
        p = await ensure_browser()
        title = await p.title()
        url = p.url
        context = f"TITLE: {title}\nURL: {url}"
    except Exception as e2:
        context = f"Could not read context: {str(e2)}"
    return f"{action}:failed:{str(error)}\nCONTEXT:\n{context}"


@tool
async def read_texts() -> str:
    """Return page title/url, sample of visible button/link texts, and input name/placeholders."""
    try:
        p = await ensure_browser()

        # Collect first 100 button/link-like elements' visible texts
        btns = []
        loc_btns = p.locator("button, a, [role='button']")
        count_btns = await loc_btns.count()
        limit_btns = min(count_btns, 100)
        for i in range(limit_btns):
            el = loc_btns.nth(i)
            try:
                t = (await el.inner_text(timeout=150) or "").strip()
                if t:
                    btns.append(t)
            except Exception:
                pass

        # Collect up to 100 inputs' name/placeholder
        inputs = []
        loc_inputs = p.locator("input, textarea, select")
        count_inputs = await loc_inputs.count()
        limit_inputs = min(count_inputs, 100)
        for i in range(limit_inputs):
            el = loc_inputs.nth(i)
            try:
                name = await el.get_attribute("name") or ""
                ph = await el.get_attribute("placeholder") or ""
                if name or ph:
                    inputs.append({"name": name, "placeholder": ph})
            except Exception:
                pass

        title = await p.title()
        return (
            f"TITLE: {title}\nURL: {p.url}\n"
            f"BUTTONS/LINKS: {btns}\n"
            f"INPUTS(name/placeholder): {inputs}"
        )
    except Exception as e:
        return await recover_on_failure("read_texts", e)


@tool
async def click_text(text: str) -> dict:
    """
    Click a button/link/icon/input by visible text, aria-label, title, placeholder, alt, or CSS class (case-insensitive substring).
    After completion, returns both the click result and a fresh observation via read_texts.
    """
    try:
        p = await ensure_browser()
        safe_text = text.replace("\n", " ").replace("\r", " ").strip()

        loc = p.locator(
            f"button:has-text('{safe_text}'), "
            f"a:has-text('{safe_text}'), "
            f"[role='button']:has-text('{safe_text}'), "
            f"[aria-label*='{safe_text}'], "
            f"[title*='{safe_text}'], "
            f"input[placeholder*='{safe_text}'], "
            f"input[aria-label*='{safe_text}'], "
            f"img[alt*='{safe_text}']"
        )

        if await loc.count() > 0:
            await loc.first.click()
            await p.wait_for_load_state('networkidle', timeout=7000)
            observation = await read_texts.ainvoke({})
            return {"act_result": "click:ok", "observation": observation}

        if safe_text and not safe_text[0].isdigit() and not safe_text.startswith('-'):
            icon_loc = p.locator(f".{safe_text}")
            if await icon_loc.count() > 0:
                await icon_loc.first.click()
                await p.wait_for_load_state('networkidle', timeout=7000)
                observation = await read_texts.ainvoke({})
                return {"act_result": "click:ok", "observation": observation}

        observation = await read_texts.ainvoke({})
        return {"act_result": "click:not_found", "observation": observation}
    except Exception as e:
        observation = await read_texts.ainvoke({})
        return {"act_result": await recover_on_failure("click_text", e), "observation": observation}

'''
@tool
async def fill_field(kv: str) -> dict:
    """
    Fill an input/textarea/select by name or placeholder.
    Format: key=value (e.g., email=alice@example.com or placeholder=Search=John).
    After completion, returns both the fill result and a fresh observation via read_texts.
    """
    try:
        p = await ensure_browser()
        m = re.match(r"\s*(.+?)\s*=\s*(.*)\s*", kv)
        if not m:
            observation = await read_texts.ainvoke({})
            return {"act_result": "fill:bad_format", "observation": observation}

        key, value = m.group(1), m.group(2)

        loc = p.locator(f"input[name='{key}'], textarea[name='{key}'], select[name='{key}']")
        if await loc.count() == 0:
            loc = p.locator(f"input[placeholder='{key}'], textarea[placeholder='{key}']")
        if await loc.count() == 0:
            observation = await read_texts.ainvoke({})
            return {"act_result": "fill:not_found", "observation": observation}

        tag = await loc.first.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            try:
                await loc.first.select_option(label=value)
            except Exception:
                await loc.first.select_option(value)
            observation = await read_texts.ainvoke({})
            return {"act_result": "fill:ok", "observation": observation}

        await loc.first.fill(value)
        await loc.first.focus()
        await p.wait_for_timeout(700)

        suggestion_selectors = [
            f"div:has-text('{value}')",
            f"[role='option']:has-text('{value}')",
            f".suggestion:has-text('{value}')",
            f".dropdown-item:has-text('{value}')",
            f"li:has-text('{value}')",
            f".autocomplete-suggestion:has-text('{value}')",
        ]
        for selector in suggestion_selectors:
            suggestion_loc = p.locator(selector)
            if await suggestion_loc.count() > 0:
                try:
                    suggestion_text = await suggestion_loc.first.inner_text()
                    await suggestion_loc.first.click()
                    await p.wait_for_timeout(300)
                    observation = await read_texts.ainvoke({})
                    return {
                        "act_result": f"fill:ok_suggestion_selected:{suggestion_text}",
                        "observation": observation,
                    }
                except Exception:
                    continue

        observation = await read_texts.ainvoke({})
        return {"act_result": "fill:ok", "observation": observation}

    except Exception as e:
        observation = await read_texts.ainvoke({})
        return {
            "act_result": await recover_on_failure("fill_field", e),
            "observation": observation,
        }
'''

@tool
async def fill_field(kv: str) -> dict:
    """
    Fill an input/textarea/select by name or placeholder.
    Supported formats:
      - key=value                        (e.g., email=alice@example.com or Value=John)
      - placeholder=Value=John           (explicit placeholder targeting)
    After completion, returns both the fill result and a fresh observation via read_texts.
    """
    try:
        p = await ensure_browser()

        # Parse "key=value"
        m = re.match(r"\s*(.+?)\s*=\s*(.*)\s*", kv)
        if not m:
            observation = await read_texts.ainvoke({})
            return {"act_result": "fill:bad_format", "observation": observation}

        key, value = m.group(1), m.group(2)

        # Optional "placeholder mode": placeholder=Value=foo
        if key and key.strip().lower() in ("placeholder", "ph"):
            if "=" in value:
                ph_text, real = value.split("=", 1)
                key, value = ph_text, real
            # if no "=", treat as bad format to avoid ambiguity
            else:
                observation = await read_texts.ainvoke({})
                return {"act_result": "fill:bad_format", "observation": observation}

        # Build locator: name exact -> placeholder exact -> placeholder contains
        loc = p.locator(f"input[name='{key}'], textarea[name='{key}'], select[name='{key}']")
        if await loc.count() == 0:
            loc = p.locator(f"input[placeholder='{key}'], textarea[placeholder='{key}']")
        if await loc.count() == 0:
            # contains-match for robustness (minimal added fallback)
            loc = p.locator(f"input[placeholder*='{key}'], textarea[placeholder*='{key}']")

        count = await loc.count()
        if count == 0:
            observation = await read_texts.ainvoke({})
            return {"act_result": "fill:not_found", "observation": observation}

        # Adaptive target: if one match use first; if multiple, prefer last (newly added rows)
        target = loc.first if count == 1 else loc.nth(count - 1)

        # Brief wait for visibility (helps right after "Add ..." actions)
        try:
            await target.wait_for(state="visible", timeout=3000)
        except Exception:
            pass

        # Select vs text fill
        tag = await target.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            try:
                await target.select_option(label=value)
            except Exception:
                await target.select_option(value)
            observation = await read_texts.ainvoke({})
            return {"act_result": "fill:ok", "observation": observation}

        # Fill text-like inputs / textarea
        await target.fill(value)
        await target.focus()
        await p.wait_for_timeout(700)

        # Optional suggestion pickers
        suggestion_selectors = [
            f"div:has-text('{value}')",
            f"[role='option']:has-text('{value}')",
            f".suggestion:has-text('{value}')",
            f".dropdown-item:has-text('{value}')",
            f"li:has-text('{value}')",
            f".autocomplete-suggestion:has-text('{value}')",
        ]
        for selector in suggestion_selectors:
            suggestion_loc = p.locator(selector)
            if await suggestion_loc.count() > 0:
                try:
                    suggestion_text = await suggestion_loc.first.inner_text()
                    await suggestion_loc.first.click()
                    await p.wait_for_timeout(300)
                    observation = await read_texts.ainvoke({})
                    return {
                        "act_result": f"fill:ok_suggestion_selected:{suggestion_text}",
                        "observation": observation,
                    }
                except Exception:
                    continue

        # Normal success
        observation = await read_texts.ainvoke({})
        return {"act_result": "fill:ok", "observation": observation}

    except Exception as e:
        observation = await read_texts.ainvoke({})
        return {
            "act_result": await recover_on_failure("fill_field", e),
            "observation": observation,
        }


@tool
async def get_secret(key: str) -> str:
    """Return env secrets for MEDPLUM_USER or MEDPLUM_PASS. Format 'KEY=value' or 'KEY=' if missing."""
    try:
        key = key.strip().upper()
        if key not in {"MEDPLUM_USER", "MEDPLUM_PASS"}:
            return "secret:not_allowed"
        val = os.getenv(key, "")
        return f"{key}={val}"
    except Exception as e:
        return await recover_on_failure("get_secret", e)


@tool
async def smart_search(search_term: str) -> str:
    """Intelligently search using any available search mechanism on the current page."""
    try:
        p = await ensure_browser()

        search_selectors = [
            "input[placeholder*='Search']",
            "input[placeholder*='search' i]",
            "input[type='search']",
            "input[name*='search' i]"
        ]
        for selector in search_selectors:
            try:
                search_field = p.locator(selector)
                if await search_field.count() > 0:
                    await search_field.first.click()
                    await search_field.first.fill(search_term)
                    await search_field.first.press("Enter")
                    await p.wait_for_timeout(1000)
                    return f"search_success:{search_term}"
            except Exception:
                continue

        try:
            result = await fill_field(f"Search={search_term}")
            if "ok" in result:
                return f"search_fallback_success:{search_term}"
        except Exception:
            pass

        return "search_failed"
    except Exception as e:
        return await recover_on_failure("smart_search", e)


@tool
async def navigate_to_main_page() -> dict:
    """
    Navigate to main page or reset location to main/landing page before starting a new task.
    After completion, returns both the navigation result and a fresh observation via read_texts.
    """
    try:
        p = await ensure_browser()
        home_selectors = [
            "a[href='/'], a[href='#/']",
            ".logo, .brand, .navbar-brand",
            "[aria-label*='home' i], [title*='home' i]",
            ".navbar-brand, .logo",
        ]
        for selector in home_selectors:
            try:
                loc = p.locator(selector)
                if await loc.count() > 0:
                    await loc.first.click()
                    await p.wait_for_load_state('networkidle', timeout=7000)
                    observation = await read_texts.ainvoke({})
                    return {"act_result": f"reset_via_click:{p.url}", "observation": observation}
            except Exception:
                continue

        try:
            await p.goto(BASE_URL)
            await p.wait_for_load_state('networkidle', timeout=7000)
            await p.wait_for_timeout(1000)
            observation = await read_texts.ainvoke({})
            return {"act_result": f"reset_via_base_url:{p.url}", "observation": observation}
        except Exception as e:
            observation = await read_texts.ainvoke({})
            return {"act_result": f"reset_failed:{str(e)}", "observation": observation}
    except Exception as e:
        observation = await read_texts.ainvoke({})
        return {"act_result": await recover_on_failure("navigate_to_main_page", e), "observation": observation}


@tool
async def capture_screenshot(path: str) -> str:
    """Capture a screenshot of the outcome of the request as evidence.
    Saves to screenshots/ directory and waits for the page to stabilize."""
    try:
        p = await ensure_browser()
        screenshots_dir = "screenshots"
        os.makedirs(screenshots_dir, exist_ok=True)

        filename = os.path.basename(path)
        full_path = os.path.join(screenshots_dir, filename)

        # Wait until the page is fully loaded and stable
        try:
            await p.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # If it fails, still try to capture

        # Small delay to ensure UI rendered (especially in headless mode)
        await p.wait_for_timeout(1000)

        # Capture screenshot
        await p.screenshot(path=full_path, full_page=True, timeout=60000)
        return full_path

    except Exception as e:
        if "timeout" in str(e).lower():
            return f"screenshot_timeout_skipped: {path}"
        else:
            return await recover_on_failure("capture_screenshot", e)


@tool
async def validate_claim_advanced(claim: str, context: str = "") -> dict:
    """
    Advanced validation using vision model to analyze claims against current page state.
    Uses the capture_screenshot tool to get current browser state for validation.
    Returns a dict with validation result and screenshot_path for frontend display.
    """
    try:
        from langchain_openai import ChatOpenAI
        import base64

        screenshot_filename = f"validation_{hash(claim) % 10000}.png"
        screenshot_path = os.path.join("screenshots", screenshot_filename)

        screenshot_result = await capture_screenshot.ainvoke({"path": screenshot_path})
        if "failed" in screenshot_result or "timeout" in screenshot_result:
            return {
                "status": "error",
                "message": f"VALIDATION_ERROR: {screenshot_result}",
                "screenshot_path": screenshot_path
            }

        try:
            with open(screenshot_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode()
        except Exception as e:
            return {
                "status": "error",
                "message": f"VALIDATION_ERROR: Could not read screenshot: {str(e)}",
                "screenshot_path": screenshot_path
            }

        p = await ensure_browser()
        current_url = p.url

        validation_llm = ChatOpenAI(model="gpt-4o", temperature=0)
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

Current page URL: {current_url}
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
            result = await validation_llm.ainvoke(validation_prompt)
            return {
                "status": "success",
                "message": result.content,
                "screenshot_path": screenshot_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"VALIDATION_ERROR: LLM validation failed: {str(e)}",
                "screenshot_path": screenshot_path
            }
    except Exception as e:
        return {
            "status": "error",
            "message": await recover_on_failure("validate_claim_advanced", e),
            "screenshot_path": None
        }


# export list for main
TOOLS = [
    read_texts,
    click_text,
    fill_field,
    get_secret,
    smart_search,
    navigate_to_main_page,
    capture_screenshot,
    validate_claim_advanced,
]
