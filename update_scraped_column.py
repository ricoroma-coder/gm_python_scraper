import asyncio
import sys
from playwright.async_api import async_playwright
from DatabaseManager import DatabaseManager
from getters import get_property


async def main():
    try:
        column = sys.argv[1]
        product_type = sys.argv[2] if len(sys.argv) > 2 else None
    except:
        column = input('Inform the column you want to update: ')
        product_type = input('Inform the product type you want to update (Empty for all): ')

    if product_type and product_type not in ['hotel', 'gastronomy', 'attraction', 'shopping', 'activity']:
        print('Product type not supported...')
        exit()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        db = DatabaseManager()

        sql = f"SELECT * FROM products WHERE ({column}='' OR {column} IS NULL)"
        params = []
        if product_type:
            sql += " AND product_type=?"
            params.append(product_type)

        results = db.get(sql, params)

        for result in results:
            url = result.get('card_href')

            try: await page.goto(url)
            except: pass

            scraped = await get_property(page, column)

            print(f'updating {result.get('id')}: {column} = {scraped}')
            db.update(result.get('id'), {column: scraped})

        await browser.close()
        print('Closing browser...')


asyncio.run(main())
