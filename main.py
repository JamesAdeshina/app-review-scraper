"""
main.py
-------
Entry point for scraping WhatsApp reviews with enhanced logging & progress.
"""

from pathlib import Path
from src.scraper import fetch_google_play_reviews, fetch_app_store_reviews
from src.utils import save_to_csv
import logging

logger = logging.getLogger("AppReviewScraper")


def main():
    raw_path = Path("data/raw")
    raw_path.mkdir(parents=True, exist_ok=True)

    # WhatsApp Configuration
    app_name = "whatsapp"
    google_id = "com.whatsapp"
    apple_name = "whatsapp-messenger"
    apple_id = 310633997
    count = 200

    logger.info(f"\n Scraping reviews for: WhatsApp")

    # Google Play
    logger.info("Starting Google Play scrape...")
    gplay_df = fetch_google_play_reviews(
        app_id=google_id, count=count, lang="en", country="us"
    )
    if gplay_df is not None:
        save_to_csv(gplay_df, raw_path / "whatsapp_google_play_reviews.csv")
    else:
        logger.warning("  Google Play scraping failed")

    # Apple App Store
    logger.info("Starting Apple App Store scrape...")
    appstore_df = fetch_app_store_reviews(
        app_name=apple_name, app_id=apple_id, country="us", count=count
    )
    if appstore_df is not None:
        save_to_csv(appstore_df, raw_path / "whatsapp_apple_store_reviews.csv")
    else:
        logger.warning("  Apple Store scraping failed")

    logger.info(" All scraping tasks finished!")


if __name__ == "__main__":
    main()
