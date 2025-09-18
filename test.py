from google_play_scraper import reviews, Sort
from app_store_scraper import AppStore
import logging
import requests
import pandas as pd

logging.basicConfig(level=logging.INFO)


# --- Fetch Google Play Reviews ---
def fetch_google_play_reviews(app_id, count=5):
    result, _ = reviews(app_id, count=count, lang='en', country='us', sort=Sort.NEWEST)
    google_reviews = [{
        'author': review['userName'],
        'rating': review['score'],
        'content': review['content'],
        'updated': review['at'],
        'link': f"https://play.google.com/store/apps/details?id={app_id}"
    } for review in result]

    return google_reviews


# --- Fetch Apple App Store Reviews ---
def fetch_apple_app_store_reviews(app_name, app_id):
    app = AppStore(country='us', app_name=app_name, app_id=app_id)
    try:
        url = f"https://itunes.apple.com/us/rss/customerreviews/id={app.app_id}/sortBy=mostRecent/json"
        response = requests.get(url)

        if response.status_code == 200:
            reviews_data = response.json()['feed']['entry']
            apple_reviews = [{
                'author': review['author']['name']['label'],
                'rating': review['im:rating']['label'],
                'content': review['content']['label'],
                'updated': review['updated']['label'],
                'link': review['link']['attributes']['href']
            } for review in reviews_data]
            return apple_reviews
        else:
            logging.error(f"Failed to fetch Apple reviews. Status code: {response.status_code}")
            return []

    except Exception as e:
        logging.error(f"Error fetching Apple reviews: {e}")
        return []


# --- Main Function ---
def main():
    # Fetch reviews from Google Play (Spotify)
    google_reviews = fetch_google_play_reviews('com.spotify.music', count=5)

    # Fetch reviews from Apple App Store (Spotify)
    apple_reviews = fetch_apple_app_store_reviews('spotify', 324684580)

    # Combine both datasets
    all_reviews = google_reviews + apple_reviews

    # Convert to DataFrame for easier viewing and export
    df = pd.DataFrame(all_reviews)

    # Display the first few reviews
    print("Combined Reviews:")
    print(df.head())

    # Save to CSV
    df.to_csv('combined_reviews.csv', index=False)
    print("Reviews saved to 'combined_reviews.csv'.")


if __name__ == "__main__":
    main()
