# Reddit to Instagram Content Pipeline

A single-operator Flask app: fetch direct Reddit images, review and edit captions,
optionally optimize them with OpenAI, approve a queue, and explicitly publish photos
to Instagram. Videos, galleries, scheduling, and a persistent posting queue are not
implemented. Queue entries and draft captions live in the current browser page and
are lost on refresh.

## Repository index

| File | Responsibility |
| --- | --- |
| `app.py` | Flask pages, credential setup, Reddit fetching, AI optimization, publishing, operator authentication |
| `configuration.py` | Shared configuration for web and CLI; environment overrides; atomic local saves |
| `media.py` | Reddit image allowlist, bounded downloads, RGB JPEG conversion and aspect-ratio padding |
| `ai_content_optimizer.py` | One OpenAI request for caption, hashtags, and analysis; configurable model |
| `main.py` | Interactive terminal workflow using the same configuration and image processing |
| `templates/` | Setup and review dashboard rendered with Jinja and Bootstrap |
| `static/js/main.js` | Browser review state, edited captions, approval queue, and API calls |
| `static/css/style.css` | Dashboard styling |
| `tests/` | Offline backend and browser-state regression checks |
| `render.yaml` | Render Blueprint for a new service; existing-service settings below |

## Run locally

Use Python 3.12. From the repository directory:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. Fill credentials in `.env` or the setup page. Reddit
fetching needs a valid API client ID, secret, and descriptive user agent. Instagram
credentials are only needed for publishing; an OpenAI key is only needed for AI.
If `APP_PASSWORD` is set, the browser asks for the operator username/password.
Use HTTPS when exposing the app publicly; the local server binds to loopback by default.
Debug mode is off unless explicitly enabled with `FLASK_DEBUG=1`.

Configuration saves to ignored `.data/config.json`. Blank setup fields retain saved
values; environment variables take precedence. `CONFIG_FILE` and `DATA_DIR` can
override paths. `config.example.json` documents the file shape. Never use the
previously committed credentials: rotate the Reddit secret and Instagram password,
which remain exposed in historical commits. Removing them from the working tree
does not remove them from Git history.

The web app no longer uses Flask sessions, so no `SECRET_KEY` is needed. Do not
commit `.env`, local config, downloaded media, or Instagram session settings.
The unused historical `flask_session/` artifact can be removed separately.

## Existing Render service

Target: https://dashboard.render.com/web/srv-d098knodl3ps73ddbmd0

The session used for this repair had no Render connector, API key, CLI, or callable
browser-control tool. The private dashboard could not be inspected; no deployment
was triggered or verified. These are the settings to apply to that existing service
after the changes reach its linked Git branch:

| Setting | Value |
| --- | --- |
| Runtime | Python |
| Root directory | Repository root (blank) |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 300 app:app` |
| Health check path | `/healthz` |
| `PYTHON_VERSION` | `3.12.13` |
| `APP_USERNAME` | Your operator login name (default `admin`) |
| `APP_PASSWORD` | A strong operator password; required on Render |
| Reddit settings | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` |
| Instagram settings | `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD` |
| Optional AI settings | `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-6-luna`, `OPENAI_REASONING_EFFORT=none` |

Use one worker and one service instance: the publish lock and local configuration
are designed for a single operator. A fetch or upload runs synchronously, so the
longer Gunicorn timeout allows external API work while other threads serve health
checks. A 300-second timeout is not a scheduling or background-job system.

Render's filesystem is ephemeral unless a persistent disk is attached. Set the
credentials in Render environment variables so they survive deploys. To preserve
Instagram login settings and setup-page edits, attach a disk and set `DATA_DIR` to
its mount path (for example `/var/data/pipeline`). Disk availability and charges
depend on the Render plan; the Blueprint deliberately does not purchase a disk.

For the existing service, use **Manual Deploy → Deploy latest commit** after
updating its settings and linked branch. Check build/start logs, confirm `/healthz`
returns `{"status":"ok"}`, log in, and fetch from a known subreddit. Test publishing
only with a post you intend to publish. `render.yaml` is for creating a new service,
and adding it to Git alone does not reconfigure the existing service.

Render references: [Flask deployment](https://render.com/docs/deploy-flask),
[Python versions](https://render.com/docs/python-version).

## Provider limitations

Instagram uses the unofficial `instagrapi` private API. Session settings are reused
between uploads instead of logging out each time. Instagram may still require a
challenge, 2FA, or reject a cloud IP; this app has no interactive challenge flow.
For a dependable public publishing product, migrate to Meta's supported publishing
API with the required account connection. This repair retains the existing login
workflow and does not claim it was tested against a live Instagram account.

Only direct `https://i.redd.it` or `https://preview.redd.it` JPG, JPEG, PNG, and WebP
images are fetched/published. Downloads reject redirects, have timeouts, and are
limited to 20 MB/40 megapixels. Images become RGB JPEGs at 1080 pixels wide; extreme
aspect ratios are padded with white. NSFW posts are filtered. Content owners' rights
and attribution still need review before publishing.

AI defaults to `gpt-6-luna` with reasoning disabled for short caption requests.
`OPENAI_MODEL` and `OPENAI_REASONING_EFFORT` allow overrides. Account access and live
caption quality were not verified without an API key. API failures surface as errors;
the app does not silently report an unchanged caption as an AI success.
[Luna documentation](https://developers.openai.com/api/docs/models/gpt-6-luna).

## Verify

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/dashboard.test.cjs
node --check static/js/main.js
```

The tests mock external providers: they do not spend API credits, log in to
Instagram, or publish anything. Run the terminal workflow with
`.venv\Scripts\python.exe main.py` if desired.

Repair verification: all 11 Python tests and 3 JavaScript tests passed with the
installed pinned dependencies. Python compilation, JavaScript syntax, dependency
consistency, and Git whitespace checks passed. A real local Flask process returned
200 for `/dashboard` and `{"status":"ok"}` for `/healthz`. This does not verify
Render deployment, real provider credentials, or live publishing.
