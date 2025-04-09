from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import praw
import json
import os
import tempfile
import requests
from instagrapi import Client
from PIL import Image
from datetime import datetime
import ai_content_optimizer


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
        
        # Add OpenAI API key if provided
        if 'openai_api_key' in data and data['openai_api_key']:
            if 'openai' not in config:
                config['openai'] = {}
            config['openai']['api_key'] = data['openai_api_key']
        
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
    try:
        post_data = request.json
        if not post_data:
            return jsonify({"status": "error", "message": "No post data received"}), 400

        # Load Instagram credentials from config
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                instagram_credentials = config['instagram']
        except (FileNotFoundError, KeyError) as e:
            return jsonify({
                "status": "error",
                "message": "Instagram credentials not found in config"
            }), 400

        # Create temp directory for media processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download and process the image
            image_url = post_data.get('url')
            if not image_url:
                return jsonify({
                    "status": "error",
                    "message": "No image URL provided"
                }), 400

            # Download image
            try:
                response = requests.get(image_url)
                response.raise_for_status()

                # Generate temporary file path
                temp_image_path = os.path.join(temp_dir, f"temp_image_{datetime.now().timestamp()}.jpg")

                # Save and process image
                with open(temp_image_path, 'wb') as f:
                    f.write(response.content)

                # Process image with PIL
                with Image.open(temp_image_path) as img:
                    # Convert to RGB if necessary (Instagram requires RGB)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # Resize if necessary (Instagram max size is 1080x1350)
                    max_size = (1080, 1350)
                    if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)

                    # Save processed image
                    img.save(temp_image_path, 'JPEG', quality=95)

                # Initialize Instagram client
                instagram = Client()
                instagram.login(
                    instagram_credentials['instagram_username'],
                    instagram_credentials['instagram_password']
                )

                # Get caption from post data or use default
                caption = post_data.get('caption', post_data.get('title', ''))

                # Upload to Instagram
                instagram.photo_upload(
                    path=temp_image_path,
                    caption=caption
                )

                return jsonify({
                    "status": "success",
                    "message": "Successfully posted to Instagram"
                })

            except requests.exceptions.RequestException as e:
                return jsonify({
                    "status": "error",
                    "message": f"Failed to download image: {str(e)}"
                }), 500

            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Error processing image: {str(e)}"
                }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }), 500

    finally:
        # Cleanup (temp directory is automatically cleaned up)
        if 'instagram' in locals():
            try:
                instagram.logout()
            except:
                pass


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


@app.route('/optimize-content', methods=['POST'])
def optimize_content():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
            
        # Initialize AI client if not already initialized
        if not ai_content_optimizer.client:
            initialized = ai_content_optimizer.initialize_openai()
            if not initialized:
                return jsonify({
                    "status": "error", 
                    "message": "OpenAI API key not found. Please add it in the setup page."
                }), 400
        
        original_caption = data.get('caption', '')
        post_title = data.get('title', '')
        subreddit = data.get('subreddit', '')
        optimization_level = data.get('optimization_level', 'moderate')
        
        # Optimize caption
        optimized_caption = ai_content_optimizer.optimize_caption(
            original_caption, 
            subreddit, 
            post_title, 
            optimization_level
        )
        
        # Generate hashtags separately if requested
        hashtags = None
        if data.get('generate_hashtags', False):
            hashtags = ai_content_optimizer.generate_hashtags(
                subreddit,
                post_title,
                optimized_caption[:100]  # Just use the beginning of the caption
            )
            
        # Get content analysis if requested
        analysis = None
        if data.get('analyze_content', False):
            analysis = ai_content_optimizer.analyze_content_sentiment(
                post_title,
                optimized_caption
            )
        
        return jsonify({
            "status": "success",
            "optimized_caption": optimized_caption,
            "hashtags": hashtags,
            "analysis": analysis
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error optimizing content: {str(e)}"
        }), 500


if __name__ == '__main__':
    app.run(debug=True)