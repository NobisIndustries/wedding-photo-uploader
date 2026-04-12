# Wedding Photo Uploader

Simple self-hosted web app for wedding guests to upload and browse photos/videos via QR code.

## Stack

- **Backend:** Python 3.12 + FastAPI
- **Frontend:** Vanilla HTML/CSS/JS (no build step)
- **Uploads:** tus protocol via `tuspyserver` (chunked/resumable), `tus-js-client` on frontend
- **Database:** SQLite via `aiosqlite`
- **Thumbnails:** Pillow + pillow-heif (images), ffmpeg (videos)
- **Deployment:** Docker on Debian VM, exposed via Cloudflare Tunnel or ngrok
- **Caching caveat:** Cloudflare aggressively caches static assets (CSS/JS). Bump the `?v=N` query string in `index.html` when changing CSS or JS files so Cloudflare serves the new version.

## Running

```bash
# Docker (production)
cp .env.example .env  # set UPLOAD_PIN
docker compose up --build

# App runs at http://localhost:8000
```

`tuspyserver` uses `fcntl` (Unix-only) — does not run natively on Windows. Always use Docker.

## Project structure

```
app/
  main.py              # FastAPI entry, router registration, static serving
  config.py            # Env var config (UPLOAD_PIN, MAX_UPLOAD_SIZE, DATA_DIR)
  auth.py              # Session helpers (require_session, create_session)
  database.py          # SQLite init + connection (aiosqlite)
  models.py            # Pydantic models
  routers/
    auth_router.py     # POST /api/auth/verify-pin, GET /api/auth/status
    gallery_router.py  # GET /api/gallery (paginated, includes is_owner flag)
    files_router.py    # GET /api/files/{id}/thumbnail|original, DELETE /api/files/{id}
  services/
    upload_handler.py  # tus router factory + upload completion hook
    thumbnail.py       # Image/video thumbnail generation (runs in background thread)
  static/
    index.html         # Single page, view switching via JS
    css/style.css      # Mobile-first, Cormorant Garamond headings + Inter body
    js/
      app.js           # Init + view switching (auth screen vs gallery)
      auth.js          # PIN form handling
      upload.js        # tus-js-client upload with progress bars
      gallery.js       # Grid rendering, lightbox with prev/next, session-based delete
```

## Key design decisions

- **No accounts** — single shared PIN gates access, session tracked via httponly cookie
- **Session-based deletion** — users can delete their own uploads (matched by session_id cookie). Admin sessions can delete any upload.
- **Admin mode** — second PIN (`ADMIN_PIN`) grants admin privileges. Admin uploads are automatically marked as "official" (can be opted out per-upload via a checkbox).
- **Official photos** — uploads from admin sessions are flagged `is_official`. The gallery has two tabs: "All Photos" and "Official Photos". Official photos show a gold star badge in the "All" view.
- **Downloads for everyone** — per-file download button in the lightbox and "download all as ZIP" button in the header are available to all users, not just admins. The ZIP respects the active tab filter (all vs official). ZIP is streamed via `zipstream-ng` with `ZIP_STORED` (no compression) so memory stays flat on the N100 — perfect for 50GB+ archives.
- **UUID filenames** — all files stored as `{uuid}.{ext}`, original names in SQLite only
- **Thumbnails generated async** — background thread after upload. Gallery items carry a `thumbnail_ready` flag; the frontend shows a spinner placeholder and polls `POST /api/gallery/thumbnail-status` (batch) until every pending thumb is ready.
- **tus protocol** — chunked 5MB uploads with automatic retry/resume for large videos on flaky mobile connections

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `UPLOAD_PIN` | `1234` | Shared PIN for guest access |
| `ADMIN_PIN` | `admin` | PIN that unlocks admin mode (downloads, global delete). Change in prod. |
| `MAX_UPLOAD_SIZE` | `2147483648` (2GB) | Max upload size in bytes |
| `DATA_DIR` | `/data` | Storage root (uploads, thumbnails, metadata.db) |
| `SESSION_SECRET` | auto-generated | Cookie signing secret |
