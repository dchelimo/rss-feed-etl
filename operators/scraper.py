"""
Scrape general/flag officer announcements from RSS feed and article pages.
Extracts structured nomination data and writes to CSV.
"""

# --- IMPORT PATH SETUP ---
import sys
import os
# Add project root to path to support running from different locations
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- ETL SETUP ---
import feedparser
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from models.orm_models import Base, Feed, Article, ArticleBody, ExtractedField
# Import Claude extraction function
from operators.extractor import extract_nominations_with_claude
from config.feeds import FEEDS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import os


# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

CHROMEDRIVER_PATH = "/usr/bin/chromedriver"  # Update for Windows if needed
WAIT_TIMEOUT = 15
DB_URL = os.getenv("RSS_FEED_ETL_DB_URL", "postgresql://user:pass@localhost:5432/rss_feed_etl")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

def get_chrome_options():
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    return opts

def fetch_article_body(link: str, service: Service, options: Options) -> str:
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

def etl_feeds():
    logging.info("Starting ETL process for configured RSS feeds")
    engine = create_engine(DB_URL, future=True)
    Base.metadata.create_all(engine)
    service = Service(executable_path=CHROMEDRIVER_PATH)
    options = get_chrome_options()

    with Session(engine, future=True) as session:
        logging.info("Database connection established and tables created if not present.")
        for feed_info in FEEDS:
            stmt_feed = select(Feed).filter_by(name=feed_info['name'])
            feed = session.execute(stmt_feed).scalar_one_or_none()
            if not feed:
                feed = Feed(name=feed_info['name'], url=feed_info['url'])
                session.add(feed)
                session.commit()
                logging.info(f"Feed created: {feed.name} - {feed.url}")
            else:
                logging.info(f"Feed found: {feed.name} - {feed.url}")

            parsed = feedparser.parse(feed.url)
            total = len(parsed.entries)
            processed = 0
            logging.info(f"Found {total} entries in RSS feed '{feed.name}'.")
            for entry in parsed.entries:
                processed += 1
                logging.info(f"Processing {processed} of {total}: {entry.title}")
                stmt_article = select(Article).filter_by(link=entry.link)
                article = session.execute(stmt_article).scalar_one_or_none()
                if not article:
                    published = None
                    if 'published_parsed' in entry:
                        published = datetime(*entry.published_parsed[:6])
                    article = Article(
                        feed=feed,
                        title=entry.title,
                        link=entry.link,
                        published=published,
                        summary=entry.get('summary', ''),
                        inserted_at=datetime.now(timezone.utc),
                    )
                    session.add(article)
                    session.commit()
                    logging.info(f"Article created: {entry.title}")
                else:
                    logging.info(f"Article found: {entry.title}")
                # --- Uniqueness check before scraping and Claude extraction ---
                required_keys = ["name_rank", "promotion_grade", "new_assignment", "current_assignment", "location"]
                existing_fields = session.query(ExtractedField).filter_by(article=article).all()
                existing_keys = set(ef.field_name for ef in existing_fields)
                if all(key in existing_keys for key in required_keys):
                    logging.info(f"Article '{entry.title}' already has all unique ExtractedField rows. Skipping scraping and Claude extraction.")
                    continue
                # --- Scrape body if needed ---
                if not article.body:
                    body_text = fetch_article_body(article.link, service, options)
                    article_body = ArticleBody(article=article, body_text=body_text)
                    session.add(article_body)
                    session.commit()
                    logging.info(f"Article body scraped and saved for: {entry.title}")
                else:
                    body_text = article.body.body_text
                    logging.info(f"Article body already exists for: {entry.title}")

                # Claude extraction and storing as ExtractedField
                try:
                    nominations = extract_nominations_with_claude(body_text)
                    for nom in nominations:
                        for key, value in nom.items():
                            existing_ef = session.query(ExtractedField).filter_by(article=article, field_name=key).first()
                            if existing_ef:
                                existing_ef.field_value = value
                            else:
                                ef = ExtractedField(article=article, field_name=key, field_value=value)
                                session.add(ef)
                    session.commit()
                    logging.info(f"Extracted {len(nominations)} nominations for: {entry.title}")
                except Exception as e:
                    logging.error(f"Claude extraction failed for {entry.title}: {e}")
        logging.info("ETL process completed for all feeds.")

# Test DB connection before running ETL
try:
    engine = create_engine(DB_URL)
    conn = engine.connect()
    print("Database connection successful!")
    conn.close()
except Exception as e:
    print(f"Database connection failed: {e}")
    exit(1)

if __name__ == "__main__":
    etl_feeds()
