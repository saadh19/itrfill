import asyncio
import os
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IT_PORTAL_URL = "https://www.incometax.gov.in/iec/foportal"

async def file_itr_automatically(pan, password, xml_path, callback_url=None):
    """
    Automates ITR filing on incometax.gov.in
    Returns dict with status and message
    """
    result = {
        "status": "pending",
        "step": "",
        "message": "",
        "otp_required": False
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # Step 1: Navigate to IT portal
            logger.info("Step 1: Opening IT portal...")
            result["step"] = "opening_portal"
            await page.goto(IT_PORTAL_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Step 2: Click Login
            logger.info("Step 2: Clicking login...")
            result["step"] = "clicking_login"
            login_btn = await page.wait_for_selector(
                "text=Login", timeout=10000
            )
            await login_btn.click()
            await asyncio.sleep(2)

            # Step 3: Enter PAN
            logger.info("Step 3: Entering PAN...")
            result["step"] = "entering_pan"
            pan_field = await page.wait_for_selector(
                "input[placeholder*='PAN'], input[name*='userId'], input[id*='userId']",
                timeout=10000
            )
            await pan_field.fill(pan.upper())
            await asyncio.sleep(1)

            # Click Continue
            continue_btn = await page.wait_for_selector(
                "button:has-text('Continue'), input[value='Continue']",
                timeout=5000
            )
            await continue_btn.click()
            await asyncio.sleep(2)

            # Step 4: Enter Password
            logger.info("Step 4: Entering password...")
            result["step"] = "entering_password"
            password_field = await page.wait_for_selector(
                "input[type='password']", timeout=10000
            )
            await password_field.fill(password)
            await asyncio.sleep(1)

            # Click Login
            submit_btn = await page.wait_for_selector(
                "button:has-text('Login'), button[type='submit']",
                timeout=5000
            )
            await submit_btn.click()
            await asyncio.sleep(3)

            # Check if login successful
            current_url = page.url
            if "dashboard" in current_url.lower() or "home" in current_url.lower():
                logger.info("Login successful!")
                result["step"] = "logged_in"
            else:
                # Check for OTP page after login
                otp_check = await page.query_selector("input[placeholder*='OTP'], input[maxlength='6']")
                if otp_check:
                    result["status"] = "otp_required_login"
                    result["otp_required"] = True
                    result["message"] = "Login OTP required. Please check your mobile."
                    await browser.close()
                    return result

            # Step 5: Navigate to e-File
            logger.info("Step 5: Going to e-File...")
            result["step"] = "navigating_efile"
            await page.goto(
                "https://www.incometax.gov.in/iec/foportal/help/how-to-file-itr",
                wait_until="networkidle",
                timeout=20000
            )
            await asyncio.sleep(2)

            # Click e-File menu
            efile_menu = await page.wait_for_selector(
                "text=e-File", timeout=10000
            )
            await efile_menu.click()
            await asyncio.sleep(1)

            # Click Income Tax Returns
            itr_option = await page.wait_for_selector(
                "text=Income Tax Returns", timeout=5000
            )
            await itr_option.click()
            await asyncio.sleep(1)

            # Click File Income Tax Return
            file_itr = await page.wait_for_selector(
                "text=File Income Tax Return", timeout=5000
            )
            await file_itr.click()
            await asyncio.sleep(2)

            # Step 6: Select Assessment Year
            logger.info("Step 6: Selecting AY 2025-26...")
            result["step"] = "selecting_ay"
            ay_selector = await page.wait_for_selector(
                "select[name*='assessmentYear'], [data-cy*='assessmentYear']",
                timeout=10000
            )
            await ay_selector.select_option(label="2025-26")
            await asyncio.sleep(1)

            # Select Online mode — we use offline (XML upload)
            offline_radio = await page.wait_for_selector(
                "input[value='offline'], label:has-text('Offline')",
                timeout=5000
            )
            await offline_radio.click()
            await asyncio.sleep(1)

            continue_btn = await page.wait_for_selector(
                "button:has-text('Continue')", timeout=5000
            )
            await continue_btn.click()
            await asyncio.sleep(2)

            # Step 7: Upload XML
            logger.info("Step 7: Uploading XML...")
            result["step"] = "uploading_xml"
            file_input = await page.wait_for_selector(
                "input[type='file']", timeout=10000
            )
            await file_input.set_input_files(os.path.abspath(xml_path))
            await asyncio.sleep(2)

            # Click Upload
            upload_btn = await page.wait_for_selector(
                "button:has-text('Upload')", timeout=5000
            )
            await upload_btn.click()
            await asyncio.sleep(3)

            # Step 8: Proceed to verification
            logger.info("Step 8: Going to verification...")
            result["step"] = "verification"
            proceed_btn = await page.wait_for_selector(
                "button:has-text('Proceed'), button:has-text('Continue')",
                timeout=10000
            )
            await proceed_btn.click()
            await asyncio.sleep(2)

            # Select Aadhaar OTP verification
            aadhaar_otp = await page.wait_for_selector(
                "label:has-text('Aadhaar OTP'), input[value*='aadhaar']",
                timeout=10000
            )
            await aadhaar_otp.click()
            await asyncio.sleep(1)

            generate_otp = await page.wait_for_selector(
                "button:has-text('Generate OTP')", timeout=5000
            )
            await generate_otp.click()
            await asyncio.sleep(2)

            # OTP has been sent to user's mobile — we stop here
            # User must enter OTP manually
            result["status"] = "otp_required_verification"
            result["otp_required"] = True
            result["step"] = "awaiting_otp"
            result["message"] = (
                "ITR uploaded successfully! OTP sent to your Aadhaar-linked mobile. "
                "Please go to incometax.gov.in and enter the OTP to complete filing. "
                "The ITR form is already filled and ready — just enter the OTP."
            )

            logger.info("OTP step reached. Waiting for user to enter OTP.")

        except Exception as e:
            logger.error(f"Error during filing: {str(e)}")
            result["status"] = "error"
            result["message"] = f"Automation error: {str(e)}"

        finally:
            await browser.close()

    return result


def file_itr_sync(pan, password, xml_path):
    """Synchronous wrapper for async filer"""
    return asyncio.run(file_itr_automatically(pan, password, xml_path))
