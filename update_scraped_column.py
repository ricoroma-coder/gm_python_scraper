import asyncio
import sys
from playwright.async_api import async_playwright
from DatabaseManager import DatabaseManager
from getters import get_property


async def main():
    try: column = sys.argv[1]
    except: column = input('Inform the column you want to update: ')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        db = DatabaseManager()
        results = db.get(f"SELECT * FROM products WHERE {column}='' OR {column} IS NULL")

        for result in results:
            url = result.get('card_href')
            await page.goto(url)

            scraped = await get_property(page, column)

            print(f'updating {result.get('id')}: {column} = {scraped}')
            db.update(result.get('id'), {column: scraped})

        await browser.close()
        print('Closing browser...')


asyncio.run(main())
