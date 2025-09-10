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
from selenium.common.exceptions import WebDriverException, InvalidSessionIdException, NoSuchElementException, \
    TimeoutException

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

# Variáveis globais para gerenciar driver
driver = None
wait = None

# Variáveis para controle de performance
DRIVER_CREATION_TIME = 0
LAST_DRIVER_CHECK = 0
DRIVER_CHECK_INTERVAL = 30

# Variáveis para estatísticas de tempo
total_processing_time = 0
total_items_processed = 0
item_times = []

# Cache para evitar processamento duplicado
processed_urls_cache = set()
CACHE_ENABLED = True


def create_chrome_driver():
    """Cria uma nova instância do Chrome driver otimizada"""
    chrome_options = Options()

    # Opções essenciais e compatíveis
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")

    # Opções para melhor estabilidade e performance
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript-harmony")
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")

    # Novas opções para melhor performance
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-crash-reporter")
    chrome_options.add_argument("--disable-oopr-debug-crash-dump")
    chrome_options.add_argument("--no-crash-upload")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-component-update")
    chrome_options.add_argument("--disable-default-apps")

    # User agent para evitar detecção
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Adiciona prefs para desabilitar notificações e popups
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "popups": 2,
            "media_stream": 2,
        },
        "profile.managed_default_content_settings.images": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Configuração do service
    service = Service(executable_path="chromedriver.exe")

    # Remove a flag problemática no Windows
    try:
        if os.name == 'nt':
            service.creation_flags = 0x08000000
    except:
        pass

    # Cria o driver com tratamento de erros melhorado
    try:
        null_output = io.StringIO()
        with redirect_stderr(null_output), redirect_stdout(null_output):
            new_driver = webdriver.Chrome(service=service, options=chrome_options)

        # Configurações adicionais após criação
        new_driver.set_page_load_timeout(15)
        new_driver.implicitly_wait(3)

        print("Chrome driver created successfully")
        return new_driver

    except Exception as e:
        print(f"Error creating Chrome driver: {str(e)}")
        print("Trying fallback configuration...")

        # Configuração fallback mais simples
        simple_options = Options()
        simple_options.add_argument("--headless")
        simple_options.add_argument("--no-sandbox")
        simple_options.add_argument("--disable-dev-shm-usage")
        simple_options.add_argument("--disable-gpu")

        try:
            fallback_driver = webdriver.Chrome(service=service, options=simple_options)
            fallback_driver.set_page_load_timeout(15)
            fallback_driver.implicitly_wait(3)
            print("Fallback Chrome driver created successfully")
            return fallback_driver
        except Exception as fallback_error:
            print(f"Fallback also failed: {str(fallback_error)}")
            raise fallback_error


def ensure_driver_alive():
    """Garante que o driver está ativo, recriando se necessário"""
    global driver, wait, LAST_DRIVER_CHECK, DRIVER_CREATION_TIME

    current_time = time.time()

    if current_time - LAST_DRIVER_CHECK < DRIVER_CHECK_INTERVAL:
        return True

    LAST_DRIVER_CHECK = current_time

    try:
        driver.title
        return True
    except (InvalidSessionIdException, WebDriverException, AttributeError):
        print("Driver session lost, creating new driver...")
        creation_start = time.time()

        try:
            if driver:
                driver.quit()
        except:
            pass

        driver = create_chrome_driver()
        wait = WebDriverWait(driver, 8)

        DRIVER_CREATION_TIME = time.time() - creation_start
        print(f"New driver created in {DRIVER_CREATION_TIME:.2f}s")
        return True
    except Exception as e:
        print(f"Error checking driver status: {str(e)}")
        return False


