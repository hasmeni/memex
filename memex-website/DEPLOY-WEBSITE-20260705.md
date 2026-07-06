# Memex Website — Deployment Guide

**Generated:** 2026-07-05 15:30:00 UTC  
**Default Port:** 8047  
**Default Admin Password:** admin123

---

## Prerequisites

- Docker Engine 24+
- Docker Compose v2 (`docker compose`)
- Port 8047 available (or your chosen port)

---

## Quick Deploy

```bash
cd memex-website
cp .env.example .env
nano .env       # edit credentials + port
docker compose up -d --build
```

Open `http://localhost:8047` — the site is live.

---

## Configuration (.env file)

All settings are in one file:

```bash
cp .env.example .env
nano .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_PASSWORD` | `admin123` | Password for the admin panel |
| `SECRET_KEY` | `website_secret_change_me` | JWT signing key (use a long random string) |
| `APP_PORT` | `8047` | Port the website runs on |
| `GITHUB_REPO` | _(empty)_ | Your GitHub repo path (e.g. `username/memex`) for live star count |

### Changing the Port

Edit `.env`:
```env
APP_PORT=9090
```

Restart:
```bash
docker compose down && docker compose up -d
```

Site now available at `http://localhost:9090`.

### Changing the Admin Password

Edit `.env`:
```env
ADMIN_PASSWORD=your_strong_password_here
```

Restart:
```bash
docker compose down && docker compose up -d
```

### Setting Up GitHub Stars

Edit `.env`:
```env
GITHUB_REPO=yourusername/memex
```

The landing page fetches the live star count from GitHub's API on every page load — accurate and dynamic.

**Notes:**
- Shows "—" until `GITHUB_REPO` is set
- Updates every time a visitor loads the page (no caching)
- GitHub's public API allows 60 requests/hour per IP — sufficient for most personal sites
- If rate limited, the count briefly shows "—" until the limit resets
- No rebuild needed — just restart after editing `.env`: `docker compose restart`

---

## Accessing the Admin Panel

The admin panel is at `/admin.html` — there is **no visible link** to it on the public site.

```
URL: http://localhost:8047/admin.html
Username: admin (hardcoded)
Password: whatever you set in ADMIN_PASSWORD
```

### What You Can Edit from Admin

| Section | What it controls |
|---------|-----------------|
| **Hero Section** | Title, subtitle, CTA button text + URL |
| **Features** | Feature cards (JSON array of {icon, title, desc}) |
| **Screenshots** | Screenshot file paths (JSON array) |
| **Footer** | Footer text |
| **Wiki Pages** | Create, edit, delete documentation pages (markdown) |

---

## Site URLs

| URL | Purpose | Public? |
|-----|---------|---------|
| `/` | Landing page (hero, features, screenshots) | ✅ Yes |
| `/wiki.html` | Documentation viewer (sidebar + markdown) | ✅ Yes |
| `/admin.html` | Content management panel | ❌ Hidden (no link) |
| `/api/health` | Health check endpoint | ✅ Yes |
| `/api/content` | Landing page content (JSON) | ✅ Yes |
| `/api/wiki` | Wiki page list | ✅ Yes |
| `/api/wiki/{slug}` | Wiki page content | ✅ Yes |

---

## Adding Screenshots

1. Place screenshot images in the `screenshots/` folder
2. In admin → Screenshots field, update the JSON array:
```json
["screenshots/my-screenshot.png", "screenshots/another.png"]
```
3. Save — screenshots appear on the landing page immediately

---

## Adding Wiki Pages

1. Go to `/admin.html` → Wiki Pages tab
2. Enter:
   - **Slug:** URL-friendly name (e.g. `getting-started`)
   - **Title:** Display title
   - **Content:** Markdown (supports headings, code, links, tables)
   - **Sort Order:** Controls sidebar order
3. Click "Save Page"
4. Visit `/wiki.html` — the page appears in the sidebar

---

## Deploying on a VPS

```bash
# Upload the memex-website folder to your VPS
scp -r memex-website/ user@YOUR_VPS_IP:~/

# SSH in
ssh user@YOUR_VPS_IP
cd memex-website

# Configure
cp .env.example .env
nano .env

# Deploy
docker compose up -d --build

# Verify
curl http://localhost:8047/api/health
```

### With a Domain (Caddy)

```
yourdomain.com {
    reverse_proxy localhost:8047
}
```

### With a Domain (Nginx + Certbot)

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:8047;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Then: `sudo certbot --nginx -d yourdomain.com`

---

## Architecture

```
Browser → Nginx Gateway (:8047)
            ├── /api/*  → FastAPI Backend (content + wiki API)
            └── /*      → Nginx Frontend (static HTML/JS/CSS)
```

3 Docker containers, 1 named volume (`web_data`) for the SQLite database.

---

## File Structure

```
memex-website/
├── backend/
│   ├── Dockerfile
│   ├── main.py           # API (content, wiki, auth)
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── nginx-frontend.conf
│   └── static/
│       ├── index.html    # Landing page
│       ├── wiki.html     # Documentation viewer
│       └── admin.html    # Admin panel (hidden)
├── nginx/
│   └── nginx.conf.template
├── screenshots/          # Your app screenshots
├── docker-compose.yml
├── .env.example
└── .env                  # Your secrets (not committed)
```

---

## Useful Commands

| Command | What it does |
|---------|--------------|
| `docker compose up -d --build` | Build and start |
| `docker compose down` | Stop all containers |
| `docker compose logs -f` | Stream live logs |
| `docker compose restart` | Restart all |
| `curl http://localhost:8047/api/health` | Health check |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port already in use | Change `APP_PORT` in `.env` |
| Admin login fails | Check `ADMIN_PASSWORD` in `.env`, restart containers |
| Screenshots not showing | Verify files exist in `screenshots/` folder and JSON paths match |
| Wiki pages empty | Go to admin, check page is set to "published: true" |
| Container restarting | `docker compose logs backend` to see the error |
