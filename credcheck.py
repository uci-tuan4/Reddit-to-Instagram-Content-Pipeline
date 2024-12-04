import praw
import sys

# Print Python version (helpful for debugging)
print(f"Python version: {sys.version}")

# Your credentials (replace these with your actual values)
client_id = 'your client id'
client_secret = 'your secret id'
user_agent = 'your user agent'

# Print credential lengths (without revealing the actual values)
print(f"Client ID length: {len(client_id)}")
print(f"Client Secret length: {len(client_secret)}")
print(f"User Agent: {user_agent}")

try:
    print("Attempting to initialize Reddit instance...")
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

    print("Reddit instance created successfully")
    print("Attempting to access subreddit...")

    subreddit = reddit.subreddit('MMA')
    print(f"Successfully accessed r/{subreddit.display_name}")

    print("Attempting to fetch a post...")
    for post in subreddit.hot(limit=1):
        print(f"Successfully fetched post: {post.title}")

except Exception as e:
    print(f"An error occurred: {str(e)}")
    print(f"Error type: {type(e)}")