def safe_driver_action(action_func, *args, max_retries=2, **kwargs):
    """Executa uma ação do driver with retry em caso de erro de sessão"""
    global driver, wait

    for attempt in range(max_retries):
        try:
            if not ensure_driver_alive():
                time.sleep(0.3)  # Reduzido de 0.5 para 0.3
                continue

            return action_func(*args, **kwargs)

        except (InvalidSessionIdException, WebDriverException) as e:
            print(f"Driver error on attempt {attempt + 1}: {str(e)}")

            if attempt < max_retries - 1:
                print("Recreating driver and retrying...")
                ensure_driver_alive()
                time.sleep(0.3)  # Reduzido de 0.5 para 0.3
            else:
                print("Max retries reached, raising exception")
                raise e
        except Exception as e:
            print(f"Non-driver error: {str(e)}")
            raise e


def safe_find_element(by, selector, context=None, max_retries=2):
    """Encontra um elemento com proteção contra stale element reference"""
    for attempt in range(max_retries):
        try:
            if context:
                return context.find_element(by, selector)
            else:
                return driver.find_element(by, selector)
        except Exception as e:
            if "stale element reference" in str(e).lower() and attempt < max_retries - 1:
                print(f"Stale element reference, retrying... (attempt {attempt + 1})")
                time.sleep(0.3)  # Reduzido de 0.5 para 0.3
                continue
            raise e


def safe_find_elements(by, selector, context=None, max_retries=2):
    """Encontra elementos com proteção contra stale element reference"""
    for attempt in range(max_retries):
        try:
            if context:
                return context.find_elements(by, selector)
            else:
                return driver.find_elements(by, selector)
        except Exception as e:
            if "stale element reference" in str(e).lower() and attempt < max_retries - 1:
                print(f"Stale element reference, retrying... (attempt {attempt + 1})")
                time.sleep(0.3)  # Reduzido de 0.5 para 0.3
                continue
            raise e


# Inicializa o driver
driver = create_chrome_driver()
wait = WebDriverWait(driver, 8)

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
            link_element = safe_find_element(By.CSS_SELECTOR, 'a.hfpxzc', context=card)
            href = link_element.get_attribute('href')

            # Verifica se já processamos esta URL
            if CACHE_ENABLED and href in processed_urls_cache:
                continue

            # Nome do card lateral
            try:
                name_element = safe_find_element(By.CSS_SELECTOR, '.qBF1Pd.fontHeadlineSmall', context=card)
                name = name_element.text
            except:
                name = None

            # Facilidades do card lateral
            try:
                facility_elements = safe_find_elements(By.CSS_SELECTOR, '.Yfjtfe.dc6iWb', context=card)
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

            # Adiciona ao cache
            if CACHE_ENABLED:
                processed_urls_cache.add(href)

        except Exception as e:
            print(f"Error collecting data from card {i + 1}: {str(e)}")
            continue

    return card_data


