import base64
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PIL import Image
import app as web
import configuration
import ai_content_optimizer
import media


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        for target, attr, value in ((configuration, 'CONFIG_FILE', directory / 'config.json'),
                                    (web, 'DATA_DIR', directory)):
            patcher = patch.object(target, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.old_password = web.app.config['APP_PASSWORD']
        self.old_username = web.app.config['APP_USERNAME']
        web.app.config.update(APP_PASSWORD='', APP_USERNAME='admin', TESTING=True)
        self.addCleanup(lambda: web.app.config.update(APP_PASSWORD=self.old_password,
                                                      APP_USERNAME=self.old_username))
        self.client = web.app.test_client()

    def credentials(self):
        return self.client.post('/setup', json={
            'reddit_client_id': 'test', 'reddit_client_secret': 'test',
            'reddit_username': 'tests/1.0', 'instagram_username': 'test',
            'instagram_password': 'test', 'openai_api_key': 'test-key'})

    def test_pages_and_health_without_provider_credentials(self):
        for path in ('/', '/dashboard', '/healthz'):
            self.assertEqual(self.client.get(path).status_code, 200)
        status = self.client.get('/configuration-status').json
        self.assertFalse(any(status.values()))

    def test_setup_preserves_ai_and_blank_fields(self):
        self.assertEqual(self.credentials().status_code, 200)
        self.client.post('/setup', json={'reddit_client_id': 'new', 'openai_api_key': ''})
        config = configuration.read_config()
        self.assertEqual(config['openai']['api_key'], 'test-key')
        self.assertEqual(config['reddit_credentials']['reddit_client_id'], 'new')
        self.assertEqual(config['instagram']['instagram_password'], 'test')
        with patch.dict(os.environ, {'REDDIT_CLIENT_ID': 'environment'}):
            self.assertEqual(configuration.read_config()['reddit_credentials']['reddit_client_id'], 'environment')

    def test_auth_and_cross_origin(self):
        web.app.config['APP_PASSWORD'] = 'operator'
        self.assertEqual(self.client.get('/').status_code, 401)
        self.assertEqual(self.client.get('/healthz').status_code, 200)
        auth = {'Authorization': 'Basic ' + base64.b64encode(b'admin:operator').decode()}
        self.assertEqual(self.client.get('/', headers=auth).status_code, 200)
        self.assertEqual(self.client.post('/setup', json={}, headers={**auth, 'Origin': 'https://attacker.example'}).status_code, 403)
        self.assertEqual(self.client.post('/setup', data='x', headers=auth).status_code, 415)

    def test_invalid_input_and_missing_credentials(self):
        for body in ([], {'subreddits': []}, {'subreddits': ['<script>']}):
            self.assertEqual(self.client.post('/fetch-posts', json=body).status_code, 400)
        self.assertEqual(self.client.post('/fetch-posts', data='null', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/fetch-posts', json={'subreddits': ['all']}).status_code, 400)
        self.assertEqual(self.client.post('/post-to-instagram', json={'url': 'http://localhost/secret.jpg'}).status_code, 400)
        self.assertEqual(self.client.post('/optimize-content', json={'caption': 'draft'}).status_code, 400)
        self.assertEqual(self.client.post('/setup', json={'openai_api_key': []}).status_code, 400)

    def test_fetch_filters_deduplicates_sorts_and_keeps_partial_results(self):
        self.credentials()
        def post(id, score, url='https://i.redd.it/test.PNG?x=1', nsfw=False):
            return SimpleNamespace(id=id, score=score, url=url, title=id, author='author',
                                   permalink='/r/all/comments/' + id, over_18=nsfw)
        reddit = MagicMock()
        reddit.__enter__.return_value = reddit
        def subreddit(name):
            if name == 'broken':
                raise RuntimeError('unavailable')
            return SimpleNamespace(hot=lambda **kw: [post('low', 1), post('high', 10), post('low', 1),
                post('external', 100, 'https://example.com/a.jpg'), post('nsfw', 100, nsfw=True)])
        reddit.subreddit.side_effect = subreddit
        with patch.object(web.praw, 'Reddit', return_value=reddit):
            response = self.client.post('/fetch-posts', json={'subreddits': ['all', 'broken']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p['id'] for p in response.json['posts']], ['high', 'low'])
        self.assertTrue(response.json['warnings'])

    def test_instagram_publish_caption_and_saved_session(self):
        self.credentials()
        instagram = MagicMock()
        instagram.photo_upload.return_value = SimpleNamespace(pk=42)
        with patch.object(web, 'prepare_image', return_value=Path(self.temp.name) / 'photo.jpg'), \
                patch.object(web, 'Client', return_value=instagram):
            response = self.client.post('/post-to-instagram', json={
                'url': 'https://i.redd.it/photo.jpg', 'caption': 'queued caption'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(instagram.photo_upload.call_args.kwargs['caption'], 'queued caption')
        self.assertEqual(instagram.dump_settings.call_count, 1)
        instagram.logout.assert_not_called()
        self.assertFalse(web.publish_lock.locked())

    def test_publish_failure_releases_lock_and_hides_provider_secrets(self):
        self.credentials()
        with patch.object(web, 'prepare_image', side_effect=RuntimeError('secret-token')):
            response = self.client.post('/post-to-instagram', json={'url': 'https://i.redd.it/photo.jpg'})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('secret-token', response.get_data(as_text=True))
        self.assertFalse(web.publish_lock.locked())

    def test_ai_model_and_provider_failure(self):
        self.credentials()
        ai = MagicMock()
        ai.__enter__.return_value = ai
        ai.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({'optimized_caption': 'edited #topic', 'hashtags': '#topic',
                'analysis': {'sentiment': 'positive', 'topics': ['topic'], 'engagement_prediction': 'medium'}})))])
        with patch.object(ai_content_optimizer, 'OpenAI', return_value=ai):
            response = self.client.post('/optimize-content', json={
                'caption': 'draft', 'generate_hashtags': True, 'analyze_content': True})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['optimized_caption'], 'edited #topic')
            args = ai.chat.completions.create.call_args.kwargs
            self.assertEqual(args['model'], 'gpt-6-luna')
            self.assertEqual(args['reasoning_effort'], 'none')
            ai.chat.completions.create.side_effect = RuntimeError('secret-key')
            failure = self.client.post('/optimize-content', json={'caption': 'draft'})
            self.assertEqual(failure.status_code, 502)
            self.assertNotIn('secret-key', failure.get_data(as_text=True))


