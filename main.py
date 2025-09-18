"""
main.py
-------
Entry point for scraping app reviews with enhanced logging & progress.
"""

from pathlib import Path
from src.scraper import fetch_google_play_reviews, fetch_app_store_reviews
from src.utils import save_to_csv
import logging

logger = logging.getLogger("AppReviewScraper")


def main():
    raw_path = Path("data/raw")
    raw_path.mkdir(parents=True, exist_ok=True)

    # Example 1: Google Play
    gplay_df = fetch_google_play_reviews(
        app_id="com.whatsapp", count=200, lang="en", country="us"
    )
    if gplay_df is not None:
        save_to_csv(gplay_df, raw_path / "google_play_reviews.csv")

    # Example 2: Apple App Store
    appstore_df = fetch_app_store_reviews(
        app_name="whatsapp-messenger", app_id=310633997, country="us", count=200
    )
    if appstore_df is not None:
        save_to_csv(appstore_df, raw_path / "apple_store_reviews.csv")

    logger.info("✅ All scraping tasks finished.")


if __name__ == "__main__":
    main()