def extract_details_from_modal_optimized(product_type, card_info):
    """Versão otimizada da extração de detalhes do modal"""
    start_time = time.time()

    def _extract_logic():
        # Navega diretamente para o link do estabelecimento
        driver.get(card_info['href'])
        time.sleep(1.8)  # Reduzido de 2.5 para 1.8

        # Extrai informações básicas primeiro (mais importantes)
        result = {
            "name": card_info.get('name_preview'),
            "rating": None,
            "rating_count": None,
            "description": "",
            "images": [],
            "link": None,
            "facilities": card_info.get('facilities', []),
            "lat": None,
            "lon": None,
            "phone": None,
            "address": None,
            "price": None,
            "operating_hours": None
        }

        # Nome do business (do modal)
        try:
            name_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf, h1')))
            result["name"] = name_element.text
        except:
            pass

        # Rating (do modal)
        try:
            rating_element = driver.find_element(By.CSS_SELECTOR, '.F7nice span:first-child span[aria-hidden="true"]')
            result["rating"] = rating_element.text
        except:
            pass

        # Rating count (do modal - no elemento UY7F9)
        try:
            rating_count_element = driver.find_element(By.CSS_SELECTOR, '.UY7F9')
            rating_count_text = rating_count_element.text
            result["rating_count"] = remove_parentheses(rating_count_text)
        except:
            pass

        # Stars (apenas para hotéis)
        if product_type.lower() == 'hotel':
            try:
                stars_element = driver.find_element(By.CSS_SELECTOR, '.LBgpqf span.mgr77e span span:last-child')
                stars_text = stars_element.text
                result["stars"] = extract_numbers_only(stars_text)
            except:
                result["stars"] = None

        # Clica no botão "About" para acessar descrição e facilities
        try:
            about_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label*="About"]')))
            driver.execute_script("arguments[0].click();", about_button)
            time.sleep(1.2)  # Reduzido de 2.0 para 1.2
        except Exception as e:
            print(f"Could not click About button: {str(e)}")

        # Descrição (após clicar em About)
        try:
            description_selectors = [
                '.HeZRrf .P1LL5e',
                '.PbZDve p .HlvSq',
                '.PbZDve .HlvSq',
                '.HeZRrf',
                '.PbZDve p'
            ]

            for selector in description_selectors:
                try:
                    if selector == '.HeZRrf .P1LL5e':
                        description_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if description_elements:
                            desc_parts = [elem.text.strip() for elem in description_elements if elem.text.strip()]
                            result["description"] = ' '.join(desc_parts)
                            if result["description"]:
                                break
                    else:
                        description_element = driver.find_element(By.CSS_SELECTOR, selector)
                        description_text = description_element.text.strip()
                        if description_text and len(description_text) > 20:
                            result["description"] = description_text
                            break
                except:
                    continue

        except Exception as e:
            print(f"Could not extract description: {str(e)}")

        # Facilities (após clicar em About)
        try:
            if product_type.lower() == 'hotel':
                facility_elements = driver.find_elements(By.CSS_SELECTOR, '.QoXOEc .CK16pd')
                for facility_elem in facility_elements:
                    try:
                        has_unavailable_symbol = facility_elem.find_elements(By.CSS_SELECTOR, '.G47vBd')
                        if not has_unavailable_symbol:
                            facility_text_elem = facility_elem.find_element(By.CSS_SELECTOR, '.gSamH')
                            facility_text = facility_text_elem.text.strip()
                            if facility_text:
                                result["facilities"].append(facility_text)
                    except:
                        continue
            else:
                facility_sections = driver.find_elements(By.CSS_SELECTOR, '.iP2t7d')
                for section in facility_sections:
                    try:
                        facility_items = section.find_elements(By.CSS_SELECTOR, '.hpLkke .iNvpkb span[aria-label]')
                        for item in facility_items:
                            facility_text = item.get_attribute('aria-label')
                            if facility_text:
                                clean_facility = re.sub(r'^(Has |Good for |Accepts |Getting )', '', facility_text)
                                result["facilities"].append(clean_facility)
                    except:
                        continue

        except Exception as e:
            print(f"Could not extract facilities: {str(e)}")

        # Extrai informações adicionais de forma otimizada
        processing_time = time.time() - start_time

        # Coordenadas (latitude/longitude) - Rápido
        try:
            current_url = driver.current_url
            if '@' in current_url:
                coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
                if coords_match:
                    result["lat"] = coords_match.group(1)
                    result["lon"] = coords_match.group(2)
        except:
            pass

        # Telefone e endereço - Rápido
        try:
            phone_elements = driver.find_elements(By.CSS_SELECTOR, 'button[data-item-id*="phone"] .Io6YTe')
            if phone_elements:
                result["phone"] = phone_elements[0].text

            address_elements = driver.find_elements(By.CSS_SELECTOR, 'button[data-item-id="address"] .Io6YTe')
            if address_elements:
                result["address"] = address_elements[0].text
        except:
            pass

        # Informações de menor prioridade só se ainda temos tempo
        if processing_time < 25:
            # Imagem principal
            try:
                img_element = driver.find_element(By.CSS_SELECTOR, 'img[src*="googleusercontent.com"]')
                img = img_element.get_attribute('src')
                result["images"] = [img] if img else []
            except:
                pass

            # Link do site
            try:
                link_element = driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
                result["link"] = link_element.get_attribute('href')
            except:
                pass

        if processing_time < 30:
            # Preço (APENAS para hotéis)
            if product_type.lower() == 'hotel':
                try:
                    price_buttons = driver.find_elements(By.CSS_SELECTOR,
                                                         'button[aria-label*="R$"], button[aria-label*="$"], button[aria-label*="€"]')
                    for button in price_buttons:
                        try:
                            price_aria_label = button.get_attribute('aria-label')
                            price_match = re.search(r'(R\$\d+[\d,.]*|€\d+[\d,.]*|\$\d+[\d,.]*)', price_aria_label)
                            if price_match:
                                result["price"] = price_match.group(1)
                                break
                        except:
                            continue
                except:
                    pass

            # Horários de funcionamento
            try:
                hours_elements = driver.find_elements(By.CSS_SELECTOR, '.Io6YTe.fontBodyMedium.kR99db.fdkmkc')
                for hours_element in hours_elements:
                    hours_text = hours_element.text
                    if hours_text and (
                            'Check-in' in hours_text or 'Check-out' in hours_text or 'Open' in hours_text or 'Closed' in hours_text):
                        result["operating_hours"] = hours_text
                        break
            except:
                pass

        return result

    try:
        return _extract_logic()
    except (InvalidSessionIdException, WebDriverException):
        ensure_driver_alive()
        time.sleep(0.3)
        return _extract_logic()
    except Exception as e:
        print(f"Error extracting details: {str(e)}")
        return {
            "name": card_info.get('name_preview'),
            "rating": None,
            "rating_count": None,
            "description": "",
            "images": [],
            "link": None,
            "facilities": card_info.get('facilities', []),
            "lat": None,
            "lon": None,
            "phone": None,
            "address": None,
            "price": None,
            "operating_hours": None
        }


