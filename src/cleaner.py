"""
cleaner.py
----------
Cleans raw scraped app review data:
- Removes duplicates & nulls
- Standardizes dates
- Normalizes review text (lowercase, strip HTML, emojis, punctuation)
- Saves processed data
"""

import re
import logging
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from pathlib import Path
from bs4 import MarkupResemblesLocatorWarning
import warnings
from tqdm import tqdm
tqdm.pandas()  # Enable progress_apply
import time

start_time = time.time()
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


# Get project root (one level above src/)
project_root = Path(__file__).parent.parent


logger = logging.getLogger("AppReviewScraper")


def clean_text(text: str) -> str:
    """Normalize review text by removing HTML, emojis, and extra spaces."""
    if not isinstance(text, str):
        return ""

    # Remove HTML tags
    text = BeautifulSoup(text, "html.parser").get_text()

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
    Cleans review CSV file and saves processed version.

    Args:
        input_path (Path): Path to raw reviews CSV.
        output_path (Path): Path to save cleaned reviews CSV.
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

        # Drop duplicates & null reviews
        df.drop_duplicates(subset=[review_col], inplace=True)
        df.dropna(subset=[review_col], inplace=True)

        # Clean text
        df["clean_review"] = df[review_col].progress_apply(clean_text)

        # Standardize date column if exists
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df.dropna(subset=["date"], inplace=True)

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
    raw_dir = project_root / "data/raw"
    processed_dir = project_root / "data/processed"

    # Clean Google Play reviews
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
    logger.info(f"🎉 All cleaning tasks finished in {elapsed:.2f} seconds.")
    print(f"🎉 All cleaning tasks finished in {elapsed:.2f} seconds.")

