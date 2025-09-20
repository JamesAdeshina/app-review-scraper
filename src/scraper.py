"""
scraper.py
----------
Professional app review scraper with:
- Logging
- Progress bars
- Error handling
- Apple Store fallback
"""

import logging
from datetime import datetime
from typing import Optional
import pandas as pd
from google_play_scraper import Sort, reviews
from tqdm import tqdm
import requests


# ---------------------------
# Logging Setup
# ---------------------------
def setup_logger(log_file: str = "scraper.log") -> logging.Logger:
    """Configure logger with both console and file handlers."""
    logger = logging.getLogger("AppReviewScraper")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if function is called multiple times
    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File handler (use project root)
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        log_path = project_root / "logs" / log_file
        log_path.parent.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_path)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


logger = setup_logger()


# ---------------------------
# Google Play Scraper
# ---------------------------
def fetch_google_play_reviews(
        app_id: str, count: int = 100, lang: str = "en", country: str = "us"
) -> Optional[pd.DataFrame]:
    """
    Fetch reviews from Google Play Store.

    Args:
        app_id (str): App package name (e.g., 'com.whatsapp')
        count (int): Number of reviews to fetch
        lang (str): Language code (default 'en')
        country (str): Country code (default 'us')

    Returns:
        Optional[pd.DataFrame]: Reviews DataFrame or None if error
    """
    logger.info(f"Starting Google Play scrape for {app_id}, {count} reviews...")
    start_time = datetime.now()

    try:
        # Fetch reviews
        with tqdm(total=count, desc="Google Play Reviews", unit="reviews") as pbar:
            result, _ = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=count,
            )
            pbar.update(len(result))

        if not result:
            logger.warning("No reviews returned from Google Play")
            return None

        df = pd.DataFrame(result)

        # Select relevant columns
        available_cols = ["reviewId", "userName", "content", "score", "at", "replyContent"]
        existing_cols = [col for col in available_cols if col in df.columns]
        df = df[existing_cols] if existing_cols else df

        logger.info(
            f"Completed Google Play scrape in {datetime.now() - start_time} — {len(df)} reviews fetched."
        )
        return df

    except Exception as e:
        logger.error(f"Error scraping Google Play reviews: {e}")
        return None


# ---------------------------
# Apple App Store Scraper
# ---------------------------
def fetch_app_store_reviews(
        app_name: str,
        app_id: int,
        country: str = "us",
        count: int = 100,
) -> Optional[pd.DataFrame]:
    """
    Fetch reviews from Apple App Store with fallback to RSS feed.

    Args:
        app_name (str): App name (e.g., 'whatsapp-messenger')
        app_id (int): App ID (e.g., 310633997 for WhatsApp)
        country (str): Country code (default 'us')
        count (int): Number of reviews

    Returns:
        Optional[pd.DataFrame]: Reviews DataFrame or None if error
    """
    logger.info(f"Starting App Store scrape for {app_name} ({app_id}), {count} reviews...")
    start_time = datetime.now()

    # Try primary method first (app_store_scraper)
    try:
        from app_store_scraper import AppStore
        app = AppStore(country=country, app_name=app_name, app_id=app_id)

        with tqdm(total=count, desc="App Store Reviews", unit="reviews") as pbar:
            app.review(how_many=count)

        if app.reviews and len(app.reviews) > 0:
            df = pd.DataFrame(app.reviews)
            logger.info(f"✅ Primary method: {len(df)} reviews fetched")
            return _process_app_store_df(df, start_time)
        else:
            logger.warning("⚠️ Primary method returned no reviews, trying fallback...")

    except Exception as e:
        logger.warning(f"⚠️ Primary method failed: {e}, trying fallback...")

    # Fallback: Direct RSS feed
    return _fetch_app_store_rss(app_id, app_name, country, count, start_time)


def _fetch_app_store_rss(app_id: int, app_name: str, country: str, count: int, start_time: datetime) -> Optional[
    pd.DataFrame]:
    """Proven fallback method using Apple's RSS feed (from test.py)."""
    try:
        logger.info("🌐 Using proven RSS feed fallback (from test.py method)...")

        # Exact URL format from your working test.py
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Check if reviews exist in the feed
        if 'feed' not in data or 'entry' not in data['feed']:
            logger.warning("No 'feed/entry' found in RSS response")
            return None

        reviews_data = data['feed']['entry']

        if not reviews_data:
            logger.warning("No reviews found in RSS feed")
            return None

        # Use exact processing from your working test.py
        processed_reviews = []
        for review in reviews_data[:count]:  # Limit to requested count
            try:
                processed_reviews.append({
                    'id': review.get('id', {}).get('label', f"rss_{len(processed_reviews)}"),
                    'userName': review.get('author', {}).get('name', {}).get('label', 'Unknown'),
                    'review': review.get('content', {}).get('label', ''),
                    'rating': int(review.get('im:rating', {}).get('label', 3)),  # Default to 3 if missing
                    'date': review.get('updated', {}).get('label', ''),
                    'link': review.get('link', {}).get('attributes', {}).get('href', '')
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Skipping malformed review entry: {e}")
                continue

        if not processed_reviews:
            logger.warning("No valid reviews processed from RSS feed")
            return None

        df = pd.DataFrame(processed_reviews)
        logger.info(f"✅ Proven RSS method: {len(df)} reviews fetched successfully!")
        return _process_app_store_df(df, start_time)

    except requests.RequestException as e:
        logger.error(f"❌ RSS request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ RSS processing failed: {e}")
        return None



def _process_app_store_df(df: pd.DataFrame, start_time: datetime) -> pd.DataFrame:
    """Safely process App Store DataFrame."""
    if df.empty:
        logger.warning("Empty DataFrame from App Store")
        return None

    # Select available columns safely
    available_cols = ["id", "userName", "review", "rating", "date", "link"]
    existing_cols = [col for col in available_cols if col in df.columns]

    if not existing_cols:
        logger.error("No expected columns found in App Store data")
        logger.info(f"Available columns: {list(df.columns)}")
        return None

    df = df[existing_cols]
    logger.info(f"Available columns: {list(df.columns)}")

    logger.info(f"Completed App Store scrape in {datetime.now() - start_time} — {len(df)} reviews fetched.")
    return df