# Memex — GitHub Repository Setup Instructions

**Generated:** 2026-07-05  
**Project:** Memex (by ironyLabs)

---

## Prerequisites

- A GitHub account
- Git installed on your machine
- The `Memex-GitHub-Release-20260705.zip` file

---

## Step 1: Create the Repository on GitHub

### Option A: GitHub Website (easiest)

1. Go to **https://github.com/new**
2. Fill in:
   - **Repository name:** `memex`
   - **Description:** `Self-hosted personal link collection with animated mind map, federation, and multi-device sync`
   - **Visibility:** Public (or Private)
   - **DO NOT** check "Add a README" (we already have one)
   - **DO NOT** check "Add .gitignore" (we already have one)
   - **DO NOT** choose a license (already in README)
3. Click **"Create repository"**
4. You'll see a page with push instructions — follow Step 2 below

### Option B: GitHub CLI

If you have the `gh` CLI installed:

```bash
gh auth login
gh repo create memex --public --description "Self-hosted personal link collection with animated mind map, federation, and multi-device sync"
```

---

## Step 2: Extract the Release Zip

### Windows (PowerShell)
```powershell
Expand-Archive -Path "Memex-GitHub-Release-20260705.zip" -DestinationPath "memex"
cd memex
```

### Linux / Mac
```bash
unzip Memex-GitHub-Release-20260705.zip -d memex
cd memex
```

---

## Step 3: Initialize Git and Push

```bash
git init
git add .
git commit -m "Initial release — Memex v1.0"
git remote add origin https://github.com/YOUR_USERNAME/memex.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 4: Verify

1. Visit `https://github.com/YOUR_USERNAME/memex`
2. You should see the README.md rendered with features, quick start, and architecture
3. All source code visible (backend, frontend, android, browser-extension, etc.)

---

## Step 5 (Optional): Create a Release

1. Go to your repo → **Releases** → **"Create a new release"**
2. Click **"Choose a tag"** → type `v1.0.0` → click "Create new tag"
3. **Title:** `Memex v1.0.0 — Initial Release`
4. **Description:**
```
## Memex v1.0.0

Self-hosted personal link collection with animated mind map.

### Highlights
- 79+ features
- D3.js force-directed mind map with 5 themes
- Android companion app (APK attached)
- Chrome/Firefox browser extension
- Federation (connect friend instances)
- Docker Compose deployment

### Deploy
\```
cp .env.example .env
nano .env
docker compose up -d --build
\```
```
5. **Attach files:**
   - Drag `Memex-Share-debug.apk` into the upload area
   - Drag `ironyLabs-links-memex-VPS-DEPLOY-20260704.zip` into the upload area
6. Click **"Publish release"**

---

## Step 6 (Optional): Add Repository Topics

1. On your repo page, click the ⚙️ gear next to "About"
2. Add topics:
```
self-hosted, bookmarks, mind-map, links, d3js, fastapi, docker, android, personal-knowledge, federation, link-manager
```
3. Click "Save changes"

---

## Step 7 (Optional): Enable GitHub Pages

If you want the wiki accessible as a web page:

1. Go to Settings → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, folder: `/ (root)`
4. Click Save
5. After a minute, your wiki is live at:
   - `https://YOUR_USERNAME.github.io/memex/WIKI-USAGE-GUIDE.html`
   - `https://YOUR_USERNAME.github.io/memex/WIKI-STYLED.html`

---

## Updating the Repo Later

When you make changes and want to push:

```bash
cd memex
git add .
git commit -m "Description of changes"
git push
```

---

## Summary Checklist

```
□ Create repo on GitHub (github.com/new)
□ Extract zip locally
□ git init → add → commit → push
□ Verify README shows on GitHub
□ (Optional) Create v1.0.0 release with APK attached
□ (Optional) Add topics for discoverability
□ (Optional) Enable GitHub Pages for wiki
```
