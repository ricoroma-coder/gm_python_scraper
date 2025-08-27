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

        # Descrição (busca específica no elemento .HeZRrf)
        description = ""
        try:
            # Primeiro clica no botão para expandir descrição se existir
            try:
                expand_button = driver.find_element(By.CSS_SELECTOR, '.HeZRrf button, .HeZRrf .gkhule')
                driver.execute_script("arguments[0].click();", expand_button)
                time.sleep(1)
            except:
                pass

            # Busca especificamente no elemento .HeZRrf
            description_elements = driver.find_elements(By.CSS_SELECTOR, '.HeZRrf .P1LL5e')
            if description_elements:
                desc_parts = [elem.text.strip() for elem in description_elements if elem.text.strip()]
                description = ' '.join(desc_parts)

            # Se não encontrou, tenta buscar texto diretamente no .HeZRrf
            if not description:
                herzrf_element = driver.find_element(By.CSS_SELECTOR, '.HeZRrf')
                herzrf_text = herzrf_element.text.strip()
                if herzrf_text and len(herzrf_text) > 20:
                    description = re.sub(r'\b(More|Less|Show more|Show less)\b', '', herzrf_text).strip()

        except:
            description = ""

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

        # Monta o resultado
        result = {
            "name": name,
            "rating": rating,
            "rating_count": rating_count,
            "description": description,
            "images": images,
            "link": link,
            "facilities": card_info['facilities'],  # Usa as facilidades coletadas do card
            "lat": lat,
            "lon": lon,
            "phone": phone,
            "address": address,
            "operating_hours": operating_hours
        }

        # Adiciona stars apenas para hotéis
        if product_type.lower() == 'hotel':
            result["stars"] = stars

        return result

    except Exception as e:
        print(f"Error extracting details from modal: {str(e)}")
        return None


def scrape_google_maps(product_type, location, max_results=10):
    query = f"{product_type} {location}"
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
                # Se existe no banco, monta o resultado com os dados do banco
                print(f"Found existing record with ID: {existing_record['id']} (not counting towards limit)")

                # Converte os dados do banco para o formato JSON
                json_result = {
                    "name": existing_record['name'],
                    "rating": str(existing_record['rating']) if existing_record['rating'] else None,
                    "rating_count": str(existing_record['rating_count']) if existing_record['rating_count'] else None,
                    "description": existing_record['description'],
                    "images": existing_record['images'].split(';') if existing_record['images'] else [],
                    "link": existing_record['link'],
                    "facilities": existing_record['facilities'].split(';') if existing_record['facilities'] else [],
                    "lat": str(existing_record['latitude']) if existing_record['latitude'] else None,
                    "lon": str(existing_record['longitude']) if existing_record['longitude'] else None,
                    "phone": existing_record['phone'],
                    "address": existing_record['address'],
                    "operating_hours": None,  # Campo não armazenado no banco
                    "db_id": existing_record['id']
                }

                # Adiciona stars apenas para hotéis
                if product_type.lower() == 'hotel':
                    json_result["stars"] = str(existing_record['stars']) if existing_record['stars'] else None

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
                    'address': result.get('address')
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

    print(
        f"Finished processing. Found {processed_count} new records and {len(results) - processed_count} existing records.")
    return results


if __name__ == "__main__":
    product_type = input("Enter product type (hotel, restaurant, attraction, shopping, etc.): ")
    location = input("Enter location (city/state/country): ")

    try:
        data = scrape_google_maps(product_type, location)

        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"Search completed! {len(data)} results saved to results.json and database")
        print(f"Results breakdown:")

        # Conta registros novos vs existentes
        new_records_count = sum(1 for item in data if 'db_id' in item and any(
            r.get('db_id') == item['db_id'] for r in data if r != item) == False)
        existing_records_count = len(data) - new_records_count

        print(f"- New records processed: {new_records_count}")
        print(f"- Existing records found: {existing_records_count}")

        # Exemplo de uso das funções do banco de dados
        db = DatabaseManager()

        # Consulta todos os registros
        all_products = db.get("SELECT * FROM products")
        print(f"Total products in database: {len(all_products)}")

        # Consulta por tipo de produto
        current_type_products = db.get("SELECT * FROM products WHERE product_type = ?", [product_type])
        print(f"Products of type '{product_type}' in database: {len(current_type_products)}")

    except Exception as e:
        print(f"Error during execution: {str(e)}")

    finally:
        driver.quit()