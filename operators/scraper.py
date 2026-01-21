"""
Web scraping module for RSS feed articles.
Provides functions to scrape article content using Selenium.
"""

import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

WAIT_TIMEOUT = 15

def get_chrome_options():
    """Configure Chrome options for headless browsing"""
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    return opts

def fetch_article_body(link: str, service: Service, options: Options) -> str:
    """
    Fetch article body content from a URL using Selenium.

    Args:
        link: URL of the article to scrape
        service: Selenium Service instance with ChromeDriver path
        options: Chrome options for the webdriver

    Returns:
        str: Extracted article body text
    """
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(link)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "body"))
            )
        except Exception:
            logging.warning(f"Timeout waiting for body content at {link}")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        body_div = soup.find("div", class_="body")
        return body_div.get_text(separator="\n", strip=True) if body_div else "Body content not found"
    except Exception as e:
        logging.error(f"Error fetching body for {link}: {e}")
        return f"Error fetching body: {e}"
    finally:
        driver.quit()
