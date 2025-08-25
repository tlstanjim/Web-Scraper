# Web Scraper Project

A powerful and configurable web scraping tool built with Python that can extract data from websites with pagination support, data cleaning, and multiple export formats.

## Features

- **Configurable scraping**: Custom CSS selectors for data extraction
- **Pagination support**: Handles both "next button" and URL pattern pagination
- **Data cleaning**: Rules for whitespace removal, currency conversion, etc.
- **Multiple export formats**: CSV, JSON, and Excel
- **Respectful scraping**: Random delays between requests and robots.txt checking
- **Progress tracking**: Real-time progress display during scraping
- **Robust error handling**: Retry mechanism for failed requests
- **User-friendly interface**: Interactive input or predefined configurations

## Installation

1. Clone the repository:
```bash
git clone https://github.com/tlstanjim/Web-Scraper.git
cd web-scraper
```

## Usage

### Basic Usage

Run the scraper with interactive mode:
```bash
python scraper.py
```

The script will prompt you for:
- Website URL to scrape
- CSS selectors for items and fields
- Pagination configuration (if applicable)
- Page limit

### Example Configuration for books.toscrape.com

The script includes a default configuration for scraping [books.toscrape.com](https://books.toscrape.com/) that extracts:
- Book titles
- Prices
- Ratings
- Links

### Advanced Usage

You can also import the WebScraper class in your own Python scripts:

```python
from scraper import WebScraper

# Initialize scraper
scraper = WebScraper(delay_range=(1, 3), max_retries=3)

# Define selectors
selectors = {
    'item_selector': 'article.product_pod',
    'title': 'h3 a',
    'price': 'p.price_color',
    'rating': 'p.star-rating',
    'link': {'selector': 'h3 a', 'attribute': 'href'},
}

# Define cleaning rules
cleaning_rules = {
    'price': {'remove_currency': True, 'convert_to_float': True},
    'title': {'remove_whitespace': True}
}

# Scrape data
data = scraper.scrape_website(
    url='https://books.toscrape.com/',
    selectors=selectors,
    pagination={'next_selector': 'li.next a'},
    limit_pages=5,
    cleaning_rules=cleaning_rules
)

# Export data
scraper.export_data(data, 'books_data', format='csv')
```

## Configuration Options

### WebScraper Parameters

- `delay_range`: Tuple of min/max seconds between requests (default: (1, 3))
- `timeout`: Request timeout in seconds (default: 10)
- `max_retries`: Maximum retry attempts for failed requests (default: 3)
- `proxies`: Proxy configuration for requests (default: None)
- `log_file`: Path to log file (default: None)

### Selector Format

Selectors can be simple CSS selectors or complex dictionaries:

```python
# Simple selector (extracts text)
'price': 'p.price_color'

# Complex selector (extracts attribute)
'link': {'selector': 'h3 a', 'attribute': 'href'}
```

### Cleaning Rules

Available cleaning options:
- `remove_whitespace`: Remove extra whitespace
- `remove_currency`: Remove currency symbols from prices
- `convert_to_float`: Convert values to float
- `convert_to_int`: Convert values to integer

## Output Formats

The scraper supports three output formats:
1. **CSV**: Comma-separated values (default)
2. **JSON**: JavaScript Object Notation
3. **Excel**: Microsoft Excel format (.xlsx)

## Ethical Scraping

This tool includes features to practice ethical web scraping:
- Respects robots.txt directives
- Implements random delays between requests
- Identifies with a proper User-Agent string
- Provides configuration to limit request rate

## Requirements

- Python 3.6+
- requests
- beautifulsoup4
- pandas
- openpyxl (for Excel export)

Install all requirements with:
```bash
pip install requests beautifulsoup4 pandas openpyxl
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is intended for educational and legitimate purposes only. Always:
- Check a website's terms of service before scraping
- Respect robots.txt directives
- Don't overwhelm servers with excessive requests
- Use appropriate delays between requests

## Support

If you have any questions or issues, please open an issue on GitHub or contact tls.tanjim@gmail.com.

---

**Note**: Web scraping may be against the terms of service of some websites. Always ensure you have permission to scrape a website and use this tool responsibly.
