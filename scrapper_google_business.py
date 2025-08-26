import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys

# Configurações do ChromeDriver
chrome_options = Options()
chrome_options.add_argument("--headless")  # roda em background
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# Silencia logs do Chrome
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument("--disable-logging")
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
chrome_options.add_experimental_option("useAutomationExtension", False)

# Ajuste o path para o seu chromedriver
service = Service(executable_path="chromedriver.exe")
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


def scrape_google_maps(product_type, location, max_results=60):
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

    # Seleciona os cards visíveis (agora com mais resultados carregados)
    cards = driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK.THOPZb.CpccDe')[:max_results]
    print(f"Final cards collected: {len(cards)}")

    # FASE 1: Coleta todos os links e dados básicos dos cards
    print("Collecting card links and basic data...")
    card_data_list = collect_card_links(cards)

    # FASE 2: Visita cada estabelecimento individualmente
    results = []
    for i, card_info in enumerate(card_data_list):
        print(f"Processing item {i + 1}/{len(card_data_list)}...")

        result = extract_details_from_modal(product_type, card_info)
        if result:
            results.append(result)

        # Pequena pausa entre requisições
        time.sleep(1)

    return results


if __name__ == "__main__":
    product_type = input("Enter product type (hotel, restaurant, attraction, shopping, etc.): ")
    location = input("Enter location (city/state/country): ")

    try:
        data = scrape_google_maps(product_type, location)

        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"Search completed! {len(data)} results saved to results.json")

    except Exception as e:
        print(f"Error during execution: {str(e)}")

    finally:
        driver.quit()