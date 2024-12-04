import praw
import pandas as pd
from datetime import datetime
import json
import requests
from typing import List, Dict
import os
from time import sleep


class RedditContentScraper:
    """
    A class to scrape content from specified MMA-related subreddits
    and prepare it for posting to social media platforms.
    """

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """
        Initialize the Reddit scraper with your API credentials.

        Args:
            client_id: Your Reddit API client ID
            client_secret: Your Reddit API client secret
            user_agent: A unique identifier for your application
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )

        # Subreddits we want to monitor
        self.subreddits = ['MMA', 'UFC', 'mmamemes', 'martialarts']

        # Track processed posts to avoid duplicates
        self.processed_posts = set()

    def get_top_posts(self, subreddit: str, time_filter: str = 'day', limit: int = 10) -> List[Dict]:
        """
        Fetch top posts from a specified subreddit.

        Args:
            subreddit: Name of the subreddit to scrape
            time_filter: Time period to consider ('day', 'week', 'month', 'year', 'all')
            limit: Maximum number of posts to fetch

        Returns:
            List of dictionaries containing post information
        """
        posts = []
        subreddit = self.reddit.subreddit(subreddit)

        for post in subreddit.top(time_filter=time_filter, limit=limit):
            # Skip if we've already processed this post
            if post.id in self.processed_posts:
                continue

            # Create a post dictionary with relevant information
            post_data = {
                'id': post.id,
                'title': post.title,
                'url': post.url,
                'permalink': f'https://reddit.com{post.permalink}',
                'score': post.score,
                'created_utc': datetime.fromtimestamp(post.created_utc),
                'author': str(post.author),
                'subreddit': post.subreddit.display_name,
                'is_video': post.is_video,
                'media_type': self._determine_media_type(post.url)
            }

            # Add post to our list and mark as processed
            posts.append(post_data)
            self.processed_posts.add(post.id)

        return posts

    def _determine_media_type(self, url: str) -> str:
        """
        Determine the type of media from the URL.

        Args:
            url: URL to analyze

        Returns:
            String indicating media type ('image', 'video', 'gif', 'text', or 'other')
        """
        lower_url = url.lower()
        if any(ext in lower_url for ext in ['.jpg', '.jpeg', '.png']):
            return 'image'
        elif any(ext in lower_url for ext in ['.mp4', '.mov']):
            return 'video'
        elif '.gif' in lower_url:
            return 'gif'
        elif 'reddit.com/r/' in lower_url:
            return 'text'
        else:
            return 'other'


class BufferPreparer:
    """
    Prepares scraped content for posting to Buffer.
    """

    def __init__(self, buffer_api_token: str):
        """
        Initialize the Buffer preparer with your API credentials.

        Args:
            buffer_api_token: Your Buffer API access token
        """
        self.buffer_api_token = buffer_api_token

    def prepare_post(self, post_data: Dict) -> Dict:
        """
        Format a Reddit post for Buffer.

        Args:
            post_data: Dictionary containing post information

        Returns:
            Dictionary formatted for Buffer API
        """
        # Create a caption that includes attribution
        caption = (
            f"{post_data['title']}\n\n"
            f"Credit: u/{post_data['author']} on r/{post_data['subreddit']}\n\n"
            "#MMA #UFC #MMANews #UFCNews #MixedMartialArts"
        )

        return {
            'text': caption,
            'media': {
                'photo': post_data['url'] if post_data['media_type'] == 'image' else None,
                'video': post_data['url'] if post_data['media_type'] == 'video' else None
            },
            'source_link': post_data['permalink']
        }

    def queue_to_buffer(self, prepared_post: Dict) -> bool:
        """
        Send a prepared post to Buffer's queue.

        Args:
            prepared_post: Dictionary containing the formatted post

        Returns:
            Boolean indicating success or failure
        """
        # This is a placeholder for the actual Buffer API implementation
        # You'll need to implement this based on Buffer's API documentation
        endpoint = "https://api.buffer.com/1/updates/create"
        headers = {"Authorization": f"Bearer {self.buffer_api_token}"}

        try:
            response = requests.post(endpoint, json=prepared_post, headers=headers)
            return response.status_code == 200
        except Exception as e:
            print(f"Error queuing post to Buffer: {e}")
            return False


def main():
    """
    Main function to run the content pipeline.
    """
    # Load configuration from environment variables or a config file
    reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_user_agent = os.getenv('REDDIT_USER_AGENT')
    buffer_api_token = os.getenv('BUFFER_API_TOKEN')

    # Initialize our classes
    scraper = RedditContentScraper(reddit_client_id, reddit_client_secret, reddit_user_agent)
    buffer_prep = BufferPreparer(buffer_api_token)

    # Process each subreddit
    for subreddit in scraper.subreddits:
        # Get top posts
        posts = scraper.get_top_posts(subreddit, time_filter='day', limit=5)

        # Process each post
        for post in posts:
            # Prepare the post for Buffer
            prepared_post = buffer_prep.prepare_post(post)

            # Queue to Buffer
            success = buffer_prep.queue_to_buffer(prepared_post)

            if success:
                print(f"Successfully queued post from r/{subreddit}: {post['title']}")
            else:
                print(f"Failed to queue post from r/{subreddit}: {post['title']}")

            # Be nice to the APIs
            sleep(2)


if __name__ == "__main__":
    main()