def load_more_cards_optimized(results_panel, current_count, max_stagnant=2):
    """Carrega mais cards usando a abordagem do código antigo - OTIMIZADO"""
    stagnant_iterations = 0
    previous_count = current_count

    print(f"Loading more cards...")

    while True:
        try:
            # Scroll até o final da lista
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
            time.sleep(1.2)  # Reduzido de 2.0 para 1.2

            # Conta quantos cards existem agora
            current_cards = safe_find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')
            new_count = len(current_cards)

            print(f"Cards loaded: {new_count}")

            # Se não carregou novos cards, incrementa contador de estagnação
            if new_count == previous_count:
                stagnant_iterations += 1
                if stagnant_iterations >= max_stagnant:
                    print(f"No more cards to load. Total: {new_count}")
                    return new_count, True
                # Tenta scroll mais agressivo quando não carrega
                for _ in range(2):
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
                    time.sleep(0.6)  # Reduzido de 1.0 para 0.6
            else:
                stagnant_iterations = 0

            previous_count = new_count

            # Scroll adicional para garantir carregamento
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight - 100", results_panel)
            time.sleep(0.4)  # Reduzido de 0.8 para 0.4
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
            time.sleep(0.8)  # Reduzido de 1.5 para 0.8

        except Exception as e:
            if "stale element reference" in str(e).lower():
                print("Stale element, recreating results_panel...")
                try:
                    results_panel = safe_find_element(By.CSS_SELECTOR, 'div[role="feed"]')
                    continue
                except:
                    print("Could not recreate results_panel")
                    return previous_count, True
            else:
                print(f"Error during scrolling: {str(e)}")
                return previous_count, True


