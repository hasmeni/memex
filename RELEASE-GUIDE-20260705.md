# Memex — Release & Distribution Guide

**Generated:** 2026-07-05 09:15:00 UTC  
**Project:** Memex (by ironyLabs)

---

## Distribution Packages

Two zip files are available for different purposes:

| File | Size | Purpose |
|------|------|---------|
| `ironyLabs-links-memex-VPS-DEPLOY-20260704.zip` | 118 KB | Deploy directly to a VPS |
| `Memex-GitHub-Release-20260705.zip` | 521 KB | Push to GitHub as a public/private repo |

---

## VPS Deployment (Quick)

Upload the VPS zip to your server and deploy:

```bash
# On your local machine — upload to VPS
scp ironyLabs-links-memex-VPS-DEPLOY-20260704.zip user@YOUR_VPS_IP:~/

# On your VPS
ssh user@YOUR_VPS_IP
unzip ironyLabs-links-memex-VPS-DEPLOY-20260704.zip -d memex
cd memex

# Configure
cp .env.example .env
nano .env
# Set: ADMIN_PASSWORD, SECRET_KEY, APP_PORT

# Deploy
docker compose up -d --build

# Verify
curl http://localhost:8098/api/health
# Expected: {"status":"ok"}
```

---

## GitHub Repository Setup

### Step 1: Extract the GitHub zip

```bash
# Windows (PowerShell)
Expand-Archive -Path "Memex-GitHub-Release-20260705.zip" -DestinationPath "memex"
cd memex

# Linux/Mac
unzip Memex-GitHub-Release-20260705.zip -d memex
cd memex
```

### Step 2: Initialize Git repository

```bash
git init
git add .
git commit -m "Initial release — Memex v1.0"
```

### Step 3: Create GitHub repo

**Option A: Via GitHub website**
1. Go to https://github.com/new
2. Repository name: `memex`
3. Description: "Self-hosted personal link collection with animated mind map, federation, and multi-device sync"
4. Choose Public or Private
5. Do NOT initialize with README (we already have one)
6. Click "Create repository"

**Option B: Via GitHub CLI**
```bash
gh repo create memex --public --description "Self-hosted personal link collection with animated mind map" --source . --push
```

### Step 4: Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/memex.git
git branch -M main
git push -u origin main
```

### Step 5: Verify

Visit `https://github.com/YOUR_USERNAME/memex` — you should see the README rendered with the feature list and quick start instructions.

---

## What's Included in Each Zip

### VPS Deploy Zip (118 KB)
```
├── backend/              # FastAPI app (main.py + Dockerfile)
├── frontend/             # Static HTML/JS/CSS + Dockerfile
├── nginx/                # Gateway config template
├── browser-extension/    # Chrome/Firefox extension source
├── docker-compose.yml    # Container orchestration
├── .env.example          # Configuration template
├── start.sh              # Linux/Mac launcher
├── start.ps1             # Windows launcher
├── DEPLOY.md             # Quick deploy guide
├── VPS-DEPLOY-GUIDE-*.md # Detailed VPS instructions
├── WIKI-USAGE-GUIDE.html # Full usage documentation
├── FINAL-FEATURES-*.md   # Feature list
├── ROADMAP-*.md          # Future plans
└── SESSION-LOG-*.md      # Development history
```

### GitHub Release Zip (521 KB)
Everything in VPS zip PLUS:
```
├── android/              # Full Kotlin source (Android companion app)
│   ├── app/src/main/     # Source code + resources
│   ├── build.gradle.kts  # Build config
│   └── gradlew.bat       # Build script
├── standalone/           # No-Docker Python runner
│   ├── run.py
│   └── requirements.txt
├── .gitignore            # Git ignore rules
├── README.md             # GitHub-friendly project README
├── FRIEND-CONNECT-*.md   # Federation guide
├── FUTURE-TASKS-*.md     # Planned features
└── RELEASE-GUIDE-*.md    # This file
```

---

## What's NOT Included (by design)

| Excluded | Why |
|----------|-----|
| `.env` | Contains secrets (password, JWT key) |
| `*.apk` | Binary build artifact — users build from source |
| `android/app/build/` | Gradle build output (regenerated on build) |
| `android/.gradle/` | Gradle cache |
| `standalone/venv/` | Python virtual environment (regenerated on install) |
| `standalone/data/` | Local database (user's data) |
| `__pycache__/` | Python bytecode cache |

---

## After Pushing to GitHub

### Recommended: Add a Release

1. Go to your repo → "Releases" → "Create a new release"
2. Tag: `v1.0.0`
3. Title: `Memex v1.0.0 — Initial Release`
4. Description: paste from README features section
5. Attach the APK file (`Memex-Share-debug.apk`) as a release asset
6. Publish

### Recommended: Add Topics

On your repo page, click the gear icon next to "About" and add topics:
```
self-hosted, bookmarks, mind-map, links, d3js, fastapi, docker, android, personal-knowledge, federation
```

### Recommended: Enable GitHub Pages (for wiki)

1. Settings → Pages → Source: "Deploy from a branch"
2. Branch: main, folder: / (root)
3. The `WIKI-USAGE-GUIDE.html` becomes accessible at `https://YOUR_USERNAME.github.io/memex/WIKI-USAGE-GUIDE.html`

---

## Deploying from GitHub (for others)

When someone clones your repo, they deploy like this:

```bash
git clone https://github.com/YOUR_USERNAME/memex.git
cd memex
cp .env.example .env
nano .env  # Set password + secret key
docker compose up -d --build
```

That's it. The README explains everything they need.

---

## Building the Android APK from Source

```bash
cd android

# Windows
set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
gradlew.bat assembleDebug

# Linux/Mac
export ANDROID_HOME=~/Android/Sdk
./gradlew assembleDebug

# Output: android/app/build/outputs/apk/debug/app-debug.apk
```

---

## Summary

| Action | Command |
|--------|---------|
| Deploy to VPS | `unzip → cp .env.example .env → edit .env → docker compose up -d --build` |
| Push to GitHub | `unzip → git init → git add . → git commit → git remote add → git push` |
| Build Android APK | `cd android → gradlew assembleDebug` |
| Load browser extension | Chrome: `chrome://extensions` → Load unpacked → select `browser-extension/` |
| Run standalone (no Docker) | `cd standalone → pip install -r requirements.txt → python run.py` |
