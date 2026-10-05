"""Public Reddit image review with credentials isolated by browser session."""
import copy
import hashlib
import hmac
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

import praw
from flask import Flask, jsonify, render_template, request, session
from instagrapi import Client
from werkzeug.exceptions import HTTPException

import ai_content_optimizer
from configuration import DATA_DIR, ENV_FIELDS, read_config as read_operator_config, update_config as update_operator_config
from media import prepare_image, is_reddit_image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024
app.config['APP_USERNAME'] = os.environ.get('APP_USERNAME', 'admin')
app.config['APP_PASSWORD'] = os.environ.get('APP_PASSWORD', '')
app.config['PUBLIC_SITE'] = os.environ.get('PUBLIC_SITE', 'true').lower() not in ('false', '0', 'no')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                  SESSION_COOKIE_SECURE=bool(os.environ.get('RENDER')))
if not app.config['PUBLIC_SITE'] and not app.config['APP_PASSWORD']:
    raise RuntimeError('Private mode requires APP_PASSWORD')
publish_lock = Lock()
visitor_lock = Lock()
visitors = {}
VISITOR_TTL = 2 * 60 * 60
MAX_VISITORS = 1000


def empty_config():
    return {section: {field: '' for field in fields} for section, fields in ENV_FIELDS.items()}


def visitor_state(create=False):
    """Called under visitor_lock. Only a random identifier goes into the cookie."""
    now = time.monotonic()
    for key in list(visitors):
        if visitors[key]['expires'] <= now:
            del visitors[key]
    visitor_id = session.get('visitor_id')
    state = visitors.get(visitor_id)
    if state is None and create:
        if len(visitors) >= MAX_VISITORS:
            raise RuntimeError('Visitor session capacity reached')
        visitor_id = secrets.token_hex(32)
        session['visitor_id'] = visitor_id
        state = visitors[visitor_id] = {'config': empty_config(), 'instagram': {}, 'expires': now + VISITOR_TTL}
    if state is not None:
        state['expires'] = now + VISITOR_TTL
    return state


def read_config():
    if not app.config['PUBLIC_SITE']:
        return read_operator_config()
    with visitor_lock:
        state = visitor_state()
        return copy.deepcopy(state['config']) if state else empty_config()


def update_config(updates):
    if not app.config['PUBLIC_SITE']:
        return update_operator_config(updates)
    with visitor_lock:
        state = visitor_state(create=True)
        for section, fields in updates.items():
            state['config'][section].update({key: value for key, value in fields.items() if value})


def error(message, code=400):
    return jsonify(status='error', message=message, error=message), code


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Send a JSON object')
    return data


@app.before_request
def protect_operator():
    if request.path == '/healthz' and request.method == 'GET':
        return None
    password = app.config['APP_PASSWORD']
    if not app.config['PUBLIC_SITE'] and password:
        auth = request.authorization
        if not (auth and auth.type == 'basic'
                and hmac.compare_digest((auth.username or '').encode(), app.config['APP_USERNAME'].encode())
                and hmac.compare_digest((auth.password or '').encode(), password.encode())):
            response, code = error('Operator login required', 401)
            response.headers['WWW-Authenticate'] = 'Basic realm="Pipeline"'
            return response, code
    if request.method == 'POST':
        origin = request.headers.get('Origin')
        expected_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME') or request.host
        if origin and urlsplit(origin).netloc != expected_host:
            return error('Cross-origin requests are not allowed', 403)
        if not request.is_json:
            return error('Content-Type must be application/json', 415)


@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.path != '/healthz' and not request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.errorhandler(ValueError)
def invalid_input(exc):
    return error(str(exc))


@app.errorhandler(HTTPException)
def http_error(exc):
    return error(exc.description, exc.code)


@app.errorhandler(Exception)
def unexpected_error(exc):
    app.logger.error('Request failed (%s)', type(exc).__name__)
    return error('The request failed. Check credentials and provider availability, then retry.', 502)


@app.get('/healthz')
def health():
    return jsonify(status='ok')


@app.get('/')
def index():
    return render_template('index.html', public_site=app.config['PUBLIC_SITE'])


