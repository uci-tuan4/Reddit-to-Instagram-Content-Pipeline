import praw
import pandas as pd
import requests
import os
from datetime import datetime
from instagrapi import Client
import time


def get_credentials():
    """
    Gets Reddit API and Instagram credentials from user input.
    Returns tuple of (reddit_client_id, reddit_client_secret, reddit_username,
                     instagram_username, instagram_password)
    """
    print("\n=== Reddit API Credentials ===")
    print("(Get these from https://www.reddit.com/prefs/apps)")
    reddit_client_id = input("Enter Reddit Client ID: ").strip()
    reddit_client_secret = input("Enter Reddit Client Secret: ").strip()
    reddit_username = input("Enter your Reddit User Agent (Example: MMA_News_Aggregator v1.0 by {username}): ").strip()

    print("\n=== Instagram Credentials ===")
    instagram_username = input("Enter Instagram username: ").strip()
    instagram_password = input("Enter Instagram password: ").strip()

    return (reddit_client_id, reddit_client_secret, reddit_username,
            instagram_username, instagram_password)


def get_subreddit_list(reddit):
    """
    Allows user to customize the list of subreddits to scrape.
    Returns list of validated subreddit names.
    """
    default_subreddits = ['mma', 'ufc', 'mmamemes']

    print("\n=== Subreddit Selection ===")
    print("Current default subreddits:", ", ".join(f"r/{sub}" for sub in default_subreddits))

    while True:
        choice = input("\nWould you like to modify the subreddit list? (yes/no): ").lower().strip()
        if choice == 'yes':
            subreddits = []
            print("\nEnter subreddit names one at a time (without r/).")
            print("Press Enter twice when done.")

            while True:
                sub = input("Enter subreddit name (or press Enter to finish): ").strip()
                if not sub:  # User pressed Enter without input
                    if not subreddits:  # No subreddits entered
                        print("No subreddits entered. Using defaults.")
                        return default_subreddits
                    break

                # Validate subreddit exists
                try:
                    reddit.subreddit(sub).id  # This will raise an error if subreddit doesn't exist
                    subreddits.append(sub)
                    print(f"Added r/{sub} to list")
                except Exception as e:
                    print(f"Error: r/{sub} not found or not accessible. Please try another.")

            print("\nFinal subreddit list:", ", ".join(f"r/{sub}" for sub in subreddits))
            return subreddits

        elif choice == 'no':
            print("Using default subreddit list.")
            return default_subreddits

        print("Please enter 'yes' or 'no'")


def setup_instagram_client(username, password):
    """
    Creates and returns an authenticated Instagram client.
    """
    try:
        client = Client()
        client.login(username, password)
        print("\nSuccessfully logged into Instagram!")
        return client
    except Exception as e:
        print(f"\nError logging into Instagram: {e}")
        return None


def setup_reddit_client(client_id, client_secret, username):
    """
    Creates and returns an authenticated Reddit client.
    """
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=f"{username}"
        )
        # Test the connection
        reddit.user.me()
        print("\nSuccessfully connected to Reddit API!")
        return reddit
    except Exception as e:
        print(f"\nError connecting to Reddit: {e}")
        return None


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

#mma #ufc #viral #fyp #mixedmartialarts #mmafıghter #mmanews #ufcnews #mmacommunity #ufcfıghter #champion #mmafıghters #wrestling #kickboxing #boxing #combatsports #mixedmartialarts #bjj #mmastriking #submission #mmatraining #ko #muaythai #jiujitsu"""

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
    print("Welcome to Tu's Reddit to Instagram Pipeline!")
    print("Please enter your credentials to begin.")

    # Get credentials from user
    credentials = get_credentials()

    # Setup Reddit client
    reddit = setup_reddit_client(credentials[0], credentials[1], credentials[2])
    if not reddit:
        print("Failed to set up Reddit client. Exiting...")
        return

    # Setup Instagram client
    instagram = setup_instagram_client(credentials[3], credentials[4])
    if not instagram:
        print("Failed to set up Instagram client. Exiting...")
        return

    # Get customized subreddit list
    subreddits = get_subreddit_list(reddit)
    posts_queue = []

    # Collect posts from all subreddits
    for subreddit in subreddits:
        print(f"\nScraping posts from r/{subreddit}...")
        subreddit_posts = scrape_subreddit_posts(reddit, subreddit, limit=20, post_type="image")
        posts_queue.extend(subreddit_posts.to_dict('records'))

    if not posts_queue:
        print("\nNo posts found in the selected subreddits. Exiting...")
        return

    # Sort posts by score to show the most popular ones first
    posts_queue.sort(key=lambda x: x['score'], reverse=True)

    print(f"\nFound {len(posts_queue)} posts to review.")

    posts_processed = 0
    for post in posts_queue:
        # Ask for approval before processing
        if get_user_approval(post):
            print("\nProcessing approved post...")
            media_path, caption = prepare_instagram_post(post)

            if media_path:
                success = post_to_instagram(instagram, media_path, caption)
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
