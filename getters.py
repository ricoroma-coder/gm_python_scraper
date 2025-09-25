import re
from parsers import parse_rating_count, parse_price


async def get_property(page, column):
    if column == 'name':
        return await get_name(page)

    if column == 'description':
        return await get_description(page)

    if column == 'link':
        return await get_link(page)

    if column == 'rating':
        return await get_rating(page)

    if column == 'rating_count':
        return await get_rating_count(page)

    if column == 'latitude':
        return await get_lat(page)

    if column == 'longitude':
        return await get_lon(page)

    if column == 'phone':
        return await get_phone(page)

    if column == 'address':
        return await get_address(page)

    if column == 'stars':
        return await get_stars(page)

    if column == 'images':
        return await get_images(page)

    if column == 'price':
        return await get_price(page)

    if column == 'facilities':
        return await get_facilities(page)

    print(f'Column {column} not supported...')
    exit()


async def get_name(page):
    try:
        name = await page.locator('h1.DUwDvf, h1').first.inner_text(timeout=1000)
    except: name = None

    return name


async def get_description(page):
    try:  # Description
        await page.locator('button[role="tab"] >> text=About').first.click()
        await page.wait_for_timeout(1000)
        desc_els = await page.locator('.P1LL5e').all()
        desc = "\n".join([await d.inner_text(timeout=1000) for d in desc_els if await d.inner_text(timeout=1000)])
        await page.locator('button[role="tab"] >> text=Overview').first.click()
        await page.wait_for_timeout(1000)
    except: desc = ""

    if desc == "":
        try:
            desc_els = await page.locator('.P1LL5e').all()
            desc = "\n".join([await d.inner_text(timeout=1000) for d in desc_els if await d.inner_text(timeout=1000)])
        except: desc = ""

    if desc == "":
        try: desc = await page.locator('.MmD1mb.fontBodyMedium').first.inner_text(timeout=1000)
        except: desc = ""

    return desc


async def get_link(page):
    try: link = await page.locator('a[data-item-id="authority"]').first.get_attribute('href', timeout=1000)
    except:
        try: link = await page.locator('.SlvSdc.co54Ed.e3R2ac').first.get_attribute('href', timeout=1000)
        except: link = None

    return link


async def get_rating(page):
    try:
        rating = await page.locator('.F7nice span[aria-hidden="true"]').first.inner_text(timeout=1000)
    except: rating = None

    return rating


async def get_rating_count(page):
    try: rating_count_text = await page.locator('span[aria-label*=" reviews"]').first.get_attribute('aria-label', timeout=1000)
    except: rating_count_text = None

    if rating_count_text is None:
        try: rating_count_text = await page.locator('.Bd93Zb .HHrUdb span').first.inner_text(timeout=1000)
        except: rating_count_text = None

    # if rating_count_text is None:
    #     try: rating_count_text = await page.locator('.UY7F9').first.inner_text(timeout=1000)
    #     except: rating_count_text = None

    rating_count = None
    if rating_count_text is not None:
        rating_count = parse_rating_count(rating_count_text)

    return rating_count


async def get_lat(page):
    try:
        lat = None
        match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', page.url)
        if match: lat = float(match.group(1))

        if lat is None:
            match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', page.url)
            if match: lat = float(match.group(1))
    except: lat = None

    return lat


async def get_lon(page):
    try:
        lon = None
        match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', page.url)
        if match: lon = float(match.group(2))

        if lon is None:
            match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', page.url)
            if match: lon = float(match.group(2))
    except: lon = None

    return lon


async def get_phone(page):
    try:
        phone = await page.locator('button[data-item-id*="phone"]').locator('.Io6YTe').first.inner_text(timeout=1000)
    except: phone = None

    return phone


async def get_address(page):
    try: address = await page.locator('button[data-item-id="address"]').locator('.Io6YTe').first.inner_text(timeout=1000)
    except: address = None

    return address


async def get_stars(page):
    try:
        stars_el = await page.locator('span', has_text='star hotel').first.text_content(timeout=1000)
        text = re.search(r'\d+', stars_el)
        if text: stars = text.group()
        else: stars = None
    except: stars = None

    return stars


async def get_images(page):
    try: img = await page.locator('img[src*="googleusercontent.com"]').first.get_attribute('src', timeout=1000)
    except: img = None

    return img


async def get_price(page):
    try: price = await page.locator('[aria-label*="$"], [aria-label*="R$"], [aria-label*="€"]').first.get_attribute('aria-label', timeout=1000)
    except:
        try: price = await page.locator('.drwWxc, .NFP9ae').first.inner_text(timeout=1000)
        except:
            try: price = await page.locator('.MNVeJb div').first.inner_text(timeout=1000)
            except: price = None

    if price: price = parse_price(price)

    return price


async def get_facilities(page):
    try:
        facility_els = await page.locator('.QoXOEc .CK16pd:not(:has(.G47vBd)) .gSamH').all()
        facilities = [await f.inner_text(timeout=1000) for f in facility_els]
    except: facilities = None

    return facilities
