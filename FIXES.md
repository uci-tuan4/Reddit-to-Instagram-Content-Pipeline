# Fix List

Priority order for the stale-code cleanup pass.

1. [x] Guard the dashboard JavaScript so it only initializes on `/dashboard`.
2. Remove secrets from `config.json` and replace them with a local ignored sample or environment variables.
3. Preserve existing `openai` settings when `/setup` saves new Reddit and Instagram credentials.
4. Move `SECRET_KEY` and debug settings out of source code for anything beyond local development.
5. Do a compatibility pass on `instagrapi`, `praw`, and OpenAI usage against the currently installed versions.
