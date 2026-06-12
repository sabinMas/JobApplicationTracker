"""
Enhanced automation for fully automated job application submission.
Handles form detection, filling, and submission across different ATS platforms.
"""
import asyncio

try:
    from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = None
    PlaywrightTimeoutError = Exception

from .ats_integration import get_submit_button_selectors, get_form_field_selectors


async def detect_and_fill_required_fields(
    page: Page,
    profile: dict,
    timeout: int = 5000
) -> dict[str, bool]:
    """
    Intelligently detect and fill all visible form fields.
    Returns mapping of field names to fill success status.
    """
    filled = {}

    field_mapping = {
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "full_name": profile.get("full_name", ""),
        "linkedin_url": profile.get("linkedin_url", ""),
        "github_url": profile.get("github_url", ""),
        "location": profile.get("location", ""),
    }

    # Try standard input fields
    selectors = get_form_field_selectors("default")

    for field_type, value in field_mapping.items():
        if not value:
            continue

        field_selectors = selectors.get(field_type, [])

        for selector in field_selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=timeout):
                    await locator.click()
                    await locator.clear()
                    await locator.fill(str(value))
                    filled[field_type] = True
                    await asyncio.sleep(0.2)
                    break
            except (PlaywrightTimeoutError, Exception):
                continue

        filled.setdefault(field_type, False)

    # Try dropdowns/select elements
    await _fill_dropdowns(page, profile)

    # Try checkboxes (e.g., "I agree to terms")
    await _fill_checkboxes(page)

    return filled


async def _fill_dropdowns(page: Page, profile: dict) -> None:
    """Fill select/dropdown elements with relevant values from profile."""
    try:
        selects = await page.query_selector_all("select")
        for select in selects:
            try:
                label = await select.evaluate("el => el.previousElementSibling?.textContent || el.aria_label || ''")

                # Try to match dropdown to profile field
                if any(x in str(label).lower() for x in ["job type", "employment"]):
                    await select.select_option("full-time")
                elif any(x in str(label).lower() for x in ["notice period", "available"]):
                    await select.select_option("2 weeks")

            except Exception:
                continue
    except Exception:
        pass


async def _fill_checkboxes(page: Page) -> None:
    """
    Auto-check important checkboxes like terms of service, legal agreements.
    CAUTION: Only check checkboxes that are clearly mandatory/consent-related.
    """
    try:
        checkboxes = await page.query_selector_all("input[type='checkbox']")
        for checkbox in checkboxes:
            try:
                label = await checkbox.evaluate(
                    "el => (el.nextElementSibling?.textContent || el.aria_label || '').toLowerCase()"
                )

                # Only auto-check specific known agreement types
                important_keywords = [
                    "agree", "accept", "terms", "conditions",
                    "privacy", "legal", "consent", "eligibility"
                ]

                if any(kw in label for kw in important_keywords):
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await checkbox.check()
                        await asyncio.sleep(0.1)

            except Exception:
                continue
    except Exception:
        pass


async def find_and_click_submit(page: Page, ats_type: str = "default") -> bool:
    """
    Find the submit/apply button and click it.
    Returns True if successfully submitted, False otherwise.
    """
    selectors = get_submit_button_selectors(ats_type)

    for selector in selectors:
        try:
            button = page.locator(selector).first
            if await button.is_visible(timeout=2000):
                await button.click()
                # Wait a moment for submission to process
                await asyncio.sleep(1)
                return True
        except (PlaywrightTimeoutError, Exception):
            continue

    return False


async def detect_submission_success(page: Page) -> bool:
    """
    Check if the application was successfully submitted.
    Look for success messages or URL changes.
    """
    try:
        # Check for success messages
        success_messages = [
            "text=Thank you",
            "text=Success",
            "text=Application submitted",
            "text=We've received",
            "text=Submitted successfully",
        ]

        for message in success_messages:
            try:
                if await page.locator(message).is_visible(timeout=2000):
                    return True
            except Exception:
                continue

        # Check if page redirected (indicates successful submission)
        current_url = page.url
        if any(x in current_url.lower() for x in ["/success", "/thank", "/submitted"]):
            return True

        return False
    except Exception:
        return False


async def wait_for_form_load(page: Page, timeout: int = 10000) -> bool:
    """Wait for form elements to load on the page."""
    try:
        # Wait for any form element
        await page.wait_for_selector("form, input, [role='form']", timeout=timeout)
        await asyncio.sleep(0.5)  # Brief pause for JS to finish rendering
        return True
    except PlaywrightTimeoutError:
        return False


async def handle_required_fields_indicator(page: Page) -> list[str]:
    """
    Identify required fields (marked with * or required attribute).
    Useful for prioritizing which fields to fill.
    """
    required = await page.evaluate("""
        () => {
            const required_labels = [];

            // Check for inputs with 'required' attribute
            document.querySelectorAll("input[required], textarea[required], select[required]").forEach(el => {
                const label = el.previousElementSibling?.textContent ||
                             el.aria_label ||
                             el.placeholder || '';
                if (label) required_labels.push(label.trim());
            });

            // Check for labels containing asterisk (*)
            document.querySelectorAll("label").forEach(el => {
                if (el.textContent.includes("*")) {
                    required_labels.push(el.textContent.replace("*", "").trim());
                }
            });

            return [...new Set(required_labels)]; // Remove duplicates
        }
    """)

    return required or []
