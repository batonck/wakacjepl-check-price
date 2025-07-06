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

def send_discord_alert(webhook_url, offer_url, price):
    content = f'Cena wycieczki spadła do {price} PLN!\nOferta: {offer_url}'
    data = {"content": content}
    response = requests.post(webhook_url, json=data)
    if response.status_code == 204:
        print('Wysłano powiadomienie na Discord!')
    else:
        print(f'Błąd przy wysyłaniu na Discord: {response.status_code} {response.text}')

def main():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    hotels = config['hotels']
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', config.get('discord_webhook_url'))
    date_from = get_env_or_config('DATE_FROM', config)
    date_to = get_env_or_config('DATE_TO', config)
    for offer_url, price_limit in hotels.items():
        url = update_url_date_range(offer_url, date_from, date_to)
        try:
            price = get_price_from_page(url)
            print(f'Aktualna cena dla {url}: {price} PLN')
            if price <= price_limit:
                send_discord_alert(webhook_url, url, price)
            else:
                print(f'Cena powyżej progu {price_limit} PLN.')
        except Exception as e:
            print(f'Błąd dla {url}: {e}')

if __name__ == '__main__':
    main()
