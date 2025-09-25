import asyncio
import sys
import time
from DatabaseManager import DatabaseManager
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from getters import get_property


PRODUCT_KEYWORDS = {
    'hotel': [
        'accommodation', 'lodging', 'guesthouses', 'farm hotel', 'eco lodge', 'glamping',
        'camping', 'aparthotel', 'hotel boutique', 'all inclusive resort', 'spa resort', 'beach resort',
        'mountain lodge', 'cabins', 'villas', 'rural houses', 'tourist farms', 'haciendas', 'estancias',
        'refuges', 'inns', 'hostels', 'auberges', 'chambres dhotes', 'ryokans', 'riads',
        'bed and breakfast', 'resort', 'pensions', 'rental apartments', 'chalets',
        'vacation homes', 'pet friendly hotel', 'hotel with breakfast'
    ],
    'gastronomy': [
        'restaurants', 'bars', 'cafes', 'street food', 'bistros', 'pizzerias', 'steakhouses', 'snack bars',
        'bakeries', 'pastry shops', 'ice cream shops', 'pubs', 'taverns', 'canteens', 'trattorias',
        'brasseries', 'gastropubs', 'food trucks', 'gastronomic markets', 'local cuisine', 'typical food',
        'regional dishes', 'international cuisine', 'italian food', 'japanese cuisine', 'mexican food',
        'french cuisine', 'chinese food', 'arabic cuisine', 'vegetarian food', 'vegan food',
        'organic cuisine', 'fast food', 'slow food', 'wine tasting', 'beer tasting', 'cooking classes',
        'food tours', 'dinner with show', 'restaurants with view', 'gastronomic experiences', 'chefs table',
        'tasting menu', 'brunch', 'happy hour', 'dining', 'cuisine', 'diner', 'wine bar'
    ],
    'attraction': [
        'tourist attractions', 'museums', 'national parks', 'historical monuments', 'beaches', 'viewpoints',
        'historic centers', 'churches', 'cathedrals', 'castles', 'palaces', 'archaeological ruins',
        'historic sites', 'unesco world heritage', 'landmarks', 'waterfalls', 'ecological trails',
        'natural reserves', 'state parks', 'botanical gardens', 'zoos', 'aquariums', 'caves', 'canyons',
        'volcanoes', 'glaciers', 'deserts', 'forests', 'lakes', 'rivers', 'art museums', 'galleries',
        'theaters', 'operas', 'cultural centers', 'historic libraries', 'traditional markets',
        'historic neighborhoods', 'colonial architecture', 'street art', 'murals', 'public sculptures',
        'sightseeing', 'must see places', 'monument', 'museum', 'natural park', 'gallery', 'temple',
        'heritage', 'historical site', 'square', 'park', 'palace'
    ],
    'shopping': [
        'shopping centers', 'local markets', 'craft stores', 'luxury boutiques', 'outlets',
        'commercial galleries', 'commercial streets', 'craft fairs', 'flea markets', 'antique shops',
        'souvenir shops', 'duty free', 'tax free shopping', 'local crafts', 'typical products',
        'souvenirs', 'jewelry', 'traditional clothing', 'ceramics', 'fabrics', 'spices', 'local wines',
        'regional sweets', 'folk art', 'musical instruments', 'personal shopping', 'shopping tours',
        'discount shopping', 'night markets', 'street fairs', 'bazaars', 'vintage stores',
        'thrift stores', 'concept stores', 'flagship stores', 'markets', 'boutiques', 'stores',
        'shops', 'market', 'shopping center'
    ],
    'activity': [
        'water sports', 'boat trips', 'trails', 'horseback riding', 'extreme sports', 'diving',
        'snorkeling', 'surf', 'windsurf', 'kitesurf', 'rafting', 'canoeing', 'stand up paddle',
        'jet ski', 'parasailing', 'bungee jump', 'rappelling', 'climbing', 'zipline', 'paragliding',
        'hang gliding', 'mountaineering', 'cycling', 'mountain bike', 'city tours', 'walking tours',
        'guided tours', 'gastronomic tours', 'wine tours', 'photography tours', 'cooking classes',
        'craft workshops', 'winery visits', 'tastings', 'night tours', 'ghost tours', 'historic tours',
        'theme parks', 'water parks', 'interactive zoos', 'educational farms', 'train rides',
        'carriage rides', 'picnics', 'children activities', 'family activities', 'kid friendly tours',
        'activities', 'things to do', 'excursions', 'tours', 'adventures', 'experiences', 'tour',
        'outdoor', 'nature', 'class', 'tasting', 'workshop'
    ]
}


async def bypass_consent(page):
    try:
        await page.click("button[aria-label^='Accept a'], button[aria-label^='Aceitar t']", timeout=3000)
    except PlaywrightTimeout:
        pass


async def collect_card_links(page):
    # Collect business card links from the search results sidebar
    cards = await page.locator('div.Nv2PK.THOPZb.CpccDe').all()
    card_data = []
    for card in cards:
        link_el = card.locator('a.hfpxzc')
        href = await link_el.get_attribute('href')

        try: name = await card.locator('.qBF1Pd.fontHeadlineSmall').inner_text(timeout=1000)
        except: name = None

        facilities = []
        for el in await card.locator('.Yfjtfe.dc6iWb[aria-label]').all():
            fac = await el.get_attribute('aria-label')
            if fac: facilities.append(fac)
        card_data.append({'href': href, 'name_preview': name, 'facilities': facilities})
    return card_data


