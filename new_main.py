import os
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
from datetime import datetime

class Scraper:
    def menu(self):
        menu = """
Escolha o país:
1. Brasil
"""
        valid_options = {1: 'https://lista.mercadolivre.com.br/'}

        while True:
            print(menu)
            try:
                option = int(input('Número de país (Exemplo: 1): '))
                if option in valid_options:
                    self.base_url = valid_options[option]
                    break
                else:
                    print("Escolha um número válido.")
            except ValueError:
                print("Digite um número válido.")

    def convert_to_float(self, price_str):
        """Converte uma string de preço para float."""
        if not price_str:
            return 0.0
        try:
            price_cleaned = price_str.replace("R$", "").replace("$", "").replace(".", "").replace(",", ".").strip()
            return float(price_cleaned)
        except ValueError:
            return 0.0

    def format_to_currency(self, value):
        """Formata um valor float para o formato de moeda brasileiro."""
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def extract_mlb_code(self, post_link):
        """Extrai o código MLB da URL do post."""
        try:
            if "MLB-" in post_link:
                start_index = post_link.find("MLB-")
                return post_link[start_index:start_index + 14]  # "MLB-" (4 chars) + 10 chars = 14
            pattern = r"MLB[^#]*"  # MLB seguido de qualquer sequência que não contenha '#'
            match = re.search(pattern, post_link)
            return match.group(0) if match else "N/A"
        except Exception:
            return "N/A"

    def scrape_product(self, post):
        """Extrai as informações de um post."""
        try:
            # Título
            title = post.find('h2', class_='poly-box poly-component__title')
            title = title.get_text().strip().capitalize() if title else "N/A"

            # Vendedor
            seller = post.find('span', class_='poly-component__seller')
            seller = seller.get_text().strip()[4:].capitalize() if seller else "N/A"

            # Preço anterior
            price_previous = post.find('s', class_='andes-money-amount andes-money-amount--previous andes-money-amount--cents-comma')
            if price_previous:
                price_previous = price_previous.text
            else:
                price_previous = post.find('span', class_='andes-money-amount__fraction').text
            
            price_previous = self.format_to_currency(self.convert_to_float(price_previous))
            
            # Preco atual
            price_current = post.find('span', class_='andes-money-amount andes-money-amount--cents-superscript').text
            price_current = self.format_to_currency(self.convert_to_float(price_current))

            # Desconto
            discount = post.find('span', class_='andes-money-amount__discount')
            discount = discount.get_text().strip() if discount else "0%"

            # Parcelamento e tipo de anúncio
            installments = post.find('span', class_='poly-price__installments poly-text-positive')
            ad_type = 'Premium' if installments else 'Classic'

            if not installments:
                installments = post.find('span', class_='poly-price__installments poly-text-primary')
            
            installments = installments.get_text().strip() if installments else "N/A"

            # Link do post
            post_link = post.find("a")["href"]
            mlb_code = self.extract_mlb_code(post_link)

            # Link da imagem
            img_link = post.find("img").get("data-src", post.find("img").get("src", "N/A"))

            # Retorna os dados extraídos
            return {
                "mlb": mlb_code,
                "title": title,
                "seller": seller,
                "ad_type": ad_type,
                "price_previous": price_previous,
                "price_current": price_current,
                "discount": discount,
                "installments": installments,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "post link": post_link,
                "image link": img_link,
            }
        except Exception as e:
            print(f"Erro ao processar o post: {e}")
            return {}

    def scraping(self):
        """Realiza o processo de scraping."""
        product_name = input("\nDigite o produto: ")
        cleaned_name = product_name.replace(" ", "-").lower()
        urls = [self.base_url + cleaned_name]

        page_number = 50
        for i in range(0, 10000, 50):
            urls.append(f"{self.base_url}{cleaned_name}_Desde_{page_number + 1}_NoIndex_True")
            page_number += 50

        self.data = []

        for i, url in enumerate(urls, start=1):
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find_all('li', class_='ui-search-layout__item')

            if not content:
                print("\nTérmino do scraping.")
                break

            print(f"\nScrapeando página número {i}: {url}")

            for post in content:
                post_data = self.scrape_product(post)
                if post_data:
                    self.data.append(post_data)

    def export_to_csv(self, cleaned_name):
        """Exporta os dados para um arquivo CSV."""
        os.makedirs("data", exist_ok=True)
        file_name = f"data/ml_{cleaned_name[:10]}.csv"
        df = pd.DataFrame(self.data)
        df.to_csv(file_name, sep=";", encoding="utf-8-sig", index=False)
        print(f"Arquivo CSV exportado com sucesso: {file_name}")

if __name__ == "__main__":
    scraper = Scraper()
    scraper.menu()
    scraper.scraping()
    product_name = input("\nDigite novamente o produto para nome do arquivo CSV: ")
    cleaned_name = product_name.replace(" ", "-").lower()
    scraper.export_to_csv(cleaned_name)