def scrape_google_maps_with_keyword(product_type, location, search_term, max_results=None):
    """Faz o scraping para um termo de busca específico - ABORDAGEM ORIGINAL OTIMIZADA"""
    global total_processing_time, total_items_processed, item_times

    def _navigate_to_search():
        query = f"{search_term} {location}"
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}/?hl=en&gl=us"
        driver.get(url)
        time.sleep(2.2)  # Reduzido de 3.0 para 2.2

    safe_driver_action(_navigate_to_search)

    # FASE 1: Carregamento de todos os cards possíveis
    try:
        results_panel = safe_find_element(By.CSS_SELECTOR, 'div[role="feed"]')
    except NoSuchElementException:
        print(f"No results found for search term: '{search_term}'")
        return []

    print(f"Loading all available cards for: '{search_term}'")

    # Carrega cards iniciais
    initial_cards = safe_find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')
    current_count = len(initial_cards)
    print(f"Initial cards: {current_count}")

    # Carrega TODOS os cards disponíveis
    total_count, finished = load_more_cards_optimized(results_panel, current_count)
    print(f"Total cards available: {total_count}")

    # Coleta os links de TODOS os cards
    def _collect_all_cards():
        cards = safe_find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')
        return collect_card_links(cards)

    card_data_list = safe_driver_action(_collect_all_cards)
    total_available = len(card_data_list)
    print(f"Cards collected for processing: {total_available}")

    # Determina quantos cards processar
    if max_results is not None:
        cards_to_process = min(max_results, total_available)
        print(f"Will process {cards_to_process} cards (limited by max_results={max_results})")
    else:
        cards_to_process = total_available
        print(f"Will process ALL {cards_to_process} cards (no limit specified)")

    # FASE 2: Processamento dos cards
    results = []
    db = DatabaseManager()
    processed_count = 0
    new_records_count = 0

    ensure_driver_alive()

    for card_index in range(cards_to_process):
        card_info = card_data_list[card_index]

        item_start_time = time.time()
        print(f"Processing card {card_index + 1}/{cards_to_process} (New records: {new_records_count})...")

        result = extract_details_from_modal_optimized(product_type, card_info)

        item_time = time.time() - item_start_time
        item_times.append(item_time)
        total_processing_time += item_time
        total_items_processed += 1

        print(f"  Item processed in {item_time:.2f}s (Avg: {total_processing_time / total_items_processed:.2f}s)")

        if result and result.get('name'):
            existing_record = None

            # Verificação robusta de registro existente
            if result.get('lat') and result.get('lon'):
                # Busca por nome e coordenadas (mais preciso)
                existing_records = db.get(
                    "SELECT * FROM products WHERE name = ? AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ? AND product_type = ?",
                    [
                        result.get('name'),
                        float(result.get('lat')) - 0.001,
                        float(result.get('lat')) + 0.001,
                        float(result.get('lon')) - 0.001,
                        float(result.get('lon')) + 0.001,
                        product_type
                    ]
                )
                if existing_records:
                    existing_record = existing_records[0]

            # Fallback: busca apenas por nome se não tiver coordenadas
            if not existing_record and result.get('name'):
                existing_records = db.get(
                    "SELECT * FROM products WHERE name = ? AND product_type = ?",
                    [result.get('name'), product_type]
                )
                if existing_records:
                    existing_record = existing_records[0]

            if existing_record:
                print(f"Found existing record with ID: {existing_record['id']} - updating with new data")

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

                if product_type.lower() == 'hotel':
                    update_data['stars'] = int(result.get('stars')) if result.get('stars') else None

                db.update(existing_record['id'], update_data)

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

                if product_type.lower() == 'hotel':
                    json_result["stars"] = result.get('stars')

                results.append(json_result)

            else:
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

                if product_type.lower() == 'hotel':
                    db_data['stars'] = int(result.get('stars')) if result.get('stars') else None

                record_id = db.create(db_data)
                if record_id:
                    result['db_id'] = record_id
                    print(f"New record saved with ID: {record_id}")
                    new_records_count += 1

                results.append(result)

        processed_count += 1

        time.sleep(0.1)  # Reduzido de 0.3 para 0.1

        if processed_count % 10 == 0:
            ensure_driver_alive()

    print(f"Completed processing {processed_count} cards for search term '{search_term}'")
    print(f"New records created: {new_records_count}")
    print(f"Total results: {len(results)}")

    return results


