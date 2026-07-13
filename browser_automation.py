import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def fill_and_submit_form(url: str, data: dict, headless: bool = True):
    """
    Opens a URL, finds a contact form, fills it with the provided data, and submits it.
    
    :param url: The URL of the contact page.
    :param data: A dictionary containing the data to fill. 
                 Expected keys: 'name', 'email', 'message' (and optionally 'subject', 'phone').
    :param headless: If True, runs in the background. If False, you can see the browser.
    """
    logging.info(f"Starting browser automation for {url}")
    
    async with async_playwright() as p:
        # Launch the browser
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            logging.info("Navigating to URL...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait a bit for any dynamic content to load
            await page.wait_for_timeout(2000)

            # --- SMART FIELD DETECTION ---
            # 1. Find Name Field
            name_selectors = [
                'input[type="text"]', 
                'input[name*="name"]', 
                'input[placeholder*="name" i]',
                'input[aria-label*="name" i]'
            ]
            for selector in name_selectors:
                try:
                    name_input = page.query_selector(selector)
                    if name_input and await name_input.is_visible():
                        await name_input.fill(data.get('name', ''))
                        logging.info("Filled Name field.")
                        break
                except Exception:
                    continue

            # 2. Find Email Field
            email_selectors = [
                'input[type="email"]', 
                'input[name*="email"]', 
                'input[placeholder*="email" i]',
                'input[aria-label*="email" i]'
            ]
            for selector in email_selectors:
                try:
                    email_input = page.query_selector(selector)
                    if email_input and await email_input.is_visible():
                        await email_input.fill(data.get('email', ''))
                        logging.info("Filled Email field.")
                        break
                except Exception:
                    continue

            # 3. Find Message/Textarea Field
            message_selectors = [
                'textarea', 
                'textarea[name*="message"]', 
                'textarea[placeholder*="message" i]',
                'div[contenteditable="true"]'
            ]
            for selector in message_selectors:
                try:
                    msg_input = page.query_selector(selector)
                    if msg_input and await msg_input.is_visible():
                        await msg_input.fill(data.get('message', ''))
                        logging.info("Filled Message field.")
                        break
                except Exception:
                    continue

            # 4. Find and Click Submit Button
            submit_selectors = [
                'button[type="submit"]', 
                'input[type="submit"]', 
                'button:has-text("Submit")', 
                'button:has-text("Send")',
                'input[value="Send"]'
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    submit_btn = page.query_selector(selector)
                    if submit_btn and await submit_btn.is_visible():
                        await submit_btn.click()
                        logging.info("Clicked Submit button!")
                        submitted = True
                        break
                except Exception:
                    continue

            if not submitted:
                logging.warning("Could not find a submit button.")

            await page.wait_for_timeout(3000)
            logging.info("Form submission process completed.")
            
            return True

        except Exception as e:
            logging.error(f"Automation failed: {e}")
            return False
            
        finally:
            await browser.close()
            logging.info("Browser closed.")

# --- Test Function ---
def test_automation():
    test_url = "https://www.w3schools.com/html/tryit.asp?filename=tryhtml_form_submit"
    
    test_data = {
        "name": "Hunti AI Bot",
        "email": "test@huntiai.com",
        "message": "This is an automated test message from Hunti AI!"
    }
    
    # Run with headless=False so you can WATCH it work!
    asyncio.run(fill_and_submit_form(test_url, test_data, headless=True))

if __name__ == "__main__":
    test_automation()