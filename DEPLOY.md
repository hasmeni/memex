# ironyLabs Links — Deployment Guide

**Last updated:** 2026-07-04

---

## Changelog / Fixes Applied

| Date | Fix |
|------|-----|
| 2026-07-04 | Pinned `bcrypt==4.0.1` in `requirements.txt` — `passlib 1.7.4` crashes with `bcrypt >= 4.1` due to a password-length validation change in the bcrypt library |
| 2026-07-04 | Fixed `backend/Dockerfile` — moved `mkdir -p /app/data` before `pip install` to avoid a layer corruption issue where `/bin/sh` became unavailable after installing `cryptography`/`cffi` |
| 2026-07-04 | Fixed `start.sh` — now sources the `.env` file so Docker Compose picks up your configured password instead of always using the hardcoded default |

---

## Requirements

- Docker Engine ≥ 24
- Docker Compose v2 (`docker compose` not `docker-compose`)
- Port **8098** open on your VPS firewall

---

## 1. Transfer the package to your VPS

```bash
scp ironyLabs-links-YYYYMMDD-HHMMSS.zip user@YOUR_VPS_IP:~
ssh user@YOUR_VPS_IP
unzip ironyLabs-links-*.zip -d ironylabs-links
cd ironylabs-links
```

---

## 2. Set your secrets

```bash
cp .env.example .env
nano .env
```

Fill in:

```env
ADMIN_PASSWORD=your_strong_password_here
SECRET_KEY=some_long_random_string_here
```

> **Do not skip this step.** The defaults are public.

To generate a strong secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 3. Deploy

```bash
chmod +x start.sh
./start.sh
```

Or directly:

```bash
docker compose up -d --build
```

Docker will build and start three containers:
- `ironylabs_api` — FastAPI backend + SQLite
- `ironylabs_frontend` — Nginx serving static HTML/JS
- `ironylabs_gateway` — Nginx reverse proxy on port 8098

---

## 4. Verify it's running

```bash
docker compose ps
curl http://localhost:8098/api/health
```

Expected response: `{"status":"ok"}`

All three containers should show status `Up`.

---

## 5. Access the site

| URL | Purpose |
|-----|---------|
| `http://YOUR_VPS_IP:8098` | Public links / mind map |
| `http://YOUR_VPS_IP:8098/admin.html` | Admin panel |
| `http://YOUR_VPS_IP:8098/api/health` | Health check endpoint |
| `http://YOUR_VPS_IP:8098/api/links` | Public links JSON |

Admin login:
- **Username:** `admin`
- **Password:** whatever you set in `.env`

---

## 6. Point your domain (ironylabs.studio)

Add an **A record** in your DNS pointing `ironylabs.studio` to your VPS IP address.

### Nginx reverse proxy (recommended with Certbot)

```nginx
server {
    listen 80;
    server_name ironylabs.studio www.ironylabs.studio;

    location / {
        proxy_pass http://127.0.0.1:8098;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Then get a free SSL cert:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d ironylabs.studio -d www.ironylabs.studio
```

### Caddy (auto HTTPS, easiest)

```
ironylabs.studio {
    reverse_proxy localhost:8098
}
```

Caddy handles SSL certificates automatically — no Certbot needed.

---

## 7. Managing links

Go to `/admin.html`, sign in, then:

- **Add Link** — fill in Title, URL, Category (group), Icon (emoji), Description, Sort Order
- **Edit** — click Edit on any row, modify, save
- **Delete** — click Delete, confirm
- **Hide without deleting** — uncheck "Active" when editing
- **Sort order** — lower numbers appear closer to the center on the mind map
- **Categories** — typed freely; each unique category becomes a cluster node

---

## 8. Updates

```bash
# Upload new zip and replace files, then:
docker compose up -d --build
```

Data is stored in a Docker named volume (`db_data`) and persists across rebuilds.

---

## 9. Useful commands

| Command | What it does |
|---------|--------------|
| `docker compose ps` | Check container status |
| `docker compose logs -f` | Stream live logs |
| `docker compose logs backend` | View backend logs only |
| `docker compose down` | Stop all containers |
| `docker compose restart backend` | Restart just the API |
| `docker compose up -d --build` | Rebuild and restart |
| `docker compose down -v` | Stop + wipe all data (**destructive**) |

---

## 10. Troubleshooting

### Admin login says "invalid credentials"

1. Make sure the backend container is **running** (not restarting):
   ```bash
   docker compose ps
   ```
2. Check backend logs for errors:
   ```bash
   docker compose logs backend
   ```
3. If you see a `bcrypt` or `passlib` error, ensure `bcrypt==4.0.1` is in `backend/requirements.txt` and rebuild:
   ```bash
   docker compose up -d --build backend
   ```
4. Verify your `.env` file has `ADMIN_PASSWORD` set and restart:
   ```bash
   docker compose down && docker compose up -d
   ```

### Container is in "Restarting" state

Check logs: `docker compose logs backend`. The most common cause is the `passlib`/`bcrypt` incompatibility (fixed in this release).

### Port 8098 not reachable

- Check firewall: `sudo ufw allow 8098` (Ubuntu)
- Check that the gateway container is running: `docker compose ps`

---

## Architecture

```
Browser
  └── :8098 (Nginx gateway container)
        ├── /api/*     → ironylabs_api (FastAPI on port 8000) + SQLite
        └── / (all)    → ironylabs_frontend (Nginx serving static HTML/JS)
```

Data is persisted in a Docker named volume mounted at `/app/data/links.db` inside the backend container.

---

## File Structure

```
.
├── .env.example          # Template — copy to .env
├── .env                  # Your secrets (not committed to git)
├── docker-compose.yml    # Container orchestration
├── start.sh              # Quick-start script (Linux/Mac)
├── start.ps1             # Quick-start script (Windows)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt  # Python dependencies (bcrypt pinned to 4.0.1)
│   └── main.py           # FastAPI application
├── frontend/
│   ├── Dockerfile
│   ├── nginx-frontend.conf
│   └── static/
│       ├── index.html    # Public mind map page
│       └── admin.html    # Admin panel
├── nginx/
│   └── nginx.conf        # Gateway routing config
├── DEPLOY.md             # This file
├── DEPLOY.html           # Visual deployment guide
└── ironyLabs_Animated_Wallpaper.html
```
