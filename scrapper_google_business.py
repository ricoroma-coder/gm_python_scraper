import logging
import time
import json
import re
from DatabaseManager import DatabaseManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Suprime logs antes de qualquer importação do Selenium
import os
import sys
import warnings
from contextlib import redirect_stderr, redirect_stdout
import io

# Configurações de ambiente para suprimir logs
os.environ['WDM_LOG_LEVEL'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings("ignore")

# Configurações do ChromeDriver
chrome_options = Options()
chrome_options.add_argument("--headless")  # roda em background
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# Supressão completa de logs
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument("--disable-logging")
chrome_options.add_argument("--silent")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-background-timer-throttling")
chrome_options.add_argument("--disable-background-networking")
chrome_options.add_argument("--disable-backgrounding-occluded-windows")
chrome_options.add_argument("--disable-renderer-backgrounding")
chrome_options.add_argument("--disable-features=TranslateUI")
chrome_options.add_argument("--disable-ipc-flooding-protection")
chrome_options.add_argument("--disable-hang-monitor")
chrome_options.add_argument("--disable-client-side-phishing-detection")
chrome_options.add_argument("--disable-component-update")
chrome_options.add_argument("--disable-default-apps")
chrome_options.add_argument("--disable-domain-reliability")
chrome_options.add_argument("--disable-features=VizDisplayCompositor")
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--disable-features=VizServiceDisplayCompositor")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

# Experimental options para supressão
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
chrome_options.add_experimental_option("useAutomationExtension", False)

# Suprime completamente stdout e stderr durante a inicialização
null_output = io.StringIO()

# Ajuste o path para o seu chromedriver
with redirect_stderr(null_output), redirect_stdout(null_output):
    service = Service(executable_path="chromedriver.exe")
    service.creation_flags = 0x08000000  # CREATE_NO_WINDOW no Windows
    driver = webdriver.Chrome(service=service, options=chrome_options)

wait = WebDriverWait(driver, 15)

# Palavras-chave para cada tipo de produto
PRODUCT_KEYWORDS = {
    'hotel': [
        'accommodation', 'hotels', 'lodging', 'guesthouses', 'farm hotel', 'eco lodge', 'glamping',
        'camping', 'aparthotel', 'hotel boutique', 'all inclusive resort', 'spa resort', 'beach resort',
        'mountain lodge', 'cabins', 'villas', 'rural houses', 'tourist farms', 'haciendas', 'estancias',
        'refuges', 'accommodations', 'inns', 'hostels', 'auberges', 'chambres dhotes', 'ryokans', 'riads',
        'bed and breakfast', 'b&b', 'resort', 'pensions', 'hostels', 'rental apartments', 'chalets',
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


def extract_numbers_only(text):
    """Extrai apenas números de uma string"""
    if not text:
        return None
    numbers = re.findall(r'\d+', text)
    return ''.join(numbers) if numbers else None


def remove_parentheses(text):
    """Remove parênteses de uma string"""
    if not text:
        return None
    return text.replace('(', '').replace(')', '').replace(',', '').strip()


def collect_card_links(cards):
    """Coleta os links dos cards antes de qualquer manipulação"""
    card_data = []
    for i, card in enumerate(cards):
        try:
            # Extrai dados básicos do card lateral (que não mudam)
            link_element = card.find_element(By.CSS_SELECTOR, 'a.hfpxzc')
            href = link_element.get_attribute('href')

            # Nome do card lateral
            try:
                name = card.find_element(By.CSS_SELECTOR, '.qBF1Pd.fontHeadlineSmall').text
            except:
                name = None

            # Facilidades do card lateral
            try:
                facility_elements = card.find_elements(By.CSS_SELECTOR, '.Yfjtfe.dc6iWb')
                facilities = [elem.get_attribute('aria-label') for elem in facility_elements if
                              elem.get_attribute('aria-label')]
            except:
                facilities = []

            card_data.append({
                'index': i,
                'href': href,
                'name_preview': name,
                'facilities': facilities
            })

        except Exception as e:
            print(f"Error collecting data from card {i + 1}: {str(e)}")
            continue

    return card_data


def extract_details_from_modal(product_type, card_info):
    """Extrai detalhes do modal após clicar no card"""
    try:
        # Navega diretamente para o link do estabelecimento
        driver.get(card_info['href'])
        time.sleep(4)

        # Nome do business (do modal)
        try:
            name_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf, h1')))
            name = name_element.text
        except:
            name = card_info['name_preview']  # Fallback para nome do card

        # Rating (do modal)
        try:
            rating_element = driver.find_element(By.CSS_SELECTOR, '.F7nice span:first-child span[aria-hidden="true"]')
            rating = rating_element.text
        except:
            rating = None

        # Rating count (do modal - no elemento UY7F9)
        try:
            rating_count_element = driver.find_element(By.CSS_SELECTOR, '.UY7F9')
            rating_count_text = rating_count_element.text
            rating_count = remove_parentheses(rating_count_text)
        except:
            rating_count = None

        # Stars (apenas para hotéis)
        stars = None
        if product_type.lower() == 'hotel':
            try:
                stars_element = driver.find_element(By.CSS_SELECTOR, '.LBgpqf span.mgr77e span span:last-child')
                stars_text = stars_element.text
                stars = extract_numbers_only(stars_text)
            except:
                stars = None

        # Clica no botão "About" para acessar descrição e facilities
        try:
            about_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label*="About"]')))
            driver.execute_script("arguments[0].click();", about_button)
            time.sleep(3)  # Aguarda carregar o conteúdo do About
        except Exception as e:
            print(f"Could not click About button: {str(e)}")

        # Descrição (após clicar em About)
        description = ""
        try:
            # Múltiplos seletores para descrição (diferentes estruturas)
            description_selectors = [
                '.HeZRrf .P1LL5e',  # Para hotéis
                '.PbZDve p .HlvSq',  # Para outros tipos
                '.PbZDve .HlvSq',  # Variação para outros tipos
                '.HeZRrf',  # Fallback geral
                '.PbZDve p'  # Fallback para outros tipos
            ]

            for selector in description_selectors:
                try:
                    if selector == '.HeZRrf .P1LL5e':
                        # Para múltiplos elementos P1LL5e
                        description_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if description_elements:
                            desc_parts = [elem.text.strip() for elem in description_elements if elem.text.strip()]
                            description = ' '.join(desc_parts)
                            if description:
                                break
                    else:
                        # Para seletor único
                        description_element = driver.find_element(By.CSS_SELECTOR, selector)
                        description_text = description_element.text.strip()
                        if description_text and len(description_text) > 20:
                            description = description_text
                            break
                except:
                    continue

        except Exception as e:
            print(f"Could not extract description: {str(e)}")
            description = ""

        # Facilities (após clicar em About)
        facilities = []
        try:
            # Para hotéis: busca facilities na estrutura .QoXOEc
            if product_type.lower() == 'hotel':
                facility_elements = driver.find_elements(By.CSS_SELECTOR, '.QoXOEc .CK16pd')
                for facility_elem in facility_elements:
                    try:
                        # Verifica se não tem o símbolo G47vBd (que indica "não tem")
                        has_unavailable_symbol = facility_elem.find_elements(By.CSS_SELECTOR, '.G47vBd')
                        if not has_unavailable_symbol:  # Se não tem o símbolo de "não disponível"
                            facility_text_elem = facility_elem.find_element(By.CSS_SELECTOR, '.gSamH')
                            facility_text = facility_text_elem.text.strip()
                            if facility_text:
                                facilities.append(facility_text)
                    except:
                        continue

            # Para outros tipos: busca facilities nas seções categorizadas
            else:
                facility_sections = driver.find_elements(By.CSS_SELECTOR, '.iP2t7d')
                for section in facility_sections:
                    try:
                        facility_items = section.find_elements(By.CSS_SELECTOR, '.hpLkke .iNvpkb span[aria-label]')
                        for item in facility_items:
                            facility_text = item.get_attribute('aria-label')
                            if facility_text:
                                # Remove prefixos como "Has", "Good for", etc.
                                clean_facility = re.sub(r'^(Has |Good for |Accepts |Getting )', '', facility_text)
                                facilities.append(clean_facility)
                    except:
                        continue

        except Exception as e:
            print(f"Could not extract facilities: {str(e)}")
            facilities = []

        # Imagem principal
        try:
            img_element = driver.find_element(By.CSS_SELECTOR, 'img[src*="googleusercontent.com"]')
            img = img_element.get_attribute('src')
            images = [img] if img else []
        except:
            images = []

        # Link do site (no modal)
        try:
            link_element = driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
            link = link_element.get_attribute('href')
        except:
            link = None

        # Coordenadas (latitude/longitude)
        try:
            current_url = driver.current_url
            if '@' in current_url:
                coords_part = current_url.split('/@')[1].split(',')[:2]
                lat = coords_part[0]
                lon = coords_part[1]
            else:
                lat = None
                lon = None
        except:
            lat = None
            lon = None

        # Horários de funcionamento
        operating_hours = None
        try:
            hours_element = driver.find_element(By.CSS_SELECTOR, '.Io6YTe.fontBodyMedium.kR99db.fdkmkc')
            hours_text = hours_element.text
            if 'Check-in' in hours_text or 'Check-out' in hours_text:
                operating_hours = hours_text
        except:
            pass

        # Telefone
        phone = None
        try:
            phone_element = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="phone"] .Io6YTe')
            phone = phone_element.text
        except:
            pass

        # Endereço
        address = None
        try:
            address_element = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"] .Io6YTe')
            address = address_element.text
        except:
            pass

        # Preço (específico por tipo de produto)
        price = None
        try:
            if product_type.lower() in ['hotel', 'attraction']:
                # Para hotéis e atrações: busca no botão com preço e período
                try:
                    price_button = driver.find_element(By.CSS_SELECTOR,
                                                       'button[aria-label*="R$"], button[aria-label*="$"], button[aria-label*="€"]')
                    price_aria_label = price_button.get_attribute('aria-label')
                    # Extrai o preço do aria-label
                    price_match = re.search(r'(R\$\d+|€\d+|\$\d+)', price_aria_label)
                    if price_match:
                        price = price_match.group(1)
                except:
                    # Fallback: busca diretamente no span com classe do preço
                    try:
                        price_element = driver.find_element(By.CSS_SELECTOR,
                                                            '.fontTitleLarge.Cbys4b, .dkgw2 .fontTitleLarge')
                        price = price_element.text
                    except:
                        pass

            elif product_type.lower() == 'gastronomy':
                # Para gastronomia: busca na seção de faixa de preço
                try:
                    price_element = driver.find_element(By.CSS_SELECTOR, '.MNVeJb.eXOdV.eF9eN.PnPrlf')
                    price_text = price_element.text
                    # Extrai a faixa de preço (ex: €20–40 per person)
                    price_match = re.search(r'(€\d+–\d+|R\$\d+–\d+|\$\d+–\d+|\+?[€R\$]\d+)', price_text)
                    if price_match:
                        price = price_match.group(1)
                except:
                    pass

            elif product_type.lower() == 'activity':
                # Para atividades: busca nos cards de ofertas
                try:
                    price_elements = driver.find_elements(By.CSS_SELECTOR, '.apD3Md, .W0by1 .apD3Md')
                    if price_elements:
                        # Pega o primeiro preço encontrado
                        price = price_elements[0].text
                except:
                    pass

            # Se não encontrou preço específico, busca genérica por padrões monetários
            if not price:
                # Busca genérica por elementos que contenham símbolos monetários
                monetary_patterns = [
                    r'R\$\s*\d+(?:[.,]\d+)*',
                    r'€\s*\d+(?:[.,]\d+)*',
                    r'\$\s*\d+(?:[.,]\d+)*',
                    r'\d+\s*€',
                    r'\d+\s*R\$',
                    r'\d+\s*\$'
                ]

                page_text = driver.find_element(By.TAG_NAME, 'body').text
                for pattern in monetary_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        price = matches[0]
                        break

        except Exception as e:
            print(f"Could not extract price: {str(e)}")
            price = None

        # Monta o resultado
        result = {
            "name": name,
            "rating": rating,
            "rating_count": rating_count,
            "description": description,
            "images": images,
            "link": link,
            "facilities": facilities,  # Usa as facilidades extraídas do About
            "lat": lat,
            "lon": lon,
            "phone": phone,
            "address": address,
            "price": price,  # Novo campo para preço
            "operating_hours": operating_hours
        }

        # Adiciona stars apenas para hotéis
        if product_type.lower() == 'hotel':
            result["stars"] = stars

        return result

    except Exception as e:
        print(f"Error extracting details from modal: {str(e)}")
        return None


def scrape_google_maps_with_keyword(product_type, location, search_term, max_results=10):
    """Faz o scraping para um termo de busca específico"""
    query = f"{search_term} {location}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}/?hl=en&gl=us"
    driver.get(url)

    # Espera carregar a lista de resultados
    time.sleep(5)

    # Scroll na lista lateral para carregar mais resultados com controle melhorado
    try:
        results_panel = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')

        previous_count = 0
        stagnant_iterations = 0
        max_stagnant = 3  # Máximo de iterações sem novos resultados

        while True:
            # Scroll até o final da lista
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
            time.sleep(3)  # Tempo maior para o lazy loading

            # Conta quantos cards existem agora
            current_cards = driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')
            current_count = len(current_cards)

            print(f"Current cards loaded: {current_count}")

            # Se chegou ao limite desejado, para
            if current_count >= max_results:
                print(f"Reached desired limit of {max_results} results")
                break

            # Se não carregou novos cards, incrementa contador de estagnação
            if current_count == previous_count:
                stagnant_iterations += 1
                if stagnant_iterations >= max_stagnant:
                    print(f"No more results loading. Final count: {current_count}")
                    break
                # Tenta scroll mais agressivo quando não carrega
                for _ in range(3):
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
                    time.sleep(1)
            else:
                stagnant_iterations = 0  # Reset contador se carregou novos

            previous_count = current_count

            # Scroll adicional para garantir que o lazy loading seja ativado
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight - 100", results_panel)
            time.sleep(1)
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
            time.sleep(2)

    except Exception as e:
        print(f"Error during scrolling: {str(e)}")

    # FASE 1: Coleta todos os links e dados básicos dos cards iniciais
    print("Collecting initial card links and basic data...")
    cards = driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')
    card_data_list = collect_card_links(cards)

    # FASE 2: Processa os cards até encontrar o limite de novos registros
    results = []
    db = DatabaseManager()
    processed_count = 0  # Contador para novos registros processados
    card_index = 0  # Índice atual na lista de cards

    while processed_count < max_results:
        # Se chegou ao fim da lista de cards, carrega mais
        if card_index >= len(card_data_list):
            try:
                # Volta para a página de busca original para carregar mais
                driver.get(url)
                time.sleep(3)

                # Scroll mais cards
                results_panel = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')

                # Scroll mais agressivo para carregar ainda mais resultados
                scroll_attempts = 10  # Aumenta tentativas de scroll
                for scroll in range(scroll_attempts):
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
                    time.sleep(2)

                    # Verifica se carregou novos cards
                    current_cards = driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')
                    if len(current_cards) > len(card_data_list):
                        break

                # Coleta novos cards
                new_cards = driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')
                new_card_data = collect_card_links(new_cards)

                # Se não encontrou novos cards suficientes, para
                if len(new_card_data) <= len(card_data_list):
                    print("No more cards available to load")
                    break

                card_data_list = new_card_data
                print(f"Loaded more cards. Total available: {len(card_data_list)}")

            except Exception as e:
                print(f"Error loading more cards: {str(e)}")
                print("Continuing with available cards...")
                # Se não conseguir carregar mais, continua com os cards disponíveis
                if card_index >= len(card_data_list):
                    break

        # Se ainda não tem cards suficientes, para
        if card_index >= len(card_data_list):
            print("Reached end of available cards")
            break

        card_info = card_data_list[card_index]
        print(
            f"Processing item {card_index + 1}/{len(card_data_list)} (New records found: {processed_count}/{max_results})...")

        result = extract_details_from_modal(product_type, card_info)
        if result:
            # Verifica se já existe no banco com mesmo nome, latitude, longitude e product_type
            existing_record = None
            if result.get('name') and result.get('lat') and result.get('lon'):
                existing_records = db.get(
                    "SELECT * FROM products WHERE name = ? AND latitude = ? AND longitude = ? AND product_type = ?",
                    [result.get('name'), float(result.get('lat')), float(result.get('lon')), product_type]
                )
                if existing_records:
                    existing_record = existing_records[0]

            if existing_record:
                # Se existe no banco, atualiza com os dados do scraper
                print(f"Found existing record with ID: {existing_record['id']} - updating with new data")

                # Prepara os dados para atualização no banco
                update_data = {
                    'name': result.get('name'),
                    'description': result.get('description'),
                    'link': result.get('link'),
                    'images': ';'.join(result.get('images', [])) if result.get('images') else None,
                    'rating': float(result.get('rating', 0)) if result.get('rating') else None,
                    'rating_count': int(result.get('rating_count', 0)) if result.get('rating_count') else None,
                    'facilities': ';'.join(result.get('facilities', [])) if result.get('facilities') else None,
                    'latitude': float(result.get('lat')) if result.get('lat') else None,
                    'longitude': float(result.get('lon')) if result.get('lon') else None,
                    'phone': result.get('phone'),
                    'address': result.get('address'),
                    'price': result.get('price')
                }

                # Adiciona stars apenas para hotéis
                if product_type.lower() == 'hotel':
                    update_data['stars'] = int(result.get('stars')) if result.get('stars') else None

                # Atualiza o registro no banco
                db.update(existing_record['id'], update_data)

                # Converte os dados do scraper para o formato JSON (ao invés dos dados do banco)
                json_result = {
                    "name": result.get('name'),
                    "rating": result.get('rating'),
                    "rating_count": result.get('rating_count'),
                    "description": result.get('description'),
                    "images": result.get('images', []),
                    "link": result.get('link'),
                    "facilities": result.get('facilities', []),
                    "lat": result.get('lat'),
                    "lon": result.get('lon'),
                    "phone": result.get('phone'),
                    "address": result.get('address'),
                    "price": result.get('price'),
                    "operating_hours": result.get('operating_hours'),
                    "db_id": existing_record['id']
                }

                # Adiciona stars apenas para hotéis
                if product_type.lower() == 'hotel':
                    json_result["stars"] = result.get('stars')

                results.append(json_result)
                # NÃO incrementa processed_count pois registro existente não conta no limite

            else:
                # Se não existe, processa normalmente e insere no banco
                # Prepara os dados para inserção no banco
                db_data = {
                    'product_type': product_type,
                    'name': result.get('name'),
                    'description': result.get('description'),
                    'link': result.get('link'),
                    'images': ';'.join(result.get('images', [])) if result.get('images') else None,
                    'rating': float(result.get('rating', 0)) if result.get('rating') else None,
                    'rating_count': int(result.get('rating_count', 0)) if result.get('rating_count') else None,
                    'facilities': ';'.join(result.get('facilities', [])) if result.get('facilities') else None,
                    'latitude': float(result.get('lat')) if result.get('lat') else None,
                    'longitude': float(result.get('lon')) if result.get('lon') else None,
                    'phone': result.get('phone'),
                    'address': result.get('address'),
                    'price': result.get('price')
                }

                # Adiciona stars apenas para hotéis
                if product_type.lower() == 'hotel':
                    db_data['stars'] = int(result.get('stars')) if result.get('stars') else None

                # Insere no banco de dados
                record_id = db.create(db_data)
                if record_id:
                    result['db_id'] = record_id
                    print(f"New record saved with ID: {record_id}")

                results.append(result)
                processed_count += 1  # Incrementa contador apenas para novos registros
                print(f"Progress: {processed_count}/{max_results} new records processed")

        card_index += 1
        # Pequena pausa entre requisições
        time.sleep(1)

    return results


def scrape_google_maps(product_type, location, max_results=10):
    """Função principal que executa o scraping com o product_type e suas palavras-chave"""
    all_results = []

    # Lista de termos de busca: product_type + suas palavras-chave
    search_terms = [product_type]  # Começa com o próprio product_type

    # Adiciona as palavras-chave se existirem para o product_type
    if product_type in PRODUCT_KEYWORDS:
        search_terms.extend(PRODUCT_KEYWORDS[product_type])

    print(f"Starting scraping for product_type: {product_type}")
    print(f"Search terms to process: {search_terms}")
    print(f"Total searches to perform: {len(search_terms)}")
    print("=" * 60)

    # Executa o scraping para cada termo de busca
    for i, search_term in enumerate(search_terms, 1):
        print(f"\n[SEARCH {i}/{len(search_terms)}] Processing search term: '{search_term}'")
        print("-" * 40)

        try:
            results = scrape_google_maps_with_keyword(product_type, location, search_term, max_results)
            all_results.extend(results)

            # Conta novos registros nesta iteração
            new_records_in_iteration = sum(1 for item in results if 'db_id' in item and
                                           not any(existing.get('db_id') == item['db_id'] and existing != item
                                                   for existing in all_results[:-len(results)]))
            existing_records_in_iteration = len(results) - new_records_in_iteration

            print(f"Search '{search_term}' completed:")
            print(f"- New records: {new_records_in_iteration}")
            print(f"- Existing records: {existing_records_in_iteration}")
            print(f"- Total results: {len(results)}")

        except Exception as e:
            print(f"Error processing search term '{search_term}': {str(e)}")
            continue

    print("\n" + "=" * 60)
    print("ALL SEARCHES COMPLETED")
    print(f"Total results collected: {len(all_results)}")

    return all_results


if __name__ == "__main__":
    allowed_types = ['hotel', 'gastronomy', 'attraction', 'shopping', 'activity']
    product_type = input("Enter product type (hotel, gastronomy, attraction, shopping or activity.): ")

    if product_type not in allowed_types:
        logging.error("Not allowed product type")
        driver.quit()
        exit(1)

    location = input("Enter location (city/state/country): ")
    max_results = int(input("Enter max results per search term (default 10): ") or 10)

    try:
        data = scrape_google_maps(product_type, location, max_results)
        file_name = f"{product_type}.json"

        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"\nSearch completed! {len(data)} total results saved to {file_name} and database")
        print(f"Results breakdown:")

        # Conta registros novos vs existentes no total
        unique_db_ids = set()
        new_records_count = 0
        existing_records_count = 0

        for item in data:
            if 'db_id' in item:
                if item['db_id'] not in unique_db_ids:
                    # Verifica se este é um registro novo ou existente baseado em outros critérios
                    # Como não temos essa informação direta, assumimos que registros únicos por db_id são válidos
                    unique_db_ids.add(item['db_id'])

        # Simplifica a contagem: todos os resultados são válidos
        print(f"- Total unique results: {len(data)}")

        # Exemplo de uso das funções do banco de dados
        db = DatabaseManager()

        # Consulta todos os registros
        all_products = db.get("SELECT * FROM products")
        print(f"Total products in database: {len(all_products)}")

        # Consulta por tipo de produto
        current_type_products = db.get("SELECT * FROM products WHERE product_type = ?", [product_type])
        print(f"Products of type '{product_type}' in database: {len(current_type_products)}")

        # Mostra estatísticas por palavra-chave utilizada
        search_terms = [product_type]
        if product_type in PRODUCT_KEYWORDS:
            search_terms.extend(PRODUCT_KEYWORDS[product_type])

        print(f"\nKeywords used for '{product_type}':")
        for term in search_terms:
            print(f"- {term}")

    except Exception as e:
        print(f"Error during execution: {str(e)}")

    finally:
        driver.quit()