async def extract_details_from_modal(page, card, product_type):
    await page.goto(card['href'])
    await page.wait_for_timeout(1300)

    name = await get_property(page, 'name')
    if name is None: name = card['name_preview']

    rating = await get_property(page, 'rating')

    rating_count = await get_property(page, 'rating_count')

    lat, lon = await get_property(page, 'latitude'), await get_property(page, 'longitude')

    phone = await get_property(page, 'phone')

    address = await get_property(page, 'address')

    stars = None
    if product_type == 'hotel': stars = await get_property(page, 'stars')

    img = await get_property(page, 'images')

    link = await get_property(page, 'link')

    price = await get_property(page, 'price')

    desc = await get_property(page, 'description')

    facilities = await get_property(page, 'facilities')
    if facilities is None: facilities = card.get('facilities', [])

    res = {
        "name": name,
        "rating": rating,
        "rating_count": rating_count,
        "description": desc,
        "images": img,
        "link": link,
        "facilities": facilities,
        "lat": lat,
        "lon": lon,
        "phone": phone,
        "address": address,
        "price": price,
        "stars": stars
    }

    return res


async def process_search_term(page, db, product_type, location, search_term, max_results=None):
    query = f"{search_term} {location}".replace(" ", "+")
    url = f"https://www.google.com/maps/search/{query}/?hl=en&gl=us"
    await page.goto(url)
    await bypass_consent(page)
    await page.wait_for_selector('div[role="feed"]', timeout=8000)
    await page.wait_for_timeout(1200)

    # Scroll to load more
    feed = page.locator('div[role="feed"]')
    stagnation = 0
    prev_count = 0
    max_attempts = 100

    print('Collecting cards...')

    for _ in range(max_attempts):
        await feed.evaluate('el => {el.scrollTop = el.scrollHeight;}')
        await page.wait_for_timeout(3000)
        cards_now = await page.locator('div.Nv2PK.THOPZb.CpccDe').count()
        if cards_now == prev_count:
            stagnation += 1
            if stagnation >= 3: break
        else:
            stagnation = 0

        prev_count = cards_now
        if max_results and cards_now >= max_results:
            break

    card_links = await collect_card_links(page)
    print(f'Cards collected: {len(card_links)}')

    total_to_process = min(max_results, len(card_links)) if max_results else len(card_links)

    card_times = []
    start_total = time.time()
    new_for_term = 0
    updated_for_term = 0

    for i, card in enumerate(card_links[:total_to_process], 1):
        card_start = time.time()
        try:
            entry = await extract_details_from_modal(page, card, product_type)
            db_data = {
                'product_type': product_type,
                'name': entry.get('name'),
                'description': entry.get('description'),
                'link': entry.get('link'),
                'images': entry.get('images', None),
                'rating': float(entry.get('rating') or 0),
                'rating_count': entry.get('rating_count', 0),
                'facilities': entry.get('facilities', None),
                'latitude': entry.get('lat'),
                'longitude': entry.get('lon'),
                'phone': entry.get('phone'),
                'address': entry.get('address'),
                'price': entry.get('price'),
                'card_href': card['href']
            }

            if product_type.lower() == 'hotel' and 'stars' in entry:
                db_data['stars'] = int(entry['stars']) if entry.get('stars') else None

            existing = db.get(
                "SELECT * FROM products WHERE name=? AND latitude=? AND longitude=? AND product_type=?",
                (db_data["name"], db_data["latitude"], db_data["longitude"], db_data["product_type"])
            )
            if len(existing) > 0:
                data = existing[0]
                db.update(data['id'], db_data)
                updated_for_term += 1
                print(f"Already exists: {db_data['name']}")
            else:
                db.create(db_data)
                new_for_term += 1
                print(f"Business saved: {entry.get('name')}")
        except Exception as e:
            print(f'Failed to process card: {e}')

        card_end = time.time()
        card_time = card_end - card_start
        card_times.append(card_time)
        print(f"Time spent for card {i}: {card_time:.2f} seconds")

    end_total = time.time()
    total_time = end_total - start_total
    if card_times:
        avg_card_time = sum(card_times) / len(card_times)
        print(f"\nAverage time per card: {avg_card_time:.2f} seconds")

    print(f"Time spent for all cards: {total_time:.2f} seconds")

    print(f"New records for term '{search_term}': {new_for_term}")
    print(f"Updated records for term '{search_term}': {updated_for_term}")
    return new_for_term, updated_for_term


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
    max_results = None # You may parametrize it
    db = DatabaseManager()
    search_terms = [product_type] + PRODUCT_KEYWORDS.get(product_type, [])

    new_total = 0
    updated_total = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        print(f"Total search terms: {len(search_terms)}")
        for search_term in search_terms:
            print(f"\nProcessing: {search_term}")
            new_for_term, updated_for_term = await process_search_term(page, db, product_type, location, search_term, max_results)
            new_total += new_for_term
            updated_total += updated_for_term
        await browser.close()

    print(f"\nTotal new records: {new_total}")
    print(f"Total updated records: {updated_total}")


if __name__ == "__main__":
    asyncio.run(main())
