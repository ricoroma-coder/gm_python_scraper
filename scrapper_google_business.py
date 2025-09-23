import asyncio
import re
import sys
import json
from DatabaseManager import DatabaseManager
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, LLMConfig, LLMExtractionStrategy, CacheMode

# Schema Crawl4AI / LLM
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "latitude": {"type": "string"},
        "longitude": {"type": "string"},
        "description": {"type": "string"},
        "rating": {"type": "string"},
        "rating_count": {"type": "string"},
        "address": {"type": "string"},
        "phone": {"type": "string"},
        "images": {"type": "string"},
        "price": {"type": "string"}
    }
}

llm_config = LLMConfig(provider="ollama/gemma:2b", api_token=None)
llm_strategy = LLMExtractionStrategy(
    llm_config=llm_config,
    schema=schema,
    extraction_type="schema",
    instruction="""
Extract only the information from the main business panel displayed on Google Maps after clicking the sidebar result card.
Ignore any items in lists such as 'Vacation rentals nearby', 'Similar places', 'Nearby hotels', or recommended cards.
The company/hotel/business name should be from the MAIN highlight panel, not from other cards.
If there is a main title element (e.g. <h1> or class 'fontHeadlineLarge'), use it!
Return only the fields for the business currently viewed: name (h1.DUwDvf), description(button[role="tab"] >> text=About .P1LL5e or .P1LL5e or .MmD1mb.fontBodyMedium), rating (.F7nice span[aria-hidden="true"]), rating_count (.UY7F9), address (button[data-item-id="address"] .Io6YTe), phone (button[data-item-id*="phone"] .Io6YTe), images (img[src*="googleusercontent.com"]), price ([aria-label*="$"], [aria-label*="R$"], [aria-label*="€"] or .drwWxc, .NFP9ae or .MNVeJb div).
Never extract names of apartments, vacation homes, or suggestions of other properties—only from the focused panel.
"""
)
crawl_config = CrawlerRunConfig(extraction_strategy=llm_strategy, cache_mode=CacheMode.BYPASS)
browser_config = BrowserConfig(headless=True)


async def extrai_card_llm(html_card):
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url="raw://" + html_card, config=crawl_config)
        if result.success:
            return json.loads(result.extracted_content)
        else:
            print("Erro na extração IA:", result.error_message)
            return {}


def parse_rating_count(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = re.sub(r"[\(\),\. ]", "", value)
        if "k" in value:
            match = re.match(r"(\d+)(?:k\+)?", value)
            if match:
                return int(match.group(1)) * 1000
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    return None


async def bypass_consent(page):
    try:
        await page.click("button[aria-label^='Accept a'], button[aria-label^='Aceitar t']", timeout=3000)
    except PlaywrightTimeout:
        pass


# NOVA COLETA: retorna os próprios elementos dos cards (para clicar)
async def collect_card_elements(page):
    return await page.locator('div.Nv2PK.THOPZb.CpccDe').all()


# EXTRAI PAINEL DE DETALHES APÓS CLIQUE NO CARD SIDEBAR
async def extract_details_from_modal(page, card):
    await card.click()
    await page.wait_for_timeout(1200)
    # await page.wait_for_selector('.Hu9e2e .aIFcqe h1, .Hu9e2e .aIFcqe .fontHeadlineLarge, .Hu9e2e .aIFcqe .DUwDvf', timeout=5000)
    try:
        panel_html = await page.locator('.Hu9e2e .aIFcqe').evaluate('el => el.outerHTML')
    except Exception as e:
        print(f"Falha ao capturar HTML do painel/modal: {e}")
        return {}

    # henrique
    print(panel_html)
    print('')

    extracted = await extrai_card_llm(panel_html)

    #henrique
    print(extracted)
    exit()

    images = extracted.get('images')
    if isinstance(images, str): images = [images]
    res = {
        "name": extracted.get('name', ''),
        "rating": extracted.get('rating'),
        "rating_count": extracted.get('rating_count'),
        "description": extracted.get('description', ''),
        "images": images if images else [],
        "lat": extracted.get('latitude'),
        "lon": extracted.get('longitude'),
        "phone": extracted.get('phone', None),
        "address": extracted.get('address', None),
        "price": extracted.get('price', None),
    }
    return res


async def process_search_term(page, db, product_type, location, search_term, max_results=None):
    query = f"{search_term} {location}".replace(" ", "+")
    url = f"https://www.google.com/maps/search/{query}/?hl=en&gl=us"
    await page.goto(url)
    await bypass_consent(page)
    await page.wait_for_selector('div[role="feed"]', timeout=8000)
    await page.wait_for_timeout(1200)
    # Scroll para carregar mais cards
    feed = page.locator('div[role="feed"]')
    stagnation = 0
    prev_count = 0
    for _ in range(25):
        await feed.evaluate('el => {el.scrollTop = el.scrollHeight;}')
        await page.wait_for_timeout(1000)
        cards_now = await page.locator('div.Nv2PK.THOPZb.CpccDe').count()
        if cards_now == prev_count:
            stagnation += 1
            if stagnation >= 2: break
        else:
            stagnation = 0
        prev_count = cards_now
        if max_results and cards_now >= max_results:
            break

    cards = await collect_card_elements(page)
    total_to_process = min(max_results, len(cards)) if max_results else len(cards)
    for card in cards[:total_to_process]:
        try:
            entry = await extract_details_from_modal(page, card)
            db_data = {
                'product_type': product_type,
                'name': entry.get('name'),
                'description': entry.get('description'),
                'images': ';'.join(entry.get('images', [])),
                'rating': float(entry.get('rating') or 0),
                'rating_count': entry.get('rating_count', 0),
                'latitude': entry.get('lat'),
                'longitude': entry.get('lon'),
                'phone': entry.get('phone'),
                'address': entry.get('address'),
                'price': entry.get('price'),
            }
            existing = db.get("SELECT * FROM products WHERE name=? AND latitude=? AND longitude=? AND product_type=?",
                              (db_data["name"], db_data["latitude"], db_data["longitude"], db_data["product_type"]))
            if existing:
                print(f"Already exists: {db_data['name']}")
                continue
            else:
                db.create(db_data)
            print(f'Business saved: {entry.get("name")}')
        except Exception as e:
            print(f'Failed to process card: {e}')


async def main():
    allowed_types = ['hotel', 'gastronomy', 'attraction', 'shopping', 'activity']

    def get_param(idx, prompt):
        try:
            value = sys.argv[idx]
            if not value.strip(): raise ValueError
            return value
        except (IndexError, ValueError):
            return input(prompt)

    product_type = get_param(1, "Enter product type (hotel, gastronomy, attraction, shopping, activity): ")
    if product_type not in allowed_types:
        print("Invalid product type")
        exit(1)
    location = get_param(2, "Enter location (city/state/country): ")
    max_results = None
    db = DatabaseManager()
    search_terms = [product_type]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        print(f"Total search terms: {len(search_terms)}")
        for search_term in search_terms:
            print(f"Processing: {search_term}")
            await process_search_term(page, db, product_type, location, search_term, max_results)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
