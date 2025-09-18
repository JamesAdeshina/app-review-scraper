"""
utils.py
--------
Helper utilities for saving and loading data.
"""

import pandas as pd
import logging

logger = logging.getLogger("AppReviewScraper")


def save_to_csv(df: pd.DataFrame, filepath: str) -> None:
    """
    Save DataFrame to a CSV file.

    Args:
        df (pd.DataFrame): The DataFrame to save
        filepath (str): Destination file path

    Returns:
        None
    """
    try:
        df.to_csv(filepath, index=False)
        logger.info(f"✅ Saved {len(df)} reviews → {filepath}")
    except Exception as e:
        logger.error(f"❌ Failed to save CSV to {filepath}: {e}")
