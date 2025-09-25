import re


def parse_rating_count(value):
    if isinstance(value, int): return value

    if isinstance(value, str):
        if "k" in value:
            match = re.match(r"(\d+)(?:k\+)?", value)
            if match: return int(match.group(1)) * 1000

        match = re.search(r'\d{1,3}(?:,\d{3})*', value)
        if match: return int(match.group(0).replace(',', ''))

        try: return int(value)
        except (ValueError, TypeError): return None

    return None


def parse_price(value):
    match = re.search(r'(R\$|\$|€|£)\s?(\d{1,3}(?:[.,]\d{3})*)([.,]\d{2})?', value)
    if match: price = match.group(0)
    else: price = value

    return price


def parse_facilities(values):
    return ';'.join(values)
