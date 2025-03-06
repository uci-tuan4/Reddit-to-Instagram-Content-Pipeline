from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import praw
import json
from instagrapi import Client

# Import other necessary modules

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/setup', methods=['POST'])
def setup():
    data = request.json
    try:
        # Save credentials to config
        config = {
            "reddit_credentials": {
                "reddit_client_id": data['reddit_client_id'],
                "reddit_client_secret": data['reddit_client_secret'],
                "reddit_username": data['reddit_username']
            },
            "instagram": {
                "instagram_username": data['instagram_username'],
                "instagram_password": data['instagram_password']
            }
        }
        with open('config.json', 'w') as f:
            json.dump(config, f)

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/post-to-instagram', methods=['POST'])
def post_to_instagram():
    post_data = request.json
    # Implement your Instagram posting logic here
    return jsonify({"status": "success"})


@app.route('/fetch-posts', methods=['POST'])
def fetch_posts():
    try:
        subreddits = request.json.get('subreddits', [])

        if not subreddits:
            return jsonify({
                'error': 'No subreddits selected'
            }), 400

        # Load configuration
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            return jsonify({
                'error': 'Configuration not found. Please set up credentials first.'
            }), 400

        # Initialize Reddit client
        try:
            reddit = praw.Reddit(
                client_id=config['reddit_credentials']['reddit_client_id'],
                client_secret=config['reddit_credentials']['reddit_client_secret'],
                user_agent=config['reddit_credentials']['reddit_username']
            )
        except Exception as e:
            return jsonify({
                'error': f'Failed to initialize Reddit client: {str(e)}'
            }), 500

        posts = []
        for subreddit_name in subreddits:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for post in subreddit.hot(limit=10):
                    if post.url.endswith(('.jpg', '.jpeg', '.png')):
                        posts.append({
                            'title': post.title,
                            'url': post.url,
                            'score': post.score,
                            'id': post.id,
                            'author': str(post.author),
                            'subreddit': subreddit_name,
                            'permalink': f"https://reddit.com{post.permalink}"
                        })
            except Exception as e:
                return jsonify({
                    'error': f'Error fetching posts from r/{subreddit_name}: {str(e)}'
                }), 500

        return jsonify({
            'status': 'success',
            'posts': posts
        })

    except Exception as e:
        return jsonify({
            'error': f'Unexpected error: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(debug=True)