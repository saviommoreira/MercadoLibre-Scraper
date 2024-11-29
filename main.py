import os
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
from datetime import datetime

class Scraper():

    def menu(self):
        menu = ("""
    Ecolha o país:
    1. Brasil
        """)

        valid_options = list(range(1, 19))

        while True:
            print(menu)
            opcion = int(input('Número de país (Exemplo: 1): '))

            if opcion in valid_options:
                urls = {
                1: 'https://lista.mercadolivre.com.br/',
                }
                self.base_url = urls[opcion]
                break
            else:
                print("Escolha um número de 1 a 1")

    def convert_to_float(self, price_str):
        """Converte uma string de preço para float"""
        if not price_str:
            return 0.0
        try:
            price_cleaned = price_str.replace("R$", "").replace("$", "").replace(".", "").replace(",", ".").strip()
            return float(price_cleaned)
        except ValueError:
            return 0.0

    def format_to_currency(self, value):
        """Formata um valor float para o formato de moeda brasileiro"""
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def scraping(self):
        # User search
        product_name = input("\nDigite o produto: ")
        # Clean the user input
        cleaned_name = product_name.replace(" ", "-").lower()
        # Create the urls to scrap
        urls = [self.base_url + cleaned_name]

        page_number = 50
        for i in range(0, 10000, 50):
            urls.append(f"{self.base_url}{cleaned_name}_Desde_{page_number + 1}_NoIndex_True")
            page_number += 50

        # create a list to save the data
        self.data = []
        # create counter
        c = 1
            
        # Iterate over each url
        for i, url in enumerate(urls, start=1):

            # Get the html of the page
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
                
            # take all posts
            content = soup.find_all('li', class_='ui-search-layout__item')
            #print(content)
            
            # Check if there's no content to scrape
            if not content:
                print("\nTérmino do scraping.")
                break

            print(f"\nScrapeando página número {i}. {url}")
            
            # iteration to scrape posts
            for post in content:
                # get the title
                title = post.find('h2', class_='poly-box poly-component__title')
                title = title.get_text().strip().capitalize()

                # get the previous price
                price_previous = post.find('s', class_='andes-money-amount andes-money-amount--previous andes-money-amount--cents-comma')
                if price_previous:
                    price_previous = price_previous.text
                else:
                    price_previous = post.find('span', class_='andes-money-amount__fraction').text
                
                # Convert and format the previous price
                price_previous = self.format_to_currency(self.convert_to_float(price_previous))

                # get the current price
                price_current = post.find('span', class_='andes-money-amount andes-money-amount--cents-superscript').text
                # Convert and format the current price
                price_current = self.format_to_currency(self.convert_to_float(price_current))

                # get discount
                discount = post.find('span', class_='andes-money-amount__discount')
                discount = discount.get_text().strip() if discount else "0%"

                # get data and time
                data = datetime.now()
                data_now = data.strftime("%d/%m/%Y %H:%M:%S")
                
                # get seller
                seller = post.find('span', class_='poly-component__seller')
                #seller = seller.get_text().strip()[4:] if seller else "N/A"
                seller = seller.get_text().strip()[4:].capitalize() if seller else "N/A"

                # get installments
                installments = post.find('span', class_='poly-price__installments poly-text-positive')
                if installments:
                    installments = installments.get_text().strip()
                    ad_type = 'Premium'
                else:
                    installments = post.find('span', class_='poly-price__installments poly-text-primary')
                    installments = installments.get_text().strip() if installments else "N/A"
                    ad_type = 'Classic'

                # get the url post
                post_link = post.find("a")["href"]
               
                # get mlb id from url post
                if post_link and "MLB-" in post_link:
                    start_index = post_link.find("MLB-")
                    mlb_code = post_link[start_index:start_index + 14]  # "MLB-" (4 chars) + 10 chars = 14
                elif post_link in post_link:
                    pattern = r"MLB[^#]*"  # MLB seguido de qualquer sequência que não contenha '#'
                    match = re.search(pattern, post_link)
                    mlb_code = match.group(0)
                else:
                    mlb_code = "N/A"

                # get the url image
                try:
                    img_link = post.find("img")["data-src"]
                except:
                    img_link = post.find("img")["src"]
                
                # show the data already scraped
                # print(f"{c}. {title}, {price}, {discount}, {post_link}, {img_link}")

                # save in a dictionary
                post_data = {
                    "mlb": mlb_code,
                    "title": title,
                    "seller": seller,
                    "ad_type": ad_type,
                    "price_previous": price_previous,
                    "price_current": price_current,
                    "discount": discount,
                    "installments": installments,
                    "date": data_now,
                    "post link": post_link,
                    "image link": img_link            
                }
                # save the dictionaries in a list
                self.data.append(post_data)
                c += 1

    def export_to_csv(self):
        # Create the "data" folder if it does not exist
        os.makedirs("data", exist_ok=True)
        
        # Export to a CSV file in UTF-8
        df = pd.DataFrame(self.data)
        df.to_csv(r"data/mercadolibre_scraped_data.csv", sep=";", encoding="utf-8-sig", index=False)
        print("Arquivo CSV exportado com sucesso em UTF-8!")

if __name__ == "__main__":
    s = Scraper()
    s.menu()
    s.scraping()
    s.export_to_csv()
