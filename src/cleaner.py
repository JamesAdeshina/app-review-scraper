"""
cleaner.py
----------
Cleans raw scraped app review data with progress bars and console logging.
Supports both generic and app-specific filenames (whatsapp_google_play_reviews.csv).
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
from datetime import datetime
import traceback

# Fix logging paths - use project root
project_root = Path(__file__).parent.parent
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

# Setup logging with correct paths
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(logs_dir / "cleaner.log")  # Fixed path
    ]
)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

logger = logging.getLogger("AppReviewCleaner")

def clean_text(text: str) -> str:
    """Normalize review text by removing HTML, emojis, and extra spaces."""
    if not isinstance(text, str):
        return ""

    # Remove HTML tags (only if it looks like HTML)
    if "<" in text and ">" in text:
        try:
            text = BeautifulSoup(text, "html.parser").get_text()
        except:
            pass

    # Remove emojis & non-ASCII chars
    try:
        text = text.encode("ascii", "ignore").decode("utf-8")
    except:
        text = str(text)

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
        # Check if input file exists
        if not input_path.exists():
            logger.warning(f"⚠️  Input file not found: {input_path}")
            return

        df = pd.read_csv(input_path)
        logger.info(f"🔍 Cleaning {input_path.name} — {len(df)} rows...")

        # Detect review text column
        if "review" in df.columns:
            review_col = "review"
        elif "content" in df.columns:
            review_col = "content"
        else:
            logger.error(f"❌ No review column found in {input_path}!")
            logger.info(f"Available columns: {list(df.columns)}")
            return

        logger.info(f"📝 Using review column: {review_col}")

        # Drop duplicates & null reviews
        initial_count = len(df)
        df.drop_duplicates(subset=[review_col], inplace=True)
        df.dropna(subset=[review_col], inplace=True)
        removed_count = initial_count - len(df)
        if removed_count > 0:
            logger.info(f"🗑️  Removed {removed_count} duplicates/empty reviews")

        # Clean text with progress bar
        logger.info("✨ Cleaning text content...")
        df["clean_review"] = df[review_col].progress_apply(clean_text)

        # Remove empty cleaned reviews
        before_clean_filter = len(df)
        df = df[df["clean_review"].str.len() > 0]
        kept_count = len(df)
        logger.info(f"🧹 Kept {kept_count} non-empty cleaned reviews (removed {before_clean_filter - kept_count})")

        # Standardize date column if exists
        date_cols = ["date", "at"]
        date_col = None
        for col in date_cols:
            if col in df.columns:
                date_col = col
                break

        if date_col:
            logger.info(f"📅 Normalizing dates in column: {date_col}")
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            before_date_filter = len(df)
            df = df[df[date_col].notna()]
            valid_dates = len(df)
            logger.info(f"✅ {valid_dates} valid dates normalized (removed {before_date_filter - valid_dates})")

        # Add source detection for future merging
        if "source" not in df.columns:
            if "google" in input_path.name.lower() or "play" in input_path.name.lower():
                df["source"] = "Google Play"
            elif "apple" in input_path.name.lower() or "store" in input_path.name.lower():
                df["source"] = "Apple App Store"
            else:
                df["source"] = input_path.stem

        # Reset index
        df.reset_index(drop=True, inplace=True)

        # Ensure processed folder exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save cleaned dataset
        df.to_csv(output_path, index=False)
        logger.info(f"✅ Saved cleaned file → {output_path} ({len(df)} rows)")

    except Exception as e:
        logger.error(f"❌ Error cleaning {input_path}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


def find_raw_files(raw_dir: Path) -> tuple[Path, Path]:
    """
    Intelligently find Google Play and Apple Store raw files.
    Supports both generic names and app-specific prefixes (whatsapp_, spotify_, etc.).
    """
    logger.info(f"🔍 Scanning {raw_dir} for raw review files...")

    all_files = list(raw_dir.glob("*.csv"))
    if not all_files:
        logger.warning("No CSV files found in raw directory!")
        return None, None

    logger.info(f"Found {len(all_files)} CSV files: {[f.name for f in all_files]}")

    # Find Google Play file (look for 'google', 'play', or generic name)
    google_file = None
    for file in all_files:
        filename = file.name.lower()
        if any(keyword in filename for keyword in ['google', 'play']) or 'google_play_reviews' in filename:
            google_file = file
            break

    # Find Apple Store file (look for 'apple', 'store', or generic name)
    apple_file = None
    for file in all_files:
        filename = file.name.lower()
        if any(keyword in filename for keyword in ['apple', 'store']) or 'apple_store_reviews' in filename:
            apple_file = file
            break

    # Fallback to exact generic names if pattern matching fails
    if not google_file:
        generic_google = raw_dir / "google_play_reviews.csv"
        if generic_google.exists():
            google_file = generic_google
            logger.info(f"Found generic Google Play file: {generic_google.name}")

    if not apple_file:
        generic_apple = raw_dir / "apple_store_reviews.csv"
        if generic_apple.exists():
            apple_file = generic_apple
            logger.info(f"Found generic Apple Store file: {generic_apple.name}")

    logger.info(f"📁 Selected files:")
    logger.info(f"   Google Play: {google_file.name if google_file else 'NOT FOUND'}")
    logger.info(f"   Apple Store: {apple_file.name if apple_file else 'NOT FOUND'}")

    return google_file, apple_file


def generate_clean_filename(raw_filename: str, platform: str) -> str:
    """
    Generate simple, clean filename by just appending '_clean' to the original.
    """
    # Get the base filename without extension
    base_name = Path(raw_filename).stem

    # Simple approach: just append '_clean' to the original filename
    clean_name = f"{base_name}_clean.csv"

    logger.debug(f"Generated clean filename: {raw_filename} → {clean_name}")
    return clean_name


if __name__ == "__main__":
    start_time = time.time()
    raw_dir = project_root / "data" / "raw"
    processed_dir = project_root / "data" / "processed"

    logger.info("🚀 Starting cleaning pipeline...")
    logger.info(f"📂 Raw data directory: {raw_dir}")
    logger.info(f"📂 Processed data directory: {processed_dir}")

    # Check if raw directory exists
    if not raw_dir.exists():
        logger.error(f"❌ Raw data directory not found: {raw_dir}")
        logger.info("💡 Run `python main.py` first to scrape data!")
        exit(1)

    # Intelligently find raw files
    google_file, apple_file = find_raw_files(raw_dir)

    # Clean Google Play reviews
    if google_file:
        clean_filename = generate_clean_filename(google_file.name, "google_play")
        output_path = processed_dir / clean_filename
        clean_reviews(google_file, output_path)
    else:
        logger.warning("⚠️  No Google Play raw file found. Run `python main.py` first!")

    # Clean Apple Store reviews
    if apple_file:
        clean_filename = generate_clean_filename(apple_file.name, "apple_store")
        output_path = processed_dir / clean_filename
        clean_reviews(apple_file, output_path)
    else:
        logger.warning("⚠️  No Apple Store raw file found. Run `python main.py` first!")

    elapsed = time.time() - start_time
    logger.info(f"🎉 All cleaning tasks finished in {elapsed:.2f} seconds!")
    print(f"\n🎉 Cleaning pipeline complete! Processed in {elapsed:.2f}s")
    print(f"📊 Check logs/cleaner.log for detailed output")

    # Show final file listing
    processed_files = list(processed_dir.glob("*.csv"))
    if processed_files:
        print(f"\n📁 Cleaned files created:")
        for file in processed_files:
            size_kb = file.stat().st_size / 1024
            print(f"   ✅ {file.name} ({size_kb:.1f} KB)")
    else:
        print("\n⚠️  No cleaned files were created. Check the logs above.")