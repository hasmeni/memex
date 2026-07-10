# Memex
<img width="1024" height="500" alt="memex_feature_graphic_1024x500" src="https://github.com/user-attachments/assets/e7f6c43c-8128-47e2-9e6b-17d78475f7a6" />

A self-hosted personal link collection rendered as an animated mind map, with multi-view modes, sharing/federation, an Android companion app, and browser extension.
Taking inspiration from mindmaps, Linkding, Hoarder? Kerakeep, readeck, the fediverse Flame dashboard. Use it as a links bio page, dashboard, bookmark aggregator and more.
Share your board with friends. Save links while you browse the web or connect to your instance with the android app. 

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

-  **Interactive Mind Map** — D3.js force-directed graph with zoom, pan, collapsible nodes
-  **Pinboard View** — Masonry card layout
-  **Tag Cloud** — Weighted tag visualization
-  **Mobile Responsive** — Card grid with search, sort, pagination
-  **Private Links** — Hide links from public view
-  **Collections** — Curated link groups
-  **Federation** — Connect friend instances, browse shared links (read-only)
-  **Analytics** — Click tracking, heatmaps, referrer stats
-  **Themes** — 5 built-in color schemes
-  **Notes** — Markdown notes per link
-  **Health Checker** — Auto-detect dead links
-  **RSS Feed** — Atom 1.0 syndication
-  **Android App** — Share links from any app
-  **Browser Extension** — Chrome + Firefox one-click save
-  **QR Codes** — Generate for any link
-  **API Keys** — Programmatic access for scripts/bots

## Quick Start

```bash
cp .env.example .env
nano .env  # Set ADMIN_PASSWORD and SECRET_KEY
docker compose up -d --build
```

Open `http://localhost:8098` (or your configured `APP_PORT`).

## Configuration

All settings in `.env`:

```env
ADMIN_PASSWORD=your_strong_password
SECRET_KEY=long_random_string_here
APP_PORT=8098
```

## Documentation

- **[Wiki & Usage Guide](WIKI-USAGE-GUIDE.html)** — Complete feature guide with screenshots
- **[VPS Deployment](VPS-DEPLOY-GUIDE-20260704-124500.md)** — Step-by-step server setup
- **[Friend Connection](FRIEND-CONNECT-GUIDE-20260705.md)** — How to connect instances

## Architecture

```
Browser → Nginx Gateway (:8098)
            ├── /api/* → FastAPI Backend (Python + SQLite)
            └── /*     → Nginx Frontend (Static HTML/JS)
```

3 Docker containers, 1 named volume for persistence.

## Android App

Source in `android/`. Build with:
```bash
cd android
gradlew.bat assembleDebug  # Windows
./gradlew assembleDebug    # Linux/Mac
```

APK output: `android/app/build/outputs/apk/debug/app-debug.apk`

## Browser Extension

Load `browser-extension/` as unpacked extension in Chrome/Edge/Firefox.


## TO DO

- ** Partial sharing works but sharing Memex live instances with approved friends so they can view or if you give them permission, modify your web from their instance. In other words
     friends see your web as a branch within their memex instance. 

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Vanilla HTML/CSS/JS, D3.js v7
- **Mobile:** Kotlin, Material Design, OkHttp
- **Infrastructure:** Docker Compose, Nginx Alpine

## License

MIT

---

Built by [ironyLabs](https://ironylabs.studio)
