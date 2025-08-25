import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from urllib.parse import urljoin, urlparse
import logging
import csv
import json
from datetime import datetime
import re
from typing import List, Dict, Any, Optional, Union
import sys
import threading
import os

class WebScraper:
    def __init__(self, delay_range=(1, 3), timeout=10, max_retries=3, proxies=None, log_file=None):
        """
        Initialize the web scraper with configurable parameters
        
        Args:
            delay_range (tuple): Range of seconds to wait between requests
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retries for failed requests
            proxies (dict): Proxy configuration for requests
            log_file (str): Path to log file
        """
        self.delay_range = delay_range
        self.timeout = timeout
        self.max_retries = max_retries
        self.proxies = proxies
        self.scraping = False
        self.current_page = 0
        self.total_items = 0
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)
        
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
    
    def get_random_delay(self) -> float:
        """Generate a random delay within the specified range"""
        return random.uniform(*self.delay_range)
    
    def is_valid_url(self, url: str) -> bool:
        """
        Check if a URL is valid
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if URL is valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False
            # Check if scheme is http or https
            return parsed.scheme in ['http', 'https']
        except:
            return False
    
    def make_absolute_url(self, base_url: str, relative_url: str) -> str:
        """
        Convert relative URL to absolute URL
        
        Args:
            base_url (str): Base URL
            relative_url (str): Relative URL to convert
            
        Returns:
            str: Absolute URL
        """
        if not relative_url:
            return ""
        
        # If URL is already absolute, return it
        if self.is_valid_url(relative_url):
            return relative_url
        
        # Convert relative URL to absolute
        try:
            return urljoin(base_url, relative_url)
        except:
            return ""
    
    def get_page_content(self, url: str, params: Optional[Dict] = None) -> Optional[BeautifulSoup]:
        """
        Retrieve content from a URL with retry logic
        
        Args:
            url (str): URL to scrape
            params (dict): Query parameters for the request
            
        Returns:
            BeautifulSoup object or None if failed
        """
        if not self.is_valid_url(url):
            self.logger.error(f"Invalid URL: {url}")
            return None
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Attempt {attempt + 1} to retrieve {url}")
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.timeout,
                    proxies=self.proxies
                )
                response.raise_for_status()
                
                # Detect encoding if not specified
                if response.encoding is None:
                    response.encoding = response.apparent_encoding
                
                # Respect robots.txt and rate limiting
                time.sleep(self.get_random_delay())
                
                return BeautifulSoup(response.content, 'html.parser')
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Failed to retrieve {url} after {self.max_retries} attempts")
                    return None
                time.sleep(self.get_random_delay() * 2)  # Longer delay after failure
    
    def clean_data(self, data: List[Dict], cleaning_rules: Optional[Dict] = None) -> List[Dict]:
        """
        Clean scraped data based on rules
        
        Args:
            data (list): Scraped data
            cleaning_rules (dict): Rules for cleaning each field
            
        Returns:
            List of cleaned data
        """
        if not cleaning_rules:
            return data
            
        cleaned_data = []
        for item in data:
            cleaned_item = {}
            for key, value in item.items():
                if key in cleaning_rules and value is not None:
                    rule = cleaning_rules[key]
                    # Remove extra whitespace
                    if rule.get('remove_whitespace', False):
                        value = ' '.join(str(value).split())
                    # Remove currency symbols
                    if rule.get('remove_currency', False):
                        value = re.sub(r'[^\d.,]', '', str(value))
                    # Convert to float
                    if rule.get('convert_to_float', False):
                        try:
                            value = float(str(value).replace(',', ''))
                        except ValueError:
                            value = None
                    # Convert to integer
                    if rule.get('convert_to_int', False):
                        try:
                            value = int(float(str(value).replace(',', '')))
                        except ValueError:
                            value = None
                cleaned_item[key] = value
            cleaned_data.append(cleaned_item)
        
        return cleaned_data
    
    def display_progress(self):
        """Display live progress information in the console"""
        while self.scraping:
            sys.stdout.write(f"\rScraping page {self.current_page}, Items collected: {self.total_items}")
            sys.stdout.flush()
            time.sleep(0.1)
    
    def scrape_website(self, url: str, selectors: Dict, pagination: Optional[Dict] = None, 
                      limit_pages: Optional[int] = None, cleaning_rules: Optional[Dict] = None) -> List[Dict]:
        """
        Scrape data from a website based on CSS selectors
        
        Args:
            url (str): Base URL to scrape
            selectors (dict): Dictionary of CSS selectors for data extraction
            pagination (dict): Pagination configuration if applicable
            limit_pages (int): Maximum number of pages to scrape
            cleaning_rules (dict): Rules for cleaning the scraped data
            
        Returns:
            List of dictionaries containing scraped data
        """
        if not self.is_valid_url(url):
            self.logger.error(f"Invalid URL: {url}")
            return []
        
        # Start progress display
        self.scraping = True
        progress_thread = threading.Thread(target=self.display_progress)
        progress_thread.daemon = True
        progress_thread.start()
        
        data = []
        page_num = 1
        has_next_page = True
        
        while has_next_page and (limit_pages is None or page_num <= limit_pages):
            self.current_page = page_num
            self.logger.info(f"Scraping page {page_num}: {url}")
            
            # Handle pagination
            if pagination and page_num > 1:
                page_url = pagination.get('url_pattern', '').format(page=page_num)
                if page_url:
                    params = None
                else:
                    params = pagination.get('params', {})
                    params[pagination.get('page_param', 'page')] = page_num
            else:
                params = None
                page_url = url
            
            full_url = urljoin(url, page_url) if page_url else url
            soup = self.get_page_content(full_url, params)
            
            if not soup:
                break
            
            # Extract data using selectors
            items = soup.select(selectors.get('item_selector', ''))
            
            if not items:
                self.logger.warning(f"No items found on page {page_num}")
                break
            
            for item in items:
                item_data = {}
                for key, selector in selectors.items():
                    if key == 'item_selector':
                        continue
                    
                    # Handle different selector types
                    if isinstance(selector, dict):
                        # Complex selector with attributes
                        element = item.select_one(selector.get('selector', ''))
                        if element:
                            if selector.get('attribute'):
                                value = element.get(selector['attribute'], '').strip()
                                # Make URLs absolute if they're links
                                if selector.get('attribute') in ['href', 'src'] and value:
                                    value = self.make_absolute_url(url, value)
                            else:
                                value = element.get_text().strip()
                        else:
                            value = None
                    else:
                        # Simple CSS selector
                        element = item.select_one(selector)
                        value = element.get_text().strip() if element else None
                    
                    item_data[key] = value
                
                data.append(item_data)
                self.total_items = len(data)
            
            # Check for next page
            if pagination:
                next_selector = pagination.get('next_selector')
                if next_selector:
                    next_button = soup.select_one(next_selector)
                    has_next_page = bool(next_button) and (limit_pages is None or page_num < limit_pages)
                else:
                    # Assume numeric pagination
                    has_next_page = len(items) > 0 and (limit_pages is None or page_num < limit_pages)
            else:
                has_next_page = False
            
            page_num += 1
        
        # Stop progress display
        self.scraping = False
        time.sleep(0.2)  # Allow progress thread to finish
        print()  # New line after progress display
        
        self.logger.info(f"Scraped {len(data)} items from {page_num - 1} pages")
        
        # Clean the data if rules are provided
        if cleaning_rules:
            data = self.clean_data(data, cleaning_rules)
        
        return data
    
    def export_data(self, data: List[Dict], filename: str, format: str = 'csv'):
        """
        Export scraped data to a file
        
        Args:
            data (list): Data to export
            filename (str): Output filename
            format (str): Export format ('csv', 'json', 'excel')
        """
        if not data:
            self.logger.warning("No data to export")
            return
        
        try:
            if format == 'csv':
                with open(f"{filename}.csv", 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            
            elif format == 'json':
                with open(f"{filename}.json", 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            elif format == 'excel':
                df = pd.DataFrame(data)
                df.to_excel(f"{filename}.xlsx", index=False)
            
            self.logger.info(f"Data exported to {filename}.{format}")
            
        except Exception as e:
            self.logger.error(f"Failed to export data: {e}")
    
    def check_robots_txt(self, url: str) -> bool:
        """
        Check if scraping is allowed by robots.txt
        
        Args:
            url (str): URL to check
            
        Returns:
            bool: True if scraping is allowed, False otherwise
        """
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            response = self.session.get(robots_url, timeout=self.timeout)
            
            if response.status_code == 200:
                robots_content = response.text
                # Simple check - in production, use a proper robots.txt parser
                if "User-agent: *" in robots_content and "Disallow: /" in robots_content:
                    return False
            return True
        except:
            return True  # Proceed if robots.txt can't be accessed

def get_user_input():
    """Get website URL and configuration from user input"""
    print("=== Web Scraper ===")
    print("Enter the website URL you want to scrape:")
    url = input("URL: ").strip()
    
    if not url:
        print("No URL provided. Using default example.")
        return None
    
    print("\nConfigure scraping (press Enter for defaults):")
    
    # Get item selector
    item_selector = input("Item CSS selector (e.g., 'article.product_pod'): ").strip()
    if not item_selector:
        print("Using default item selector")
        item_selector = "article.product_pod"
    
    # Get field selectors
    selectors = {'item_selector': item_selector}
    print("\nEnter field selectors (leave blank when done):")
    
    while True:
        field_name = input("Field name (e.g., 'title', 'price'): ").strip()
        if not field_name:
            break
        
        field_selector = input(f"CSS selector for {field_name}: ").strip()
        if field_selector:
            selectors[field_name] = field_selector
    
    # If no fields were added, use defaults
    if len(selectors) == 1:  # Only item_selector
        selectors.update({
            'title': 'h3 a',
            'price': 'p.price_color',
            'rating': 'p.star-rating',
            'link': {'selector': 'h3 a', 'attribute': 'href'}
        })
        print("Using default field selectors")
    
    # Pagination
    pagination = None
    has_pagination = input("\nDoes the site have pagination? (y/n): ").strip().lower()
    if has_pagination == 'y':
        pagination_type = input("Pagination type: (1) Next button, (2) URL pattern: ").strip()
        if pagination_type == '1':
            next_selector = input("CSS selector for next button: ").strip()
            pagination = {'next_selector': next_selector}
        elif pagination_type == '2':
            url_pattern = input("URL pattern (use {page} for page number): ").strip()
            pagination = {'url_pattern': url_pattern}
    
    # Page limit
    limit_pages = input("\nMaximum pages to scrape (Enter for no limit): ").strip()
    limit_pages = int(limit_pages) if limit_pages.isdigit() else None
    
    return {
        'url': url,
        'selectors': selectors,
        'pagination': pagination,
        'limit_pages': limit_pages
    }

def print_banner():
    banner = r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██╗    ██╗███████╗██████╗ ███████╗██████╗   ██████╗ ██████╗ ██████╗        ║
║   ██║    ██║██╔════╝██╔══██╗██╔════╝██╔══██╗ ██╔═══██╗██╔══██╗██╔══██╗       ║
║   ██║ █╗ ██║█████╗  ██████╔╝█████╗  ██████╔╝ ██║   ██║██████╔╝██║  ██║       ║
║   ██║███╗██║██╔══╝  ██╔══██╗██╔══╝  ██╔══██╗ ██║   ██║██╔═══╝ ██║  ██║       ║
║   ╚███╔███╔╝███████╗██████╔╝███████╗██║  ██║ ╚██████╔╝██║     █████╔╝       ║
║    ╚══╝╚══╝ ╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝  ╚═════╝ ╚═╝     ╚════╝        ║
║                                                                              ║
║                              ░█▀▀█ ░█▀▀█ ░█▀▄▀█                              ║
║                              ░█─── ░█▄▄█ ░█░█░█                              ║
║                              ░█▄▄█ ░█─── ░█──░█                              ║
║                                                                              ║
║                          Web Scraper — Python | tlstanjim                    ║
║                        mail: tls.tanjim@gmail.com | v2.1.0                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

# Example usage
if __name__ == "__main__":
    # Print ASCII banner
    print_banner()
    print("Version: 2.1.0 | Features: Pagination, Data Cleaning, Multiple Export Formats")
    print("=" * 80)
    print()
    
    # Get user input or use default configuration
    config = get_user_input()
    
    if config is None:
        # Use default configuration for books.toscrape.com
        config = {
            'url': 'https://books.toscrape.com/',
            'selectors': {
                'item_selector': 'article.product_pod',
                'title': 'h3 a',
                'price': 'p.price_color',
                'rating': 'p.star-rating',
                'link': {'selector': 'h3 a', 'attribute': 'href'},
            },
            'pagination': {
                'next_selector': 'li.next a'
            },
            'limit_pages': 2
        }
        cleaning_rules = {
            'price': {'remove_currency': True, 'convert_to_float': True},
            'title': {'remove_whitespace': True},
            'rating': {'remove_whitespace': True}
        }
    else:
        cleaning_rules = None
    
    # Initialize scraper
    scraper = WebScraper(
        delay_range=(1, 2), 
        max_retries=2,
        log_file="scraper.log"
    )
    
    # Check robots.txt first
    if not scraper.check_robots_txt(config['url']):
        scraper.logger.error("Scraping is disallowed by robots.txt")
    else:
        print(f"\nStarting scrape of {config['url']}")
        print("Press Ctrl+C to stop scraping at any time\n")
        
        try:
            # Scrape the website
            scraped_data = scraper.scrape_website(
                url=config['url'],
                selectors=config['selectors'],
                pagination=config.get('pagination'),
                limit_pages=config.get('limit_pages'),
                cleaning_rules=cleaning_rules
            )
            
            # Export the data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain = urlparse(config['url']).netloc.replace('.', '_')
            filename = f"{domain}_data_{timestamp}"
            
            scraper.export_data(scraped_data, filename, format='csv')
            scraper.export_data(scraped_data, filename, format='json')
            
            # Display summary
            print(f"\nScraping completed!")
            print(f"Total items: {len(scraped_data)}")
            print(f"Data saved to: {filename}.csv and {filename}.json")
            
            # Display first few results
            if scraped_data:
                print(f"\nFirst {min(3, len(scraped_data))} items:")
                for i, item in enumerate(scraped_data[:3]):
                    print(f"{i+1}. {item}")
                    print()
            
        except KeyboardInterrupt:
            print("\n\nScraping interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            scraper.logger.error(f"Scraping failed: {e}")