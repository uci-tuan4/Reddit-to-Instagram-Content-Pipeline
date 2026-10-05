# Fix List

Priority order for the stale-code cleanup pass.

1. [x] Guard the dashboard JavaScript so it only initializes on `/dashboard`.
2. [x] Remove secrets from `config.json`; use ignored local settings or environment variables.
3. [x] Preserve existing OpenAI settings and blank/omitted credentials on setup saves.
4. [x] Remove unused Flask sessions/hardcoded secret key; make debug opt-in and require operator authentication on Render.
5. [x] Install and check compatibility with Flask 3.1.3, instagrapi 3.0.20, PRAW 8.0.3, and OpenAI 3.24.0.
6. [x] Fix queued captions, review index reset, provider errors, unsafe HTML interpolation, and repeated approval.
7. [x] Share configuration/media processing with the CLI; fix its read-only Reddit connection check.
8. [x] Add bounded image downloads, valid photo dimensions, reused Instagram sessions, and publish concurrency protection.
9. [x] Use configurable GPT-6 Luna and one request for caption/hashtags/analysis.
10. [x] Add repository index, local instructions, Render settings, and offline regression coverage.

Still requires external verification: valid Reddit API access, OpenAI model access,
Instagram login/challenges and an intentional test upload, and the existing Render
service's linked branch/settings/deploy. Rotate historically committed credentials.
