import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if os.path.abspath(os.path.dirname(__file__)) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from operators.scraper import fetch_article_body, get_chrome_options
from operators.extractor import extract_nominations_with_claude
from operators.flatten import flatten_results
from models.orm_models import Base, Feed, Article, ArticleBody, ExtractedField
from config.feeds import FEEDS
import feedparser
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# --- ENVIRONMENT CONFIGURATION ---
# Use environment variables set by launch_etl.sh script
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

# Validate required environment variables
required_env_vars = {
    "RSS_FEED_ETL_DB_URL": "Database connection string",
    "ANTHROPIC_API_KEY": "Claude API key for extraction",
    "CHROMEDRIVER_PATH": "Path to ChromeDriver executable"
}

def should_process_entry(entry, feed_config):
    """
    Determine if an RSS entry should be processed based on configurable filters.
    
    Args:
        entry: feedparser entry object
        feed_config: feed configuration from config/feeds.py
    
    Returns:
        tuple: (should_process: bool, match_info: dict) 
               match_info contains details about which filter matched
    """
    # If no filters specified, don't process any entries
    filters = feed_config.get("filters", {})
    if not filters:
        return False, {"reason": "no_filters", "filter_type": "none", "matched_value": "none"}
    
    # Get entry attributes safely
    entry_link = getattr(entry, 'link', '').lower()
    entry_title = getattr(entry, 'title', '').lower() 
    entry_summary = getattr(entry, 'summary', '').lower()
    
    # Check link keywords
    link_keywords = filters.get("link_keywords", [])
    for keyword in link_keywords:
        if keyword.lower() in entry_link:
            match_info = {
                "reason": "keyword_match",
                "filter_type": "link_keywords", 
                "matched_keyword": keyword,
                "matched_in": entry.link,
                "all_keywords": link_keywords
            }
            return True, match_info
    
    # Check title keywords  
    title_keywords = filters.get("title_keywords", [])
    for keyword in title_keywords:
        if keyword.lower() in entry_title:
            match_info = {
                "reason": "keyword_match",
                "filter_type": "title_keywords",
                "matched_keyword": keyword,
                "matched_in": entry.title,
                "all_keywords": title_keywords
            }
            return True, match_info
    
    # Check summary keywords
    summary_keywords = filters.get("summary_keywords", [])
    for keyword in summary_keywords:
        if keyword.lower() in entry_summary:
            match_info = {
                "reason": "keyword_match", 
                "filter_type": "summary_keywords",
                "matched_keyword": keyword,
                "matched_in": getattr(entry, 'summary', ''),
                "all_keywords": summary_keywords
            }
            return True, match_info
    
    # Entry doesn't match any filters
    no_match_info = {
        "reason": "no_match",
        "filter_type": "none",
        "checked_filters": list(filters.keys()),
        "entry_link": entry.link,
        "entry_title": entry.title
    }
    return False, no_match_info

def validate_environment():
    """Validate that all required environment variables are set"""
    missing_vars = []
    for var_name, description in required_env_vars.items():
        if not os.getenv(var_name):
            missing_vars.append(f"{var_name} ({description})")
    
    if missing_vars:
        error_msg = f"Missing required environment variables:\n" + "\n".join(f"  - {var}" for var in missing_vars)
        error_msg += f"\n\nRun 'source launch_etl.sh' to set up the environment properly."
        logging.error(error_msg)
        raise EnvironmentError(error_msg)
    
    logging.info("Environment validation successful - all required variables are set")
    logging.info(f"Using ChromeDriver: {CHROMEDRIVER_PATH}")
    logging.info(f"Using database: {os.getenv('RSS_FEED_ETL_DB_URL', 'default')}")

