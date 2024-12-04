# First we'll need these libraries
import praw
import pandas as pd
import requests
import os
from datetime import datetime
from instabot import Bot
import time


def setup_reddit_client():
    """
    Creates and returns an authenticated Reddit client.
    You'll need to set up a Reddit application first at https://www.reddit.com/prefs/apps
    """
    reddit = praw.Reddit(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        user_agent="MMA_News_Aggregator v1.0 by YOUR_USERNAME"
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


def post_to_instagram(bot, media_path, caption):
    """
    Posts the prepared content to Instagram.
    Returns True if successful, False otherwise.
    """
    try:
        bot.upload_photo(media_path, caption=caption)
        # Instagram requires a delay between posts
        time.sleep(30)
        return True
    except Exception as e:
        print(f"Error posting to Instagram: {e}")
        return False


def main():
    # Initialize Reddit client
    reddit = setup_reddit_client()

    # Initialize Instagram bot
    bot = Bot()
    bot.login(username="YOUR_INSTAGRAM_USERNAME", password="YOUR_INSTAGRAM_PASSWORD")

    # List of subreddits to scrape
    subreddits = ['MMA', 'ufc', 'mmamemes', 'martialarts']

    for subreddit in subreddits:
        # Scrape posts
        posts = scrape_subreddit_posts(reddit, subreddit, limit=5, post_type="image")

        for _, post in posts.iterrows():
            # Prepare the post for Instagram
            media_path, caption = prepare_instagram_post(post)

            if media_path:
                # Post to Instagram
                success = post_to_instagram(bot, media_path, caption)
                if success:
                    print(f"Successfully posted {post['title']}")
                else:
                    print(f"Failed to post {post['title']}")

                # Clean up downloaded media
                os.remove(media_path)

            # Wait between posts to avoid Instagram's rate limits
            time.sleep(600)  # 10 minutes between posts


if __name__ == "__main__":
    main()
