import os
import time
import re
from DatabaseManager import DatabaseManager
from dotenv import load_dotenv
from google import genai

load_dotenv()
db = DatabaseManager()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
RESOURCE_EXHAUSTED = 0


def extract_retry_delay_from_error(error):
    error_str = str(error)
    match = re.search(r'retryDelay["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)s', error_str)
    if match:
        return float(match.group(1))

    match2 = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', error_str)
    if match2:
        return float(match2.group(1))

    return 10


def create_promotional_description(card_href):
    prompt = (
        f'Vasculhe as reviews da ficha deste negócio do Google Maps ({card_href}), e gere um texto de descrição promocional curto e persuasivo para esse local, citando diferenciais e elogios recorrentes (em inglês). O retorno deve ser apenas da descrição em texto simples, sem simbolos, HTML ou parágrafos. O retorno também deve ter no mínimo 100 caracteres e no máximo 400 caracteres.'
    )
    resp = client.models.generate_content(
        model="gemini-2.5-flash-lite", contents=prompt
    )
    return resp.text


def process_registry(reg_id, card_href, max_retries=3):
    global RESOURCE_EXHAUSTED
    attempts = 0
    while attempts < max_retries:
        try:
            description = create_promotional_description(card_href)

            print(description)

            db.update(reg_id, {'description': description})
            print(f"{reg_id} updated...")

            RESOURCE_EXHAUSTED = 0
            break
        except Exception as e:
            print(f"Erro no id {reg_id}:")
            error_text = str(e)
            if 'RESOURCE_EXHAUSTED' in error_text:
                print('RESOURCE_EXHAUSTED')
                RESOURCE_EXHAUSTED += 1
                delay = extract_retry_delay_from_error(e) + 1
                print(f"Aguardando {delay} segundos conforme retryDelay da API...")
                time.sleep(delay)
            else:
                print(error_text)

            attempts += 1
            continue


def main():
    data = db.get(
        "SELECT * from products WHERE description IS NULL OR description='' OR description=?",
        ['Based on sightseeing, recreation, and getting around']
    )

    print(f"Registros encontrados: {len(data)}")
    if len(data) == 0:
        exit()

    for registry in data:
        if RESOURCE_EXHAUSTED >= 9:
            print('A API do Gemini não está respondendo, encerrando o fluxo...')
            exit()

        reg_id = registry.get('id')
        href = registry.get('card_href')
        print(f'Processando ID {reg_id} - {registry.get("name")}...')
        process_registry(reg_id, href)


if __name__ == "__main__":
    main()
