import os
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import time

class LinkScraper:
    def __init__(self, input_file, output_file):
        self.input_file = input_file
        self.output_file = output_file
        self.data = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    def read_csv(self):
        """Lê o arquivo CSV e obtém os links da coluna 'post link'."""
        try:
            df = pd.read_csv(self.input_file, sep=";")
            self.links = df['post link'].dropna().tolist()
            print(f"Lidos {len(self.links)} links do arquivo {self.input_file}.")
        except FileNotFoundError:
            print(f"Arquivo {self.input_file} não encontrado.")
            self.links = []
        except Exception as e:
            print(f"Erro ao ler o arquivo CSV: {e}")
            self.links = []

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
    
    def clean_seller(self, seller):
        """Remove prefixos como 'Vendido por' e 'Loja oficial'."""
        if seller and seller != "N/A":
            # Remover 'Vendido por' ou 'Loja oficial' e garantir que o espaço depois do prefixo seja também removido
            return re.sub(r"^(Vendido por|Loja oficial)\s*", "", seller, flags=re.IGNORECASE).strip()
        return seller

    def clean_seller_sales(self, seller_sales):
        """Remove prefixos como 'Mercadolíder | ' de seller_sales."""
        if seller_sales and seller_sales != "N/A":
            return re.sub(r"^Mercadolíder\s\|\s", "", seller_sales, flags=re.IGNORECASE).strip()
        return seller_sales

    def scrape_link(self, url):
        """Acessa a URL e extrai informações relevantes."""
        try:
            # Definindo os headers com o User-Agent
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            
            # Fazendo a requisição com o header personalizado
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            #response = requests.get(url, timeout=10)
            #response.raise_for_status()
            #soup = BeautifulSoup(response.text, 'html.parser')

            # Título
            title = soup.find('h1', class_='ui-pdp-title')
            title = title.get_text().strip().capitalize() if title else "N/A"

            # Vendedor
            #seller = soup.find('button', class_='ui-pdp-seller__link-trigger-button non-selectable')
            seller  = soup.find('div', class_='ui-seller-data-header__title-container')
            seller = seller.get_text().strip().capitalize() if seller else "N/A"
            seller = self.clean_seller(seller)

            # Vendedor - Vendas realizadas
            #seller_sales = soup.find('div', class_='ui-pdp-seller__header__info-container__subtitle-one-line')
            seller_sales = soup.find('p', class_='ui-pdp-color--BLACK ui-pdp-size--XSMALL ui-pdp-family--SEMIBOLD ui-seller-data-status__info-title')
            seller_sales = seller_sales.get_text().strip().capitalize() if seller_sales else "N/A"
            seller_sales = self.clean_seller_sales(seller_sales)

            # Preço anterior
            price_previous = soup.find('s', class_='andes-money-amount ui-pdp-price__part ui-pdp-price__original-value andes-money-amount--previous andes-money-amount--cents-superscript andes-money-amount--compact')
            if price_previous:
                price_previous = price_previous.get_text().strip()
            else:
                price_previous = soup.find('span', class_='andes-money-amount__fraction').get_text().strip() if price_previous else "N/A"
            
            price_previous = self.format_to_currency(self.convert_to_float(price_previous))

            # Preco atual
            price_current = soup.find('span', class_='andes-money-amount ui-pdp-price__part andes-money-amount--cents-superscript andes-money-amount--compact')
            if price_current:
                price_current = price_current.get_text().strip()
                price_current = self.format_to_currency(self.convert_to_float(price_current))
            else:
                price_current = "NA"

            # Desconto
            discount = soup.find('span', class_='andes-money-amount__discount')
            discount = discount.get_text().strip() if discount else "0%"

            # Parcelamento e tipo de anúncio
            # Inicializa as variáveis com valores padrão
            installments = "N/A"
            ad_type = "N/A"

            # Verifica a presença do texto sem juros no parcelamento
            installments_element = soup.find('div', class_='ui-pdp-price__subtitles')
            if installments_element:
                installments = installments_element.get_text().strip()
                if installments and "sem juros" in installments.lower():
                    installments = installments_element.get_text().strip()
                    ad_type = 'Premium'
                else:
                    installments = installments_element.get_text().strip()
                    ad_type = 'Classic'

            # Quantidade disponível
            qtd_available = None

            # Verificar se há uma quantidade disponível explícita (>1)
            qtd_available_element = soup.find('span', class_='ui-pdp-buybox__quantity__available')
            if qtd_available_element:
                qtd_available = qtd_available_element.get_text().strip()

            # Verificar para quantidade = 1
            if not qtd_available:
                qtd_available_element = soup.find('div', class_='ui-pdp-buybox__quantity')
                if qtd_available_element:
                    qtd_available = qtd_available_element.get_text().strip()

            # Verificar se o anúncio está pausado (quantidade = 0)
            if not qtd_available:
                ad_paused_element = soup.find('div', class_='ui-vip-shipping-message__text')
                if ad_paused_element and "Anúncio pausado" in ad_paused_element.get_text():
                    qtd_available = "Anúncio pausado"

            # Caso nenhuma das condições anteriores seja satisfeita
            if not qtd_available:
                qtd_available = "N/A"

            # Remover parênteses, se existirem
            qtd_available = qtd_available.replace("(", "").replace(")", "").strip() if qtd_available != "N/A" else "N/A"

            # Armazenar os dados extraídos
            return {
                "title": title,
                "seller": seller,
                "seller_sales": seller_sales,
                "ad_type": ad_type,
                "price_previous": price_previous,
                "price_current": price_current,
                "discount": discount,
                "installments": installments,
                "qtd_available": qtd_available,
                "url": url,
                "scraped_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar {url}: {e}")
            return {
                "url": url,
                "title": "N/A",
                "price_previous": "N/A",
                "price_current": "N/A",
                "seller": "N/A",
                "seller_sales": "N/A",
                "qtd_available": "N/A", 
                "scraped_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }

    def scrape_link_parallel(self, links):
        """Realiza o scraping de links em paralelo."""
        with ThreadPoolExecutor(max_workers=5) as executor:  # Ajuste max_workers conforme necessário
            results = list(executor.map(self.scrape_link, links))
            self.data.extend(results)

    def scrape_links(self):
        """Percorre todos os links e realiza o scraping com pausa entre as requisições."""
        if not self.links:
            print("Nenhum link para processar.")
            return

        for i, link in enumerate(self.links, start=1):
            print(f"Processando link {i}/{len(self.links)}: {link}")
            result = self.scrape_link(link)
            self.data.append(result)
            time.sleep(2)  # Pausa para evitar bloqueios

    def export_to_csv(self):
        """Exporta os dados extraídos para um novo arquivo CSV."""
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        df = pd.DataFrame(self.data)
        df.to_csv(self.output_file, sep=";", encoding="utf-8-sig", index=False)
        print(f"Dados exportados para {self.output_file} com sucesso!")

if __name__ == "__main__":
    # Configuração dos arquivos
    input_csv = "data/ml_links.csv"  # Arquivo de entrada
    output_csv = "data/extracted_data.csv"  # Arquivo de saída

    # Inicialização do scraper
    scraper = LinkScraper(input_csv, output_csv)

    # Fluxo principal
    scraper.read_csv()
    scraper.scrape_links()
    #scraper.scrape_link_parallel(scraper.links)
    scraper.export_to_csv()
