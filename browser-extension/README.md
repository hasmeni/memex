# ironyLabs Link Saver — Browser Extension

## Supported Browsers

- Chrome (v88+)
- Edge (v88+)
- Brave
- Firefox (v109+)

## Installation (Chrome/Edge/Brave)

1. Open `chrome://extensions/` (or `edge://extensions/`)
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select this `browser-extension` folder
5. The extension icon appears in your toolbar

## Installation (Firefox)

1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on..."
3. Select the `manifest.json` file from this folder
4. The extension icon appears in your toolbar

**Note:** Temporary add-ons are removed when Firefox closes. For persistent install, use `web-ext run` or submit to AMO.

## Setup

1. Click the extension icon
2. Click "⚙ Settings"
3. Enter your server URL (e.g. `https://yoursite.com` or `http://localhost:8098`)
4. Enter your admin password
5. Click "Connect"

## Usage

1. Navigate to any page you want to save
2. Click the extension icon
3. Title and URL are pre-filled from the current tab
4. Optionally edit category and tags
5. Click "Save Link"

## Generating Icons

Open `generate-icons.html` in a browser, right-click each canvas, and save as `icon16.png`, `icon48.png`, `icon128.png` in this folder.

## Notes

- The extension stores your JWT token in `chrome.storage.local`
- Token expires after 24 hours — reconnect via Settings
- Duplicate URLs are detected (shows warning instead of saving)
- Works with any ironyLabs instance (local or remote)
