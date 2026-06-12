"""
Playwright-based browser automation for job application form filling.
Runs in headed (visible) Chromium so the user can watch and intervene.
"""
import asyncio
import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = None
    Browser = None
    BrowserContext = None

from .websocket_manager import ws_manager
from . import ai_service


# Active sessions: session_id -> session state dict
_sessions: Dict[str, dict] = {}


async def _broadcast(session_id: str, step: str, status: str, message: str, page: Optional[Page] = None):
    event = {
        "session_id": session_id,
        "step": step,
        "status": status,
        "message": message,
        "screenshot_b64": None,
    }
    if page:
        try:
            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
            event["screenshot_b64"] = base64.b64encode(screenshot_bytes).decode()
        except Exception:
            pass
    await ws_manager.broadcast(session_id, event)


async def start_session(application_id: int, apply_url: str) -> str:
    """Launch a headed Chromium browser and navigate to the apply URL."""
    session_id = str(uuid.uuid4())

    playwright = await async_playwright().start()
    browser: Browser = await playwright.chromium.launch(
        headless=False,
        args=["--start-maximized"],
        slow_mo=50,  # slight slow-down for human-like pacing
    )
    context: BrowserContext = await browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    page: Page = await context.new_page()

    _sessions[session_id] = {
        "playwright": playwright,
        "browser": browser,
        "context": context,
        "page": page,
        "application_id": application_id,
        "apply_url": apply_url,
        "status": "navigating",
        "log": [],
        "paused": False,
        "pause_event": asyncio.Event(),
    }
    _sessions[session_id]["pause_event"].set()  # not paused initially

    await page.goto(apply_url, wait_until="domcontentloaded", timeout=30000)
    await _broadcast(session_id, "navigate", "running", f"Opened: {apply_url}", page)

    return session_id


async def get_form_fields(session_id: str) -> list[str]:
    """Extract visible form field labels from the current page."""
    session = _sessions.get(session_id)
    if not session:
        return []
    page: Page = session["page"]

    labels = await page.evaluate("""
        () => {
            const results = [];
            // Get label elements
            document.querySelectorAll('label').forEach(el => {
                const text = el.innerText.trim();
                if (text) results.push(text);
            });
            // Get placeholder attributes
            document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(el => {
                const p = el.getAttribute('placeholder');
                if (p && !results.includes(p)) results.push(p);
            });
            // Get aria-labels
            document.querySelectorAll('[aria-label]').forEach(el => {
                const a = el.getAttribute('aria-label');
                if (a && !results.includes(a)) results.push(a);
            });
            return results;
        }
    """)
    return labels or []


