"""
cleaner.py
----------
Cleans raw scraped app review data with progress bars and console logging.
"""

import re
import logging
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from bs4 import MarkupResemblesLocatorWarning
import warnings
from tqdm import tqdm
tqdm.pandas()
import time

# Fix logging to show console output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("logs/cleaner.log")  # File output
    ]
)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# Get project root
project_root = Path(__file__).parent.parent
logger = logging.getLogger("AppReviewCleaner")

def clean_text(text: str) -> str:
    """Normalize review text by removing HTML, emojis, and extra spaces."""
    if not isinstance(text, str):
        return ""

    # Remove HTML tags
    try:
        text = BeautifulSoup(text, "html.parser").get_text()
    except:
        pass

    # Remove emojis & non-ASCII chars
    text = text.encode("ascii", "ignore").decode("utf-8")

    # Lowercase
    text = text.lower()

    # Remove punctuation & special chars (keep words & numbers)
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def clean_reviews(input_path: Path, output_path: Path) -> None:
    """
    Cleans review CSV file and saves processed version with progress tracking.
    """
    try:
        df = pd.read_csv(input_path)
        logger.info(f"🔍 Cleaning {input_path.name} — {len(df)} rows...")

        # Detect review text column
        if "review" in df.columns:
            review_col = "review"
        elif "content" in df.columns:
            review_col = "content"
        else:
            logger.error(f"❌ No review column found in {input_path}!")
            return

        logger.info(f"📝 Using review column: {review_col}")

        # Drop duplicates & null reviews
        initial_count = len(df)
        df.drop_duplicates(subset=[review_col], inplace=True)
        df.dropna(subset=[review_col], inplace=True)
        logger.info(f"🗑️  Removed {initial_count - len(df)} duplicates/empty reviews")

        # Clean text with progress bar
        logger.info("✨ Cleaning text content...")
        df["clean_review"] = df[review_col].progress_apply(clean_text)

        # Remove empty cleaned reviews
        cleaned_count = len(df[df["clean_review"].str.len() > 0])
        df = df[df["clean_review"].str.len() > 0]
        logger.info(f"🧹 Kept {cleaned_count} non-empty cleaned reviews")

        # Standardize date column if exists
        if "date" in df.columns or "at" in df.columns:
            date_col = "date" if "date" in df.columns else "at"
            logger.info(f"📅 Normalizing dates in column: {date_col}")
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            valid_dates = df[date_col].notna().sum()
            df = df[df[date_col].notna()]
            logger.info(f"✅ {valid_dates} valid dates normalized")

        # Reset index
        df.reset_index(drop=True, inplace=True)

        # Ensure processed folder exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save cleaned dataset
        df.to_csv(output_path, index=False)
        logger.info(f"✅ Saved cleaned file → {output_path} ({len(df)} rows)")

    except Exception as e:
        logger.error(f"❌ Error cleaning {input_path}: {e}")


if __name__ == "__main__":
    start_time = time.time()
    raw_dir = project_root / "data/raw"
    processed_dir = project_root / "data/processed"

    # Clean Google Play reviews
    logger.info("🚀 Starting cleaning pipeline...")
    clean_reviews(
        raw_dir / "google_play_reviews.csv",
        processed_dir / "google_play_reviews_clean.csv",
    )

    # Clean Apple Store reviews
    clean_reviews(
        raw_dir / "apple_store_reviews.csv",
        processed_dir / "apple_store_reviews_clean.csv",
    )

    elapsed = time.time() - start_time
    logger.info(f"🎉 All cleaning tasks finished in {elapsed:.2f} seconds!")
    print(f"\n🎉 Cleaning pipeline complete! Processed in {elapsed:.2f}s")