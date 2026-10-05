"""Single-operator configuration; deployment environment overrides local settings."""
import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
DATA_DIR = Path(os.environ.get('DATA_DIR', ROOT / '.data'))
CONFIG_FILE = Path(os.environ.get('CONFIG_FILE', DATA_DIR / 'config.json'))
CONFIG_LOCK = RLock()
ENV_FIELDS = {
    'reddit_credentials': {'reddit_client_id': 'REDDIT_CLIENT_ID',
                           'reddit_client_secret': 'REDDIT_CLIENT_SECRET',
                           'reddit_username': 'REDDIT_USER_AGENT'},
    'instagram': {'instagram_username': 'INSTAGRAM_USERNAME',
                  'instagram_password': 'INSTAGRAM_PASSWORD'},
    'openai': {'api_key': 'OPENAI_API_KEY'},
}


def read_config():
    with CONFIG_LOCK:
        if CONFIG_FILE.exists():
            with CONFIG_FILE.open(encoding='utf-8') as stream:
                config = json.load(stream)
        else:
            config = {}
        if not isinstance(config, dict):
            raise ValueError('Configuration must be a JSON object')
        for section, fields in ENV_FIELDS.items():
            values = config.setdefault(section, {})
            if not isinstance(values, dict):
                raise ValueError('Invalid configuration section')
            for field, env_name in fields.items():
                if os.environ.get(env_name):
                    values[field] = os.environ[env_name]
                else:
                    values.setdefault(field, '')
        return config


def update_config(updates):
    """Keep omitted/blank values and unrelated settings; replace atomically."""
    with CONFIG_LOCK:
        config = read_config()
        for section, fields in updates.items():
            config.setdefault(section, {}).update({k: v for k, v in fields.items() if v})
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=CONFIG_FILE.parent, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(config, stream, indent=2)
            os.replace(name, CONFIG_FILE)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return config
