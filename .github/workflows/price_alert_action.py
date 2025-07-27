import requests
from bs4 import BeautifulSoup
import json
import re
import os

def get_env_or_config(key, config):
    value = os.environ.get(key.upper())
    if value is not None and value.strip() != '':
        return value
    return config.get(key.lower())

def get_price_from_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Check for no offers message
    if 'znaleźliśmy ofert, które spełniają wszystkie wybrane kryteria' in soup.get_text():
        return None
    for tag in soup.find_all(['span', 'div']):
        text = tag.get_text(strip=True)
        if text.endswith('zł'):
            match = re.search(r'(\d+[\s\d]*)zł', text)
            if match:
                price_str = match.group(1).replace(' ', '')
                try:
                    return float(price_str)
                except ValueError:
                    continue
    raise Exception('Nie znaleziono ceny na stronie!')

def update_url_date_range(url, date_from, date_to):
    # Replace od-YYYY-MM-DD and do-YYYY-MM-DD in the url
    url = re.sub(r'od-\d{4}-\d{2}-\d{2}', f'od-{date_from}', url)
    url = re.sub(r'do-\d{4}-\d{2}-\d{2}', f'do-{date_to}', url)
    return url

def update_url_catering(url, catering):
    # Zamień fragment cateringowy w URL na podstawie wartości catering
    # Obsługuje najczęstsze przypadki: all-inclusive, HB, BB, FB, AI, itp.
    url = re.sub(r',(all-inclusive|hb|bb|fb|ai),', f',{catering.lower()},', url, flags=re.IGNORECASE)
    return url

def extract_hotel_name_from_url(url):
    # Pobierz fragment po 'wczasy/' i przed '-h' lub '/?'
    match = re.search(r'wczasy/([^/?]+?)-h\d+', url)
    if match:
        return match.group(1).replace('-', ' ').title()
    # fallback: spróbuj pobrać po 'wczasy/' do pierwszego '/'
    match = re.search(r'wczasy/([^/?]+)', url)
    if match:
        return match.group(1).replace('-', ' ').title()
    return 'Nieznany Hotel'

def send_discord_alert(webhook_url, offer_url, price, catering=None):
    hotel_name = extract_hotel_name_from_url(offer_url)
    content = f'Cena wycieczki do **{hotel_name}** spadła do {price} PLN!'
    if catering:
        content += f' ({catering})'
    content += f'\nOferta: {offer_url}'
    data = {"content": content}
    response = requests.post(webhook_url, json=data)
    if response.status_code == 204:
        print('Wysłano powiadomienie na Discord!', flush=True)
    else:
        print(f'Błąd przy wysyłaniu na Discord: {response.status_code} {response.text}', flush=True)

def send_discord_no_offer_alert(webhook_url, offer_url):
    content = f'Brak ofert spełniających kryteria na ten moment. Sprawdź ponownie później.\nLink: {offer_url}'
    data = {"content": content}
    response = requests.post(webhook_url, json=data)
    if response.status_code == 204:
        print('Wysłano powiadomienie o braku ofert na Discord!', flush=True)
    else:
        print(f'Błąd przy wysyłaniu na Discord: {response.status_code} {response.text}', flush=True)

def main():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    hotels = config['hotels']
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', config.get('discord_webhook_url'))
    date_from = get_env_or_config('DATE_FROM', config)
    date_to = get_env_or_config('DATE_TO', config)
    for offer_url, hotel_info in hotels.items():
        price_limit = hotel_info['price_limit']
        catering = hotel_info['catering']
        url = update_url_date_range(offer_url, date_from, date_to)
        url = update_url_catering(url, catering)
        try:
            price = get_price_from_page(url)
            if price is None:
                send_discord_no_offer_alert(webhook_url, url)
                print(f'Brak ofert dla {url} ({catering})', flush=True)
                continue
            print(f'Aktualna cena dla {url} ({catering}): {price} PLN', flush=True)
            if price <= price_limit:
                send_discord_alert(webhook_url, url, price, catering)
            else:
                print(f'Cena powyżej progu {price_limit} PLN.', flush=True)
        except Exception as e:
            print(f'Błąd dla {url}: {e}', flush=True)

if __name__ == '__main__':
    main()