async def fill_form(session_id: str, profile: dict) -> list[dict]:
    """
    AI-maps form fields to profile values and fills the form.
    Returns the automation log entries for this step.
    """
    session = _sessions.get(session_id)
    if not session:
        return []

    page: Page = session["page"]
    log = []

    await _broadcast(session_id, "detect_fields", "running", "Detecting form fields...", page)

    field_labels = await get_form_fields(session_id)
    if not field_labels:
        await _broadcast(session_id, "detect_fields", "error", "No form fields detected.", page)
        return log

    await _broadcast(session_id, "detect_fields", "running", f"Found {len(field_labels)} fields. Mapping with AI...", page)

    field_mapping = await ai_service.map_form_fields(field_labels, profile)

    for label, value in field_mapping.items():
        # Wait if paused
        await session["pause_event"].wait()

        if not value:
            continue

        try:
            # Try to find input by label text
            filled = False
            for selector in [
                f"label:has-text('{label}') + input",
                f"label:has-text('{label}') + textarea",
                f"input[placeholder*='{label}']",
                f"textarea[placeholder*='{label}']",
                f"input[aria-label*='{label}']",
            ]:
                try:
                    locator = page.locator(selector).first
                    if await locator.is_visible(timeout=1000):
                        await locator.click()
                        await locator.fill(str(value))
                        filled = True
                        break
                except Exception:
                    continue

            if filled:
                entry = {
                    "step": "fill_field",
                    "status": "success",
                    "message": f"Filled '{label}'",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                log.append(entry)
                session["log"].append(entry)
                await _broadcast(session_id, "fill_field", "running", f"✓ Filled: {label}", page)
                await asyncio.sleep(0.3)  # brief human-like pause between fields

        except Exception as e:
            entry = {
                "step": "fill_field",
                "status": "error",
                "message": f"Could not fill '{label}': {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            log.append(entry)
            session["log"].append(entry)

    await _broadcast(session_id, "fill_form", "running", "Form filling complete. Review before submitting.", page)
    return log


async def upload_documents(
    session_id: str,
    resume_path: Optional[str] = None,
    cover_letter_path: Optional[str] = None,
):
    """Upload resume and/or cover letter to file input fields."""
    session = _sessions.get(session_id)
    if not session:
        return

    page: Page = session["page"]

    file_inputs = await page.query_selector_all("input[type='file']")
    if not file_inputs:
        await _broadcast(session_id, "upload_docs", "running", "No file upload fields found on this page.", page)
        return

    # Heuristic: first file input = resume, second = cover letter
    for i, file_input in enumerate(file_inputs[:2]):
        file_path = resume_path if i == 0 else cover_letter_path
        doc_label = "resume" if i == 0 else "cover letter"
        if file_path and Path(file_path).exists():
            try:
                await file_input.set_input_files(file_path)
                await _broadcast(session_id, "upload_docs", "running", f"✓ Uploaded {doc_label}", page)
                await asyncio.sleep(1)
            except Exception as e:
                await _broadcast(session_id, "upload_docs", "error", f"Failed to upload {doc_label}: {e}", page)


async def take_screenshot(session_id: str) -> Optional[str]:
    """Return base64-encoded JPEG screenshot of current page."""
    session = _sessions.get(session_id)
    if not session:
        return None
    try:
        page: Page = session["page"]
        data = await page.screenshot(type="jpeg", quality=75)
        return base64.b64encode(data).decode()
    except Exception:
        return None


async def pause_session(session_id: str):
    session = _sessions.get(session_id)
    if session:
        session["paused"] = True
        session["pause_event"].clear()
        session["status"] = "paused"
        await _broadcast(session_id, "control", "paused", "Automation paused. You have control.")


async def resume_session(session_id: str):
    session = _sessions.get(session_id)
    if session:
        session["paused"] = False
        session["pause_event"].set()
        session["status"] = "running"
        await _broadcast(session_id, "control", "running", "Automation resumed.")


async def stop_session(session_id: str):
    session = _sessions.get(session_id)
    if session:
        try:
            await session["browser"].close()
            await session["playwright"].stop()
        except Exception:
            pass
        session["status"] = "stopped"
        await ws_manager.broadcast(session_id, {
            "session_id": session_id,
            "step": "control",
            "status": "done",
            "message": "Session closed.",
        })
        del _sessions[session_id]


def get_session_status(session_id: str) -> Optional[dict]:
    session = _sessions.get(session_id)
    if not session:
        return None
    return {
        "session_id": session_id,
        "status": session["status"],
        "log": session["log"],
        "paused": session["paused"],
    }


class PlaywrightService:
    """Wrapper for simple Playwright page fetching for scrapers."""

    def __init__(self):
        """Initialize browser components as None - lazy loaded on first use."""
        self._playwright = None
        self._browser = None
        self._context = None
        self._logger = None

    async def _init_browser(self):
        """Initialize browser on first use (lazy loading)."""
        if self._browser is not None:
            return

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            self._context = await self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize Playwright browser: {e}")
            raise

    async def fetch_page(self, url: str, timeout: int = 30000) -> Optional[str]:
        """
        Fetch a page and return its HTML content.

        Args:
            url: The URL to fetch
            timeout: Request timeout in milliseconds

        Returns:
            HTML content as string, or None if fetch failed
        """
        try:
            await self._init_browser()

            page = await self._context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                html = await page.content()
                return html
            finally:
                await page.close()

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    async def close(self):
        """Clean up browser and Playwright resources."""
        try:
            if self._context:
                await self._context.close()
                self._context = None
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error closing Playwright: {e}")