class MediaTests(unittest.TestCase):
    def test_allowlist(self):
        for url in ('http://i.redd.it/a.jpg', 'https://i.redd.it.evil.test/a.jpg',
                    'https://user@i.redd.it/a.jpg', 'https://i.redd.it:bad/a.jpg',
                    'https://127.0.0.1/a.jpg', 'https://i.redd.it/a.mp4'):
            self.assertFalse(media.is_reddit_image(url), url)
        self.assertTrue(media.is_reddit_image('https://preview.redd.it/a.WEBP?width=1080'))

    def test_download_and_pad_portrait_landscape(self):
        for size in ((400, 1200), (1200, 200), (191, 100)):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as directory:
                source = io.BytesIO()
                Image.new('RGBA', size, 'red').save(source, 'PNG')
                response = MagicMock(status_code=200)
                response.__enter__.return_value = response
                response.iter_content.return_value = [source.getvalue()]
                path = Path(directory) / 'photo.jpg'
                with patch.object(media.requests, 'get', return_value=response):
                    media.prepare_image('https://i.redd.it/a.png', path)
                with Image.open(path) as result:
                    self.assertEqual(result.mode, 'RGB')
                    self.assertEqual(result.width, 1080)
                    self.assertGreaterEqual(result.width / result.height, 0.8)
                    self.assertLessEqual(result.width / result.height, 1.91)

    def test_oversized_download_and_redirect_rejected(self):
        response = MagicMock(status_code=200)
        response.__enter__.return_value = response
        response.iter_content.return_value = [b'12345']
        with tempfile.TemporaryDirectory() as directory, patch.object(media.requests, 'get', return_value=response):
            with patch.object(media, 'MAX_BYTES', 4), self.assertRaises(ValueError):
                media.prepare_image('https://i.redd.it/a.png', Path(directory) / 'x')
            response.status_code = 302
            with self.assertRaises(ValueError):
                media.prepare_image('https://i.redd.it/a.png', Path(directory) / 'x')


if __name__ == '__main__':
    unittest.main()
