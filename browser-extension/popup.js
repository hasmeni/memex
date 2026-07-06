// ironyLabs Link Saver — Browser Extension
// Compatible with Chrome, Edge, Brave, and Firefox

const api = typeof browser !== 'undefined' ? browser : chrome;
const $ = id => document.getElementById(id);

// Load saved settings
api.storage.local.get(['serverUrl', 'token'], (data) => {
  if (data.serverUrl) $('serverUrl').value = data.serverUrl;
  if (!data.token) {
    $('main-view').style.display = 'none';
    $('setup').style.display = 'block';
  }
});

// Get current tab info
api.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0]) {
    $('title').value = tabs[0].title || '';
    $('url').value = tabs[0].url || '';
  }
});

// Settings toggle
$('showSetup').onclick = () => { $('main-view').style.display = 'none'; $('setup').style.display = 'block'; };
$('backBtn').onclick = () => { $('setup').style.display = 'none'; $('main-view').style.display = 'block'; };

// Connect
$('connectBtn').onclick = async () => {
  const serverUrl = $('serverUrl').value.trim().replace(/\/$/, '');
  const password = $('password').value;
  $('setupStatus').textContent = 'Connecting...';
  $('setupStatus').className = 'status';

  try {
    const res = await fetch(`${serverUrl}/api/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `username=admin&password=${encodeURIComponent(password)}`
    });
    if (!res.ok) throw new Error('Invalid credentials');
    const data = await res.json();
    api.storage.local.set({ serverUrl, token: data.access_token });
    $('setupStatus').textContent = '✓ Connected!';
    $('setupStatus').className = 'status ok';
    setTimeout(() => {
      $('setup').style.display = 'none';
      $('main-view').style.display = 'block';
    }, 1000);
  } catch (e) {
    $('setupStatus').textContent = '✗ ' + e.message;
    $('setupStatus').className = 'status err';
  }
};

// Save link
$('saveBtn').onclick = async () => {
  const title = $('title').value.trim();
  const url = $('url').value.trim();
  const category = $('category').value.trim() || 'General';
  const tags = $('tags').value.trim();

  if (!title || !url) { $('status').textContent = 'Title and URL required'; $('status').className = 'status err'; return; }

  api.storage.local.get(['serverUrl', 'token'], async (data) => {
    if (!data.serverUrl || !data.token) {
      $('status').textContent = 'Not connected — open Settings';
      $('status').className = 'status err';
      return;
    }

    $('saveBtn').disabled = true;
    $('saveBtn').textContent = 'Saving...';
    $('status').textContent = '';

    try {
      const res = await fetch(`${data.serverUrl}/api/admin/links`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${data.token}`
        },
        body: JSON.stringify({ title, url, category, tags, icon: '🔗' })
      });

      if (res.status === 401) {
        $('status').textContent = 'Session expired — reconnect in Settings';
        $('status').className = 'status err';
      } else if (res.status === 409) {
        const err = await res.json();
        $('status').textContent = '⚠ ' + err.detail;
        $('status').className = 'status err';
      } else if (res.ok) {
        $('status').textContent = '✓ Saved!';
        $('status').className = 'status ok';
        setTimeout(() => window.close(), 1200);
      } else {
        $('status').textContent = 'Error: ' + res.status;
        $('status').className = 'status err';
      }
    } catch (e) {
      $('status').textContent = '✗ ' + e.message;
      $('status').className = 'status err';
    }

    $('saveBtn').disabled = false;
    $('saveBtn').textContent = 'Save Link';
  });
};
