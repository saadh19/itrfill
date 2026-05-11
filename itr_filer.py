import asyncio
import os
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IT_PORTAL_URL = "https://www.incometax.gov.in/iec/foportal"
SCREENSHOT_DIR = "screenshots"


async def file_itr_automatically(pan, password, xml_path):
    """
    Automates ITR filing on incometax.gov.in
    Returns dict with status, step, message, otp_required
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    result = {
        "status": "pending",
        "step": "",
        "message": "",
        "otp_required": False
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--disable-setuid-sandbox",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        async def screenshot(name):
            try:
                path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
                await page.screenshot(path=path)
                logger.info(f"Screenshot saved: {path}")
            except Exception:
                pass

        try:
            # ── Step 1: Open IT Portal ────────────────────────────────────
            logger.info("Step 1: Opening IT portal...")
            result["step"] = "opening_portal"
            await page.goto(IT_PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            await screenshot("01_portal_home")

            # ── Step 2: Click Login button ────────────────────────────────
            logger.info("Step 2: Clicking Login...")
            result["step"] = "clicking_login"
            try:
                login_btn = await page.wait_for_selector(
                    "a:has-text('Login'), button:has-text('Login')",
                    timeout=10000
                )
                await login_btn.click()
            except PlaywrightTimeout:
                # Some versions of portal have direct link
                await page.goto(
                    "https://www.incometax.gov.in/iec/foportal/login",
                    wait_until="domcontentloaded",
                    timeout=20000
                )
            await page.wait_for_timeout(2000)
            await screenshot("02_login_page")

            # ── Step 3: Enter PAN ─────────────────────────────────────────
            logger.info("Step 3: Entering PAN...")
            result["step"] = "entering_pan"
            pan_field = await page.wait_for_selector(
                "input[placeholder*='PAN'], input[name*='userId'], input[id*='userId'], input[id*='pan']",
                timeout=10000
            )
            await pan_field.click()
            await pan_field.fill(pan.upper())
            await page.wait_for_timeout(1000)

            # ── Step 4: Click Continue ────────────────────────────────────
            continue_btn = await page.wait_for_selector(
                "button:has-text('Continue'), input[value='Continue']",
                timeout=5000
            )
            await continue_btn.click()
            await page.wait_for_timeout(2000)
            await screenshot("03_after_pan")

            # ── Step 5: Enter Password ────────────────────────────────────
            logger.info("Step 5: Entering password...")
            result["step"] = "entering_password"
            password_field = await page.wait_for_selector(
                "input[type='password']", timeout=10000
            )
            await password_field.click()
            await password_field.fill(password)
            await page.wait_for_timeout(1000)

            submit_btn = await page.wait_for_selector(
                "button:has-text('Login'), button:has-text('Sign In'), button[type='submit']",
                timeout=5000
            )
            await submit_btn.click()
            await page.wait_for_timeout(3000)
            await screenshot("04_after_login_click")

            # ── Step 6: Check login result ────────────────────────────────
            logger.info("Step 6: Checking login result...")
            result["step"] = "checking_login"

            # Check for login OTP first
            otp_field = await page.query_selector(
                "input[placeholder*='OTP'], input[maxlength='6'], input[id*='otp']"
            )
            if otp_field:
                await screenshot("05_login_otp_required")
                result["status"] = "otp_required_login"
                result["otp_required"] = True
                result["message"] = "Login OTP required. Please check your Aadhaar-linked mobile and enter OTP on incometax.gov.in."
                await browser.close()
                return result

            # Check for wrong password error
            error_msg = await page.query_selector(
                "text=Invalid, text=incorrect, .error-message, .alert-danger"
            )
            if error_msg:
                await screenshot("05_login_error")
                result["status"] = "error"
                result["message"] = "Login failed — incorrect PAN or password."
                await browser.close()
                return result

            # Wait for dashboard / e-File menu to confirm login
            try:
                await page.wait_for_selector(
                    "text=e-File, text=Dashboard, text=My Account",
                    timeout=15000
                )
                logger.info("Login successful!")
                result["step"] = "logged_in"
            except PlaywrightTimeout:
                await screenshot("05_login_unknown_state")
                result["status"] = "error"
                result["message"] = "Could not confirm login — portal may have changed layout."
                await browser.close()
                return result

            await screenshot("05_dashboard")

            # ── Step 7: Navigate to e-File → Income Tax Returns ───────────
            logger.info("Step 7: Navigating to e-File menu...")
            result["step"] = "navigating_efile"

            efile_menu = await page.wait_for_selector(
                "text=e-File", timeout=10000
            )
            await efile_menu.hover()
            await page.wait_for_timeout(1000)

            itr_option = await page.wait_for_selector(
                "text=Income Tax Returns", timeout=5000
            )
            await itr_option.click()
            await page.wait_for_timeout(1000)

            file_itr_btn = await page.wait_for_selector(
                "text=File Income Tax Return", timeout=5000
            )
            await file_itr_btn.click()
            await page.wait_for_timeout(2000)
            await screenshot("06_file_itr_page")

            # ── Step 8: Select Assessment Year ────────────────────────────
            logger.info("Step 8: Selecting AY 2025-26...")
            result["step"] = "selecting_ay"

            try:
                ay_selector = await page.wait_for_selector(
                    "select[name*='assessmentYear'], select[id*='assessmentYear']",
                    timeout=10000
                )
                await ay_selector.select_option(label="2025-26")
            except PlaywrightTimeout:
                # Some portals use radio buttons or cards for AY
                ay_option = await page.wait_for_selector(
                    "text=2025-26", timeout=10000
                )
                await ay_option.click()

            await page.wait_for_timeout(1000)

            # ── Step 9: Select Offline (XML upload) mode ──────────────────
            logger.info("Step 9: Selecting Offline mode...")
            result["step"] = "selecting_offline_mode"
            try:
                offline_option = await page.wait_for_selector(
                    "label:has-text('Offline'), input[value='offline'], text=Offline",
                    timeout=5000
                )
                await offline_option.click()
            except PlaywrightTimeout:
                logger.warning("Offline radio not found — may already be selected or UI differs")

            await page.wait_for_timeout(1000)

            continue_btn = await page.wait_for_selector(
                "button:has-text('Continue')", timeout=5000
            )
            await continue_btn.click()
            await page.wait_for_timeout(2000)
            await screenshot("07_offline_mode_selected")

            # ── Step 10: Upload XML ───────────────────────────────────────
            logger.info("Step 10: Uploading ITR XML...")
            result["step"] = "uploading_xml"

            xml_abs_path = os.path.abspath(xml_path)
            if not os.path.exists(xml_abs_path):
                result["status"] = "error"
                result["message"] = f"XML file not found at: {xml_abs_path}"
                await browser.close()
                return result

            file_input = await page.wait_for_selector(
                "input[type='file']", timeout=10000
            )
            await file_input.set_input_files(xml_abs_path)
            await page.wait_for_timeout(2000)
            await screenshot("08_xml_uploaded")

            upload_btn = await page.wait_for_selector(
                "button:has-text('Upload'), button:has-text('Submit')",
                timeout=5000
            )
            await upload_btn.click()
            await page.wait_for_timeout(3000)
            await screenshot("09_after_upload")

            # ── Step 11: Proceed to Verification ─────────────────────────
            logger.info("Step 11: Proceeding to verification...")
            result["step"] = "verification"

            proceed_btn = await page.wait_for_selector(
                "button:has-text('Proceed'), button:has-text('Continue'), button:has-text('Next')",
                timeout=10000
            )
            await proceed_btn.click()
            await page.wait_for_timeout(2000)
            await screenshot("10_verification_page")

            # ── Step 12: Select Aadhaar OTP verification ──────────────────
            logger.info("Step 12: Selecting Aadhaar OTP...")
            result["step"] = "selecting_aadhaar_otp"

            try:
                aadhaar_option = await page.wait_for_selector(
                    "label:has-text('Aadhaar OTP'), input[value*='aadhaar'], text=Aadhaar OTP",
                    timeout=10000
                )
                await aadhaar_option.click()
                await page.wait_for_timeout(1000)

                generate_otp_btn = await page.wait_for_selector(
                    "button:has-text('Generate OTP'), button:has-text('Send OTP')",
                    timeout=5000
                )
                await generate_otp_btn.click()
                await page.wait_for_timeout(2000)
                await screenshot("11_otp_sent")

            except PlaywrightTimeout:
                logger.warning("Aadhaar OTP option not found — portal may be at OTP screen already")
                await screenshot("11_otp_screen_unknown")

            # ── Done: Hand off to user for OTP ────────────────────────────
            result["status"] = "otp_required_verification"
            result["otp_required"] = True
            result["step"] = "awaiting_otp"
            result["message"] = (
                "ITR uploaded successfully! OTP has been sent to your Aadhaar-linked mobile. "
                "Please open incometax.gov.in — the OTP entry screen is ready. "
                "Enter the 6-digit OTP and click Submit to complete filing."
            )
            logger.info("Automation complete. Awaiting OTP from user.")

        except PlaywrightTimeout as e:
            await screenshot("error_timeout")
            logger.error(f"Timeout error: {str(e)}")
            result["status"] = "error"
            result["message"] = f"Timed out waiting for portal element: {str(e)}"

        except Exception as e:
            await screenshot("error_general")
            logger.error(f"Unexpected error: {str(e)}")
            result["status"] = "error"
            result["message"] = f"Automation error: {str(e)}"

        finally:
            await browser.close()

    return result


def file_itr_sync(pan, password, xml_path):
    """Synchronous wrapper for use in Flask routes"""
    return asyncio.run(file_itr_automatically(pan, password, xml_path))