@app.get('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.get('/configuration-status')
def configuration_status():
    config = read_config()
    return jsonify({section: all(config[section].get(field) for field in fields)
                    for section, fields in ENV_FIELDS.items()})


@app.post('/setup')
def setup():
    data = json_body()
    updates = {}
    for section, fields in ENV_FIELDS.items():
        updates[section] = {}
        for field in fields:
            input_field = 'openai_api_key' if section == 'openai' else field
            value = data.get(input_field, '')
            if not isinstance(value, str) or len(value) > 4096:
                raise ValueError('Credential fields must be strings under 4096 characters')
            updates[section][field] = value if field == 'instagram_password' else value.strip()
    update_config(updates)
    return jsonify(status='success')


@app.post('/forget-credentials')
def forget_credentials():
    if not app.config['PUBLIC_SITE']:
        return error('Session clearing is only available in public mode')
    with visitor_lock:
        visitors.pop(session.get('visitor_id'), None)
        session.clear()
    return jsonify(status='success')


@app.post('/fetch-posts')
def fetch_posts():
    names = json_body().get('subreddits', [])
    if not isinstance(names, list) or not 1 <= len(names) <= 10:
        raise ValueError('Select between 1 and 10 subreddits')
    if any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,21}', name) for name in names):
        raise ValueError('Use subreddit names without r/ or punctuation')
    config = read_config()['reddit_credentials']
    if not all(config.get(field) for field in ENV_FIELDS['reddit_credentials']):
        return error('Set Reddit credentials on the setup page')
    reddit = praw.Reddit(client_id=config['reddit_client_id'],
                         client_secret=config['reddit_client_secret'],
                         user_agent=config['reddit_username'],
                         timeout=20, ratelimit_seconds=0)
    posts, warnings, seen = [], [], set()
    with reddit:
        for name in dict.fromkeys(names):
            try:
                for post in reddit.subreddit(name).hot(limit=20):
                    if post.id in seen or not is_reddit_image(post.url) or post.over_18:
                        continue
                    seen.add(post.id)
                    posts.append(dict(title=post.title, url=post.url, score=post.score,
                                      id=post.id, author=str(post.author), subreddit=name,
                                      permalink=f'https://www.reddit.com{post.permalink}'))
            except Exception:
                warnings.append(f'Could not fetch r/{name}. Check access and Reddit credentials.')
    if warnings and not posts:
        return error(' '.join(warnings), 502)
    posts.sort(key=lambda post: post['score'], reverse=True)
    return jsonify(status='success', posts=posts, warnings=warnings)


@app.post('/post-to-instagram')
def post_to_instagram():
    data = json_body()
    url = data.get('url')
    caption = data.get('caption', data.get('title', ''))
    if not isinstance(url, str) or not is_reddit_image(url):
        raise ValueError('Choose a direct HTTPS image hosted by Reddit')
    if not isinstance(caption, str) or len(caption) > 2200:
        raise ValueError('Caption must be at most 2200 characters')
    credentials = read_config()['instagram']
    if not all(credentials.get(field) for field in ENV_FIELDS['instagram']):
        return error('Set Instagram credentials on the setup page')
    if not publish_lock.acquire(blocking=False):
        return error('Another Instagram post is being published. Wait for it to finish.', 409)
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = prepare_image(url, Path(temp_dir) / 'photo.jpg')
            instagram = Client()
            instagram.request_timeout = 20
            account_key = hashlib.sha256(credentials['instagram_username'].encode()).hexdigest()
            if app.config['PUBLIC_SITE']:
                with visitor_lock:
                    state = visitor_state()
                    saved_settings = copy.deepcopy(state['instagram'].get(account_key)) if state else None
                if saved_settings:
                    instagram.set_settings(saved_settings)
            else:
                session_dir = DATA_DIR / 'instagram'
                session_dir.mkdir(parents=True, exist_ok=True)
                session_path = session_dir / (account_key + '.json')
                if session_path.exists():
                    instagram.load_settings(session_path)
            if not instagram.login(credentials['instagram_username'], credentials['instagram_password']):
                raise RuntimeError('Instagram login failed')
            if app.config['PUBLIC_SITE']:
                with visitor_lock:
                    state = visitor_state()
                    if state:
                        state['instagram'][account_key] = instagram.get_settings()
            else:
                instagram.dump_settings(session_path)
            result = instagram.photo_upload(path=path, caption=caption)
            return jsonify(status='success', message='Successfully posted to Instagram', media_id=str(result.pk))
    finally:
        publish_lock.release()


@app.post('/optimize-content')
def optimize_content():
    data = json_body()
    for field in ('caption', 'title', 'subreddit'):
        if not isinstance(data.get(field, ''), str) or len(data.get(field, '')) > 2200:
            raise ValueError('Caption, title, and subreddit must be strings under 2200 characters')
    level = data.get('optimization_level', 'moderate')
    if level not in ('light', 'moderate', 'creative'):
        raise ValueError('Unknown optimization level')
    api_key = read_config()['openai']['api_key']
    if not api_key:
        return error('Add an OpenAI API key to enable caption optimization')
    return jsonify(status='success', **ai_content_optimizer.optimize_content(data, api_key))


if __name__ == '__main__':
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', '5000')),
            debug=os.environ.get('FLASK_DEBUG') == '1')