def run_etl():
    # Validate environment before starting ETL
    validate_environment()
    service = Service(executable_path=CHROMEDRIVER_PATH)
    options = get_chrome_options()

    logging.info("Starting ETL process for Department of War RSS feed")
    logging.info(f"Environment sourced from launch_etl.sh - ChromeDriver: {CHROMEDRIVER_PATH}")
    
    DB_CONN_STR = os.getenv("RSS_FEED_ETL_DB_URL")
    if not DB_CONN_STR:
        raise EnvironmentError("RSS_FEED_ETL_DB_URL not set. Run 'source launch_etl.sh' first.")
    
    engine = create_engine(DB_CONN_STR)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    logging.info("Database connection established and tables created if not present.")
    
    # Log configured feeds
    logging.info(f"Processing {len(FEEDS)} configured feed(s) from config/feeds.py")
    for i, feed_config in enumerate(FEEDS, 1):
        logging.info(f"  {i}. {feed_config['name']}")
    
    # Process all configured feeds from config/feeds.py
    total_articles_processed = 0
    for feed_config in FEEDS:
        feed_name = feed_config["name"]
        feed_url = feed_config["url"]
        
        logging.info(f"Processing feed: {feed_name}")
        
        # Get or create feed in database
        feed = session.query(Feed).filter_by(name=feed_name).first()
        if not feed:
            feed = Feed(name=feed_name, url=feed_url)
            session.add(feed)
            session.commit()
            logging.info(f"Feed created: {feed.name} - {feed.url}")
        else:
            logging.info(f"Feed found: {feed.name} - {feed.url}")

        # Parse RSS feed
        parsed = feedparser.parse(feed.url)
        all_entries = parsed.entries
        logging.info(f"Found {len(all_entries)} total entries in RSS feed: {feed_name}")
        
        # First pass: filter entries and get the ones that should be processed
        entries_to_process = []
        filtered_out_count = 0
        for entry in all_entries:
            should_process, match_info = should_process_entry(entry, feed_config)
            if should_process:
                entries_to_process.append((entry, match_info))
            else:
                filtered_out_count += 1
                # Optional: Log filtered out entries (use DEBUG level to avoid noise)
                logging.debug(f"❌ Filtered out: '{entry.title}' | "
                            f"Checked filters: {match_info.get('checked_filters', [])} | "
                            f"Link: {entry.link[:]}...")
        
        total_to_process = len(entries_to_process)
        logging.info(f"After filtering: {total_to_process} entries to process, {filtered_out_count} filtered out")
        processed = 0
        
        # Second pass: process the filtered entries
        for entry, match_info in entries_to_process:
            processed += 1
            # Log detailed filter match information
            if match_info["reason"] == "keyword_match":
                logging.info(f"✅ Processing {processed}/{total_to_process}: '{entry.title}' | "
                           f"Filter: {match_info['filter_type']} | "
                           f"Keyword: '{match_info['matched_keyword']}' | "
                           f"Found in: {match_info['matched_in'][:50]}...")
            else:
                logging.info(f"✅ Processing {processed}/{total_to_process}: '{entry.title}' | "
                           f"Reason: {match_info['reason']}")
            
            # Process the article that matched filters
            article = session.query(Article).filter_by(link=entry.link).first()
            if not article:
                article = Article(
                    feed=feed,
                    title=entry.title,
                    link=entry.link,
                    published=entry.published_parsed and datetime(*entry.published_parsed[:6]) or None,
                    summary=entry.get('summary', ''),
                    inserted_at=datetime.now(timezone.utc)
                )
                session.add(article)
                session.commit()
                logging.info(f"Article created: {entry.title}")
            else:
                # Article exists - update fields in case they changed
                article.title = entry.title
                article.summary = entry.get('summary', '')
                if entry.published_parsed:
                    article.published = datetime(*entry.published_parsed[:6])
                session.commit()
                logging.info(f"Article found and updated: {entry.title}")

            # Check if article is fully processed (has body + extracted fields + flat rows)
            has_body = article.body is not None
            has_extracted_fields = session.query(ExtractedField).filter_by(article=article).first() is not None
            
            if has_body and has_extracted_fields:
                logging.info(f"Article fully processed, skipping: {entry.title} (saves scraping + Claude API costs)")
                continue  # Skip entire processing for this article

            if not article.body:
                body_text = fetch_article_body(entry.link, service, options)
                article_body = ArticleBody(article=article, body_text=body_text)
                session.add(article_body)
                session.commit()
                logging.info(f"Article body scraped and saved for: {entry.title}")
            else:
                body_text = article.body.body_text
                logging.info(f"Article body already exists for: {entry.title}")

            try:
                logging.info(f"Running Claude extraction for: {entry.title}")
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
                # --- FLATTEN NOMINATIONS AND LOG ---
                flatten_input = [{
                    "announcement_title": article.title,
                    "date_published": article.published,
                    "summary": article.summary,
                    "link": article.link,
                    "nominations": nominations
                }]
                flat_rows = flatten_results(flatten_input)
                logging.info(f"Flattened nominations for {entry.title}: {flat_rows}")
                # --- INSERT FLATTENED NOMINATIONS INTO DB ---
                from models.orm_models import FlatRow
                for flat_row in flat_rows:
                    # Upsert logic: update if exists, else insert
                    existing_row = session.query(FlatRow).filter_by(
                        announcement_title=flat_row.get("announcement_title"),
                        name_rank=flat_row.get("name_rank")
                    ).first()
                    if existing_row:
                        existing_row.date_published = flat_row.get("date_published")
                        existing_row.summary = flat_row.get("summary")
                        existing_row.link = flat_row.get("link")
                        existing_row.name = flat_row.get("name")
                        existing_row.rank = flat_row.get("rank")
                        existing_row.location = flat_row.get("location")
                        existing_row.new_assignment = flat_row.get("new_assignment")
                        existing_row.promotion_grade = flat_row.get("promotion_grade")
                        existing_row.current_assignment = flat_row.get("current_assignment")
                        logging.info(f"FlatRow exists and updated: announcement_title='{flat_row.get('announcement_title')}', name_rank='{flat_row.get('name_rank')}' (not inserted)")
                    else:
                        db_row = FlatRow(
                            announcement_title=flat_row.get("announcement_title"),
                            date_published=flat_row.get("date_published"),
                            summary=flat_row.get("summary"),
                            link=flat_row.get("link"),
                            name_rank=flat_row.get("name_rank"),
                            name=flat_row.get("name"),
                            rank=flat_row.get("rank"),
                            location=flat_row.get("location"),
                            new_assignment=flat_row.get("new_assignment"),
                            promotion_grade=flat_row.get("promotion_grade"),
                            current_assignment=flat_row.get("current_assignment"),
                        )
                        session.add(db_row)
                        logging.info(f"FlatRow inserted: announcement_title='{flat_row.get('announcement_title')}', name_rank='{flat_row.get('name_rank')}'")
                session.commit()
                logging.info(f"Extracted {len(nominations)} nominations for: {entry.title}")
            except Exception as e:
                logging.error(f"Claude extraction failed for {entry.title}: {e}")
            session.commit()
        
        logging.info(f"Feed processing completed for {feed_name}. {processed} articles processed.")
        total_articles_processed += processed
    
    logging.info(f"ETL process completed for all configured feeds. Total articles processed: {total_articles_processed}")
    session.close()


default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 9, 19),
    'retries': 1,
    'retry_delay': timedelta(minutes=10)
}


with DAG(
    'war_general_officer_etl',
    default_args=default_args,
    schedule=None,  # Airflow 3.x: use schedule, not schedule_interval
    catchup=False,
    description="ETL for Department of War general officer announcements",
) as dag:

    etl_task = PythonOperator(
        task_id='run_war_etl',
        python_callable=run_etl,
    )


if __name__ == "__main__":
    print("=== Running War ETL DAG Directly ===")
    print("Note: Ensure environment is set up by running 'source launch_etl.sh' first")
    print("Required environment variables: RSS_FEED_ETL_DB_URL, ANTHROPIC_API_KEY, CHROMEDRIVER_PATH")
    print("")
    try:
        run_etl()
        print("=== ETL process completed successfully ===")
    except EnvironmentError as e:
        print(f"❌ Environment Error: {e}")
        print("💡 Solution: Run 'source launch_etl.sh' to set up the environment")
        exit(1)
    except Exception as e:
        print(f"❌ ETL Error: {e}")
        exit(1)