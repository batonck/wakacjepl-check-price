import requests
from bs4 import BeautifulSoup
import json
import re
import os

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
    price_limit = config['price_limit']
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', config.get('discord_webhook_url'))
    for offer_url in hotels:
        try:
            price = get_price_from_page(offer_url)
            print(f'Aktualna cena dla {offer_url}: {price} PLN')
            if price <= price_limit:
                send_discord_alert(webhook_url, offer_url, price)
            else:
                print(f'Cena powyżej progu {price_limit} PLN.')
        except Exception as e:
            print(f'Błąd dla {offer_url}: {e}')

if __name__ == '__main__':
    main()