def scrape_google_maps(product_type, location, max_results=None):
    """Função principal que executa o scraping com limite opcional"""
    global total_processing_time, total_items_processed, item_times, processed_urls_cache

    total_processing_time = 0
    total_items_processed = 0
    item_times = []
    processed_urls_cache.clear()  # Limpa o cache a cada execução

    all_results = []
    search_start_time = time.time()

    # TODAS as palavras-chave originais (mantém todas)
    search_terms = [product_type]
    if product_type in PRODUCT_KEYWORDS:
        search_terms.extend(PRODUCT_KEYWORDS[product_type])

    print(f"Starting scraping for: {product_type}")
    print(f"Total search terms: {len(search_terms)}")
    print("=" * 60)

    for i, search_term in enumerate(search_terms, 1):
        term_start_time = time.time()
        print(f"\n[{i}/{len(search_terms)}] Processing search term: '{search_term}'")
        print("-" * 50)

        try:
            results = scrape_google_maps_with_keyword(product_type, location, search_term, max_results)
            all_results.extend(results)
            term_time = time.time() - term_start_time
            print(f"Search '{search_term}' completed in {term_time:.2f}s: {len(results)} results")

        except Exception as e:
            print(f"Error processing search term '{search_term}': {str(e)}")
            continue

    total_time = time.time() - search_start_time
    print(f"\n{'=' * 60}")
    print("ALL SEARCHES COMPLETED")
    print(f"Total execution time: {total_time:.2f}s")
    print(f"Total results collected: {len(all_results)}")

    if item_times:
        avg_time = sum(item_times) / len(item_times)
        max_time = max(item_times)
        min_time = min(item_times)
        print(f"\nTime statistics:")
        print(f"- Total items processed: {len(item_times)}")
        print(f"- Average time per item: {avg_time:.2f}s")
        print(f"- Fastest item: {min_time:.2f}s")
        print(f"- Slowest item: {max_time:.2f}s")
        print(f"- Total processing time: {sum(item_times):.2f}s")

    return all_results


if __name__ == "__main__":
    allowed_types = ['hotel', 'gastronomy', 'attraction', 'shopping', 'activity']
    product_type = input("Enter product type (hotel, gastronomy, attraction, shopping, activity): ")

    if product_type not in allowed_types:
        print("Invalid product type")
        try:
            driver.quit()
        except:
            pass
        exit(1)

    location = input("Enter location (city/state/country): ")

    max_results_input = input("Enter max results per search term (leave empty for all): ").strip()
    max_results = int(max_results_input) if max_results_input else None

    try:
        overall_start_time = time.time()
        data = scrape_google_maps(product_type, location, max_results)
        overall_time = time.time() - overall_start_time

        file_name = f"{product_type}.json"
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 80}")
        print("FINAL EXECUTION SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total execution time: {overall_time:.2f}s")
        print(f"Total results saved: {len(data)}")
        print(f"Results saved to: {file_name}")
        print(f"{'=' * 80}")

        # Conta registros novos vs existentes no total
        unique_db_ids = set()
        new_records_count = 0
        existing_records_count = 0

        for item in data:
            if 'db_id' in item:
                if item['db_id'] not in unique_db_ids:
                    unique_db_ids.add(item['db_id'])
                    new_records_count += 1
                else:
                    existing_records_count += 1

        print(f"New records: {new_records_count}")
        print(f"Existing records: {existing_records_count}")
        print(f"Total unique results: {len(data)}")

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
        for term in search_terms[:10]:
            print(f"- {term}")
        if len(search_terms) > 10:
            print(f"- ... and {len(search_terms) - 10} more keywords")

    except Exception as e:
        print(f"Error during execution: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        try:
            driver.quit()
            print("Driver closed successfully")
        except Exception as e:
            print(f"Error closing driver: {str(e)}")