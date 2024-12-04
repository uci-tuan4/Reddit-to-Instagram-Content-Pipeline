import praw
import pandas as pd
import requests
import os
from datetime import datetime
from instagrapi import Client
import time


def setup_reddit_client():
    """
    Creates and returns an authenticated Reddit client.
    You'll need to set up a Reddit application first at https://www.reddit.com/prefs/apps
    """
    reddit = praw.Reddit(
        client_id="your_client_id",
        client_secret="your_client_secret",
        user_agent="your_user_agent"
    )
    return reddit


def download_media(url, filename):
    """
    Downloads media from a URL and saves it with the given filename.
    Returns the path to the saved file.
    """
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    return None


def get_user_approval(post_data):
    print("\n" + "=" * 50)
    # Safely access dictionary values with .get() method to avoid KeyError
    print(f"Subreddit: r/{post_data.get('subreddit', 'Unknown')}")
    print(f"Title: {post_data.get('title', 'No title')}")
    print(f"Author: u/{post_data.get('author', 'Unknown')}")
    print(f"Score: {post_data.get('score', 0)}")
    print(f"URL: {post_data.get('url', 'No URL')}")
    print("=" * 50)

    while True:
        response = input("\nWould you like to post this? (yes/no): ").lower().strip()
        if response in ['yes', 'no']:
            return response == 'yes'
        print("Please enter 'yes' or 'no'")

def scrape_subreddit_posts(reddit, subreddit_name, limit=10, post_type="all"):
    """
    Scrapes posts from a specified subreddit.
    post_type can be "all", "image", or "video"
    """
    subreddit = reddit.subreddit(subreddit_name)
    posts_data = []

    for post in subreddit.hot(limit=limit):
        # Skip posts that don't have media if we're looking for specific types
        if post_type == "image" and not post.url.endswith(('.jpg', '.jpeg', '.png')):
            continue
        if post_type == "video" and not hasattr(post, 'is_video'):
            continue

        post_data = {
            'title': post.title,
            'url': post.url,
            'score': post.score,
            'id': post.id,
            'author': str(post.author),
            'created_utc': datetime.fromtimestamp(post.created_utc),
            'permalink': f"https://reddit.com{post.permalink}",
            'is_video': hasattr(post, 'is_video') and post.is_video
        }
        posts_data.append(post_data)

    return pd.DataFrame(posts_data)


def prepare_instagram_post(post_data):
    """
    Prepares a Reddit post for Instagram by downloading media and formatting caption.
    Returns tuple of (media_path, caption)
    """
    # Create a directory for media if it doesn't exist
    if not os.path.exists('media'):
        os.makedirs('media')

    # Download the media
    filename = f"media/{post_data['id']}.jpg"
    media_path = download_media(post_data['url'], filename)

    # Prepare the caption
    caption = f"""{post_data['title']} 🔥🔥🔥

#mma #ufc #mixedmartialarts #mmafıghter #mmanews #mmalife #ufcnews #mmacommunity #ufcvegas #ufcfıghter #champion 
#mmafıghters #wrestling #kickboxing #boxing #breakingmma #mmatalk #combatsports #mixedmartialarts #bjj
#mmastriking #submission #mmatraining #ko"""

    return media_path, caption


def post_to_instagram(client, media_path, caption):
    """
    Posts the prepared content to Instagram using instagrapi.
    Returns True if successful, False otherwise.
    """
    try:
        client.photo_upload(media_path, caption)
        time.sleep(30)  # Cooldown period after posting
        return True
    except Exception as e:
        print(f"Error posting to Instagram: {e}")
        return False


def main():
    # Initialize Reddit client
    reddit = setup_reddit_client()

    # Initialize Instagram bot
    client = Client()
    client.login(username="strike_zone_news", password="Angels87!")

    # List of subreddits to scrape
    subreddits = ['MMA', 'ufc', 'mmamemes', 'martialarts', 'kickboxing']
    posts_queue = []

    # Collect posts from all subreddits
    for subreddit in subreddits:
        print(f"\nScraping posts from r/{subreddit}...")
        subreddit_posts = scrape_subreddit_posts(reddit, subreddit, limit=5, post_type="image")
        posts_queue.extend(subreddit_posts.to_dict('records'))

    # Sort posts by score to show the most popular ones first
    posts_queue.sort(key=lambda x: x['score'], reverse=True)

    posts_processed = 0
    for post in posts_queue:
        # Ask for approval before processing
        if get_user_approval(post):
            print("\nProcessing approved post...")
            media_path, caption = prepare_instagram_post(post)

            if media_path:
                success = post_to_instagram(client, media_path, caption)
                if success:
                    print(f"Successfully posted: {post['title']}")
                    posts_processed += 1
                else:
                    print(f"Failed to post: {post['title']}")

                # Clean up downloaded media
                os.remove(media_path)

                # Wait between successful posts
                if success:
                    print("\nWaiting 10 minutes before next post...")
                    time.sleep(600)
        else:
            print("Post skipped. Moving to next post...")

    print(f"\nSession complete. Posted {posts_processed} items to Instagram.")


if __name__ == "__main__":
    main()
