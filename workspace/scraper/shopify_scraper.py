import requests
from bs4 import BeautifulSoup
import sys
import json

def scrape_shopify_product(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch the URL: {e}"}

    soup = BeautifulSoup(response.text, 'html.parser')

    product_data = {}

    # Extract Product Title
    title_tag = soup.find('meta', property='og:title')
    product_data['title'] = title_tag['content'] if title_tag else 'N/A'

    # Extract Product Price
    price_tag = soup.find('meta', property='og:price:amount')
    product_data['price'] = price_tag['content'] if price_tag else 'N/A'

    # Extract Product Image
    image_tag = soup.find('meta', property='og:image')
    product_data['image_url'] = image_tag['content'] if image_tag else 'N/A'

    # Extract Product Description (often found in a meta tag or a specific div)
    description_tag = soup.find('meta', property='og:description')
    product_data['description'] = description_tag['content'] if description_tag else 'N/A'

    return product_data

if __name__ == "__main__":
    if len(sys.argv) > 1:
        shopify_url = sys.argv[1]
        scraped_data = scrape_shopify_product(shopify_url)
        print(json.dumps(scraped_data, indent=4))
    else:
        print("Usage: python shopify_scraper.py <shopify_product_url>")
