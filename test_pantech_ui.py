import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 950})
        
        print("1. Navigating to http://127.0.0.1:8000/static/index.html...")
        await page.goto("http://127.0.0.1:8000/static/index.html", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        
        # 1. Open bot dropdown menu
        print("2. Opening bot dropdown...")
        await page.click("#btn-bot-dropdown")
        await page.wait_for_timeout(500)
        
        # Capture screenshot of dropdown with Pantech option
        await page.screenshot(path="/Users/faizan/.gemini/antigravity/brain/5048cda7-761c-4bb4-b7d7-88a56df02f96/pantech_ui_dropdown.png")
        print("Saved dropdown screenshot: pantech_ui_dropdown.png")
        
        # 2. Click Quick Demo / Load Live Sample Data (all 8 networks)
        print("3. Loading 8-network live dataset...")
        await page.click("#btn-bot-dropdown") # Close dropdown
        await page.wait_for_timeout(300)
        await page.click("#btn-load-demo")
        
        # Wait for processing and results
        print("4. Waiting for master table rendering...")
        await page.wait_for_selector("#master-table-body tr", timeout=15000)
        await page.wait_for_timeout(1500)
        
        # Search for "Pantech" in table search filter
        search_input = page.locator("#search-table")
        if await search_input.count() > 0:
            await search_input.fill("Pantech")
            await page.wait_for_timeout(800)
        
        # Capture screenshot of reconciled Flipkart / Pantech row
        await page.screenshot(path="/Users/faizan/.gemini/antigravity/brain/5048cda7-761c-4bb4-b7d7-88a56df02f96/pantech_reconciliation.png")
        print("Saved reconciliation screenshot: pantech_reconciliation.png")
        
        # Check rows
        rows = await page.locator("#master-table-body tr").all_inner_texts()
        print(f"Visible rows matching Pantech: {len(rows)}")
        for r in rows:
            print("  Row:", r.replace("\t", " | "))
                
        # 5. Open Advanced Analytics to verify Pantech breakdown
        analytics_btn = page.locator("#btn-advanced-analytics")
        if await analytics_btn.count() > 0:
            print("5. Opening Advanced Analytics...")
            await analytics_btn.click()
            await page.wait_for_timeout(1500)
            await page.screenshot(path="/Users/faizan/.gemini/antigravity/brain/5048cda7-761c-4bb4-b7d7-88a56df02f96/pantech_analytics.png")
            print("Saved analytics screenshot: pantech_analytics.png")
            
        await browser.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(run())
