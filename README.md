# Reddit to Instagram Content Pipeline

A public Flask app: fetch direct Reddit images, review and edit captions,
optionally optimize them with OpenAI, approve a queue, and explicitly publish photos
to Instagram. Videos, galleries, scheduling, and a persistent posting queue are not
implemented. Queue entries and draft captions live in the current browser page and
are lost on refresh.

## Repository index

| File | Responsibility |
| --- | --- |
| `app.py` | Public pages, visitor credential sessions, Reddit fetching, AI optimization, publishing, optional private mode |
| `configuration.py` | Private-mode/CLI configuration; environment overrides; atomic local saves |
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

Open http://127.0.0.1:5000. The site is public by default: visitors enter their own
credentials on the setup page without a site username/password. Reddit
fetching needs a valid API client ID, secret, and descriptive user agent. Instagram
credentials are only needed for publishing; an OpenAI key is only needed for AI.
Public mode ignores `APP_USERNAME` and `APP_PASSWORD`, including previously saved
Render values. For an optional private deployment, set `PUBLIC_SITE=false`,
`APP_USERNAME`, and `APP_PASSWORD`.
Use HTTPS when exposing the app publicly; the local server binds to loopback by default.
Debug mode is off unless explicitly enabled with `FLASK_DEBUG=1`.

In public mode, each browser has a separate server-side credential session. Credentials
and Instagram login settings stay in memory and expire after two hours of inactivity
or a server restart. Only a random session identifier is stored in the signed,
HttpOnly, SameSite cookie. The setup page's **Clear my credentials** button deletes
that visitor's credentials and login settings. Public visitors cannot use owner
credentials from environment variables or local config, or other visitors' credentials.
Blank setup fields retain that visitor's saved values.

In private mode and the CLI, configuration saves to ignored `.data/config.json`;
environment variables take precedence. `CONFIG_FILE` and `DATA_DIR` can override
paths. `config.example.json` documents the file shape. Never use the
previously committed credentials: rotate the Reddit secret and Instagram password,
which remain exposed in historical commits. Removing them from the working tree
does not remove them from Git history.

Set `SECRET_KEY` to a random secret to keep cookie signing stable; otherwise a key
is generated at startup. Credentials still expire on restart because the visitor
store is in memory. Render session cookies require HTTPS. Do not
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
| `PUBLIC_SITE` | `true` (default); no site login required |
| `SECRET_KEY` | Optional random cookie-signing key; Blueprint generates one |
| Optional AI settings | `OPENAI_MODEL=gpt-6-luna`, `OPENAI_REASONING_EFFORT=none` |

Use one worker and one service instance: visitor sessions are in memory and the
publish lock serializes uploads. A fetch or upload runs synchronously, so the
longer Gunicorn timeout allows external API work while other threads serve health
checks. A 300-second timeout is not a scheduling or background-job system.

Public mode does not need a persistent disk and does not save visitor credentials
to files. There is a maximum of 1000 active visitor sessions. This in-memory design
does not support multiple workers/instances. For larger deployments, migrate sessions
to a shared store and add request throttling. Private mode can use a persistent
disk mounted at `DATA_DIR` for its operator settings.

Remove `PUBLIC_SITE=false` if it was set; existing `APP_PASSWORD` values are ignored
in public mode. Owner Reddit, Instagram, and OpenAI secrets are not used by public
visitors and can be removed from the service environment if private mode/CLI is unused.

For the existing service, use **Manual Deploy → Deploy latest commit** after
updating its settings and linked branch. Check build/start logs, confirm `/healthz`
returns `{"status":"ok"}`, enter your own provider credentials, and fetch from a known subreddit. Test publishing
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

Repair verification: all 14 Python tests and 3 JavaScript tests passed with the
installed pinned dependencies. Python compilation, JavaScript syntax, dependency
consistency, and Git whitespace checks passed. A real local Flask process returned
200 for `/dashboard` and `{"status":"ok"}` for `/healthz`. This does not verify
Render deployment, real provider credentials, or live publishing.
