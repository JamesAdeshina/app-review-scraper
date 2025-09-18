"""
scraper.py
----------
Professional app review scraper with:
- Logging
- Progress bars
- Error handling
"""

import logging
from datetime import datetime
from typing import Optional
from app_store_scraper import AppStore
import requests
import logging
from datetime import datetime
from typing import Optional
import pandas as pd
from google_play_scraper import Sort, reviews
from app_store_scraper import AppStore
from tqdm import tqdm


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

        # File handler
        fh = logging.FileHandler(log_file)
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
        # Progress bar is artificial here (single call),
        # but helps indicate work is happening
        with tqdm(total=count, desc="Google Play Reviews", unit="reviews") as pbar:
            result, _ = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=count,
            )
            pbar.update(len(result))

        df = pd.DataFrame(result)
        df = df[["reviewId", "userName", "content", "score", "at", "replyContent"]]

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
    Fetch reviews from Apple App Store.
    """
    logger.info(f"Starting App Store scrape for {app_name} ({app_id}), {count} reviews...")
    start_time = datetime.now()

    try:
        # Direct URL request to fetch reviews
        url = f"https://itunes.apple.com/us/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
        response = requests.get(url)

        if response.status_code != 200:
            logger.error(f"Failed to fetch reviews from the App Store. Status code: {response.status_code}")
            return None

        # Parse the reviews from the response
        reviews_data = response.json().get('feed', {}).get('entry', [])
        if not reviews_data:
            logger.warning("No reviews found for this app.")
            return None

        # Extract reviews
        apple_reviews = [{
            'id': review['id']['label'],
            'userName': review['author']['name']['label'],
            'review': review['content']['label'],
            'rating': review['im:rating']['label'],
            'date': review['updated']['label'],
            'link': review['link']['attributes']['href']
        } for review in reviews_data]

        # Create DataFrame
        df = pd.DataFrame(apple_reviews)
        logger.info(f"Completed App Store scrape in {datetime.now() - start_time} — {len(df)} reviews fetched.")

        # Check the columns
        logger.info(f"Available columns: {df.columns.tolist()}")

        # Ensure required columns are available
        if {'id', 'userName', 'review', 'rating', 'date'}.issubset(df.columns):
            df = df[['id', 'userName', 'review', 'rating', 'date']]
        else:
            logger.error("Required columns are not available in the App Store reviews data.")
            return None

        return df

    except Exception as e:
        logger.error(f"Error scraping App Store reviews: {e}")
        return None
