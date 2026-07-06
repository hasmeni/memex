/* Memex Mind Map ─ mindmap.js */

const API = '/api';
let ORANGE = '#FF7A29';
let ORANGE_LIGHT = '#FFA35C';

const CAT_PALETTE = [
  '#FF7A29','#FFA35C','#e04fc0','#4fc0e0','#7ae83e',
  '#e8d43e','#a78bfa','#f87171','#34d399','#60a5fa'
];

let allLinks = [];
let activeCategory = 'All';
let customCatColors = {};
let customCatIcons = {};
let currentTheme = {};
let collapsedCategories = new Set();
const MAX_LINKS_PER_CAT = 10;
const PERF_THRESHOLD = 50; // disable animations above this node count

// ── Theme Loading ────────────────────────────────────────────────────────────
async function loadTheme() {
  try {
    const res = await fetch(`${API}/settings/theme`);
    if (res.ok) {
      const data = await res.json();
      currentTheme = data.theme;
      applyTheme(data.theme);
    }
  } catch(e) {}
}

function applyTheme(theme) {
  const root = document.documentElement;
  root.style.setProperty('--bg', theme.bg || '#0a0a0a');
  root.style.setProperty('--accent', theme.accent || '#FF7A29');
  root.style.setProperty('--accent-light', theme.accentLight || '#FFA35C');
  root.style.setProperty('--text', theme.text || '#ffffff');
  root.style.setProperty('--glow-color', theme.glowColor || 'rgba(255,122,41,0.12)');
  ORANGE = theme.accent || '#FF7A29';
  ORANGE_LIGHT = theme.accentLight || '#FFA35C';
  document.querySelectorAll('.particle').forEach(p => p.style.background = ORANGE);
}

// ── Particles ────────────────────────────────────────────────────────────────
(function spawnParticles() {
  const container = document.getElementById('particles');
  for (let i = 0; i < 26; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const size = 2 + Math.random() * 3;
    p.style.cssText = `width:${size}px;height:${size}px;left:${Math.random()*100}vw;top:${60+Math.random()*40}vh`;
    const dur = 12 + Math.random() * 14;
    p.style.animationDuration = dur + 's';
    p.style.animationDelay = (Math.random() * dur) + 's';
    container.appendChild(p);
  }
})();

// ── Fetch links ───────────────────────────────────────────────────────────────
async function fetchLinks() {
  try {
    const [linksRes, catsRes] = await Promise.all([
      fetch(`${API}/links`),
      fetch(`${API}/categories`)
    ]);
    if (!linksRes.ok) throw new Error('API error');
    allLinks = await linksRes.json();
    if (catsRes.ok) {
      const cats = await catsRes.json();
      cats.forEach(c => {
        if (c.color) customCatColors[c.name] = c.color;
        if (c.icon_url) customCatIcons[c.name] = c.icon_url;
      });
    }
  } catch (e) {
    console.warn('Could not fetch links:', e);
    allLinks = [];
  }
  buildCategoryBars();
  renderMindMap();
  renderMobileGrid();
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function getCategories() {
  return ['All', ...new Set(allLinks.map(l => l.category))];
}

function catColor(cat) {
  if (customCatColors[cat]) return customCatColors[cat];
  const cats = [...new Set(allLinks.map(l => l.category))];
  const idx = cats.indexOf(cat);
  return CAT_PALETTE[idx % CAT_PALETTE.length];
}

function filteredLinks() {
  return activeCategory === 'All' ? allLinks : allLinks.filter(l => l.category === activeCategory);
}

function isRecentlyAdded(link) {
  if (!link.created_at) return false;
  const created = new Date(link.created_at);
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  return created > sevenDaysAgo;
}

// ── Category bar ─────────────────────────────────────────────────────────────
function buildCategoryBars() {
  const bar = document.getElementById('cat-bar');
  bar.innerHTML = '';
  getCategories().forEach(cat => {
    const btn = document.createElement('button');
    btn.className = 'cat-btn' + (cat === activeCategory ? ' active' : '');
    btn.textContent = cat;
    btn.onclick = () => {
      activeCategory = cat;
      document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderMindMap();
    };
    bar.appendChild(btn);
  });
  const mBar = document.getElementById('mobile-cat-bar');
  mBar.innerHTML = '';
  getCategories().forEach(cat => {
    const btn = document.createElement('button');
    btn.className = 'cat-btn' + (cat === activeCategory ? ' active' : '');
    btn.textContent = cat;
    btn.onclick = () => {
      activeCategory = cat;
      document.querySelectorAll('#mobile-cat-bar .cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      mobileVisibleCount = MOBILE_PAGE_SIZE;
      renderMobileGrid();
    };
    mBar.appendChild(btn);
  });
}

// ── Mobile grid ──────────────────────────────────────────────────────────────
const MOBILE_PAGE_SIZE = 15;
let mobileVisibleCount = MOBILE_PAGE_SIZE;
let mobileSortMode = 'default'; // default, name, clicks, recent

function renderMobileGrid() {
  const grid = document.getElementById('link-cards');
  const showMoreBtn = document.getElementById('mobile-show-more');
  grid.innerHTML = '';

  // Determine source links
  let links;
  if (mobileCollectionLinks) {
    links = mobileCollectionLinks;
  } else {
    links = filteredLinks();
  }

  // Apply tag filter
  if (mobileTagFilter) {
    links = links.filter(l => l.tags && l.tags.split(',').map(t => t.trim()).includes(mobileTagFilter));
  }

  // Sort
  if (mobileSortMode === 'name') {
    links = [...links].sort((a, b) => a.title.localeCompare(b.title));
  } else if (mobileSortMode === 'clicks') {
    links = [...links].sort((a, b) => (b.click_count || 0) - (a.click_count || 0));
  } else if (mobileSortMode === 'recent') {
    links = [...links].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }

  const visible = links.slice(0, mobileVisibleCount);
  const hasMore = links.length > mobileVisibleCount;

  visible.forEach(link => {
    const a = document.createElement('a');
    a.className = 'link-card';
    a.href = link.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.dataset.title = link.title;
    a.addEventListener('click', () => {
      fetch(`${API}/links/${link.id}/click`, { method: 'POST' }).catch(() => {});
    });

    // Long-press to open notes
    let pressTimer = null;
    a.addEventListener('touchstart', (e) => {
      if (!link.notes) return;
      pressTimer = setTimeout(() => {
        e.preventDefault();
        openNotesPanel(link);
      }, 600);
    }, { passive: false });
    a.addEventListener('touchend', () => { clearTimeout(pressTimer); });
    a.addEventListener('touchmove', () => { clearTimeout(pressTimer); });

    const badges = [];
    if (isRecentlyAdded(link)) badges.push('<span class="badge-new">NEW</span>');
    if (link.featured) badges.push('<span class="badge-featured">★</span>');
    a.innerHTML = `
      <div class="link-card-icon">${link.icon}</div>
      <div class="link-card-title">${link.title}</div>
      <div class="link-card-cat">${link.category}</div>
      ${badges.length ? '<div class="link-card-badges">' + badges.join('') + '</div>' : ''}
      ${link.notes ? '<div class="link-card-notes-hint">hold for notes</div>' : ''}
    `;
    grid.appendChild(a);
  });

  // Show More button
  if (hasMore) {
    showMoreBtn.style.display = 'block';
    showMoreBtn.textContent = `Show more (${links.length - mobileVisibleCount} remaining)`;
  } else {
    showMoreBtn.style.display = 'none';
  }

  buildAlphaNav(links);
  buildSortBar();
}

// Show More handler
document.getElementById('mobile-show-more').addEventListener('click', () => {
  mobileVisibleCount += MOBILE_PAGE_SIZE;
  renderMobileGrid();
});


// ── Mind Map ─────────────────────────────────────────────────────────────────
const tooltip = document.getElementById('node-tooltip');
const ttTitle = document.getElementById('tt-title');
const ttDesc = document.getElementById('tt-desc');
const ttUrl = document.getElementById('tt-url');

function renderMindMap() {
  const canvas = document.getElementById('mindmap-canvas');
  canvas.innerHTML = '';

  const W = window.innerWidth;
  const H = window.innerHeight;
  const CX = W / 2;
  const CY = H / 2;

  const allFiltered = filteredLinks();
  const cats = [...new Set(allFiltered.map(l => l.category))];

  // Build graph with pagination + collapsible categories
  const nodes = [{ id: '__root__', type: 'root' }];
  const edges = [];

  cats.forEach(cat => {
    const catLinks = allFiltered.filter(l => l.category === cat);
    const isCollapsed = collapsedCategories.has(cat);
    const visibleLinks = isCollapsed ? [] : catLinks.slice(0, MAX_LINKS_PER_CAT);
    const hiddenCount = isCollapsed ? catLinks.length : Math.max(0, catLinks.length - MAX_LINKS_PER_CAT);

    nodes.push({
      id: `cat__${cat}`, type: 'category', label: cat,
      color: catColor(cat), collapsed: isCollapsed,
      totalCount: catLinks.length, hiddenCount
    });
    edges.push({ source: '__root__', target: `cat__${cat}`, type: 'root-cat' });

    visibleLinks.forEach(link => {
      nodes.push({ id: `link__${link.id}`, type: 'link', link, color: catColor(cat) });
      edges.push({ source: `cat__${cat}`, target: `link__${link.id}`, type: 'cat-link' });
    });
  });

  const totalNodes = nodes.length;
  const highPerf = totalNodes > PERF_THRESHOLD;

  // Dynamic force tuning based on node count
  const chargeStrength = totalNodes > 100 ? -500 : totalNodes > 50 ? -400 : -320;
  const linkDistRoot = totalNodes > 50 ? 220 : 160;
  const linkDistLeaf = totalNodes > 50 ? 130 : 100;
  const collisionRoot = totalNodes > 50 ? 60 : 50;
  const collisionCat = totalNodes > 50 ? 50 : 40;
  const collisionLink = totalNodes > 50 ? 38 : 32;

  const svg = d3.select(canvas).append('svg')
    .attr('width', W).attr('height', H);

  // Zoom + Pan
  const zoomGroup = svg.append('g');
  const zoom = d3.zoom()
    .scaleExtent([0.3, 4])
    .on('zoom', (event) => { zoomGroup.attr('transform', event.transform); });
  svg.call(zoom);

  // Defs
  const defs = svg.append('defs');
  defs.append('filter').attr('id', 'glow')
    .append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur');
  const feMerge = defs.select('filter').append('feMerge');
  feMerge.append('feMergeNode').attr('in', 'coloredBlur');
  feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

  // Featured glow filter
  const featFilter = defs.append('filter').attr('id', 'featGlow');
  featFilter.append('feGaussianBlur').attr('stdDeviation', '5').attr('result', 'glow');
  const fm2 = featFilter.append('feMerge');
  fm2.append('feMergeNode').attr('in', 'glow');
  fm2.append('feMergeNode').attr('in', 'SourceGraphic');

  const rg = defs.append('radialGradient').attr('id', 'rootGrad')
    .attr('cx','50%').attr('cy','50%').attr('r','50%');
  rg.append('stop').attr('offset','0%').style('stop-color', ORANGE_LIGHT).style('stop-opacity','0.55');
  rg.append('stop').attr('offset','100%').style('stop-color', ORANGE).style('stop-opacity','0');

  // Background grid (skip if high perf mode)
  if (!highPerf) {
    const grid = zoomGroup.append('g').attr('opacity', 0.05);
    for (let x = 0; x < W; x += 170) grid.append('line').attr('x1',x).attr('x2',x).attr('y1',0).attr('y2',H).attr('stroke',ORANGE).attr('stroke-width',0.5);
    for (let y = 0; y < H; y += 170) grid.append('line').attr('x1',0).attr('x2',W).attr('y1',y).attr('y2',y).attr('stroke',ORANGE).attr('stroke-width',0.5);
  }

  // Simulation with dynamic forces
  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id)
      .distance(d => d.type === 'root-cat' ? linkDistRoot : linkDistLeaf).strength(0.8))
    .force('charge', d3.forceManyBody().strength(chargeStrength))
    .force('center', d3.forceCenter(CX, CY))
    .force('collision', d3.forceCollide().radius(d =>
      d.type === 'root' ? collisionRoot : d.type === 'category' ? collisionCat : collisionLink))
    .alphaDecay(highPerf ? 0.04 : 0.025);

  // Edges
  const edgeGroup = zoomGroup.append('g');
  const edgeSel = edgeGroup.selectAll('line')
    .data(edges).join('line')
    .attr('stroke', d => d.type === 'root-cat' ? ORANGE : ORANGE_LIGHT)
    .attr('stroke-width', d => d.type === 'root-cat' ? 1.5 : 0.8)
    .attr('stroke-opacity', d => d.type === 'root-cat' ? 0.4 : 0.25);

  if (!highPerf) edgeSel.attr('filter', 'url(#glow)');

  // Pulse dots (only if not high perf)
  const pulseDots = [];
  if (!highPerf) {
    edges.filter(e => e.type === 'root-cat').forEach((e, i) => {
      const dot = edgeGroup.append('circle')
        .attr('r', 3).attr('fill', ORANGE_LIGHT).attr('opacity', 0)
        .attr('filter', 'url(#glow)');
      pulseDots.push({ dot, edge: e, phase: i * 0.4 });
    });
  }

  // Node groups
  const nodeGroup = zoomGroup.append('g');
  const nodeSel = nodeGroup.selectAll('g')
    .data(nodes).join('g')
    .attr('cursor', d => d.type === 'link' ? 'pointer' : d.type === 'category' ? 'pointer' : 'default')
    .call(d3.drag()
      .on('start', (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
      .on('drag', (event, d) => { d.fx=event.x; d.fy=event.y; })
      .on('end', (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }));

  // Root node
  const rootSel = nodeSel.filter(d => d.type === 'root');
  rootSel.append('circle').attr('r', 44).attr('fill', 'url(#rootGrad)').attr('opacity', 0.9);
  rootSel.append('circle').attr('r', 38).attr('fill', 'url(#rootGrad)').attr('opacity', 0.6);
  if (!highPerf) {
    rootSel.append('circle').attr('r', 28).attr('fill','none').attr('stroke', ORANGE).attr('stroke-width', 2)
      .append('animate').attr('attributeName','r').attr('values','28;44;28').attr('dur','1.8s').attr('repeatCount','indefinite');
  }
  rootSel.append('circle').attr('r', 18).attr('fill','none').attr('stroke', ORANGE).attr('stroke-width', 2);
  rootSel.append('path').attr('d','M -6,-9 L -6,9 L 11,0 Z').attr('fill', ORANGE).attr('stroke','none');
  rootSel.append('line').attr('x1',0).attr('y1',-19).attr('x2',0).attr('y2',-28).attr('stroke',ORANGE).attr('stroke-width',2);
  rootSel.append('circle').attr('cy',-26).attr('r',3).attr('fill',ORANGE_LIGHT);

  // Category nodes (clickable to collapse/expand)
  const catSel = nodeSel.filter(d => d.type === 'category');
  catSel.each(function(d) {
    const g = d3.select(this);
    const catIconUrl = customCatIcons[d.label] || '';

    g.append('circle').attr('r', 26).attr('fill', 'rgba(0,0,0,0.6)')
     .attr('stroke', d.color).attr('stroke-width', 1.5).attr('opacity', 0.85)
     .attr('filter', highPerf ? null : 'url(#glow)');

    if (!highPerf) {
      const pulse = g.append('circle').attr('r', 26).attr('fill','none')
        .attr('stroke', d.color).attr('stroke-width', 1).attr('opacity', 0.4);
      pulse.append('animate').attr('attributeName','r').attr('values','26;34;26').attr('dur','2.5s').attr('repeatCount','indefinite');
      pulse.append('animate').attr('attributeName','opacity').attr('values','0.4;0;0.4').attr('dur','2.5s').attr('repeatCount','indefinite');
    }

    if (catIconUrl) {
      // Show uploaded category icon
      g.append('image').attr('href', catIconUrl)
       .attr('x', -12).attr('y', -18).attr('width', 24).attr('height', 24)
       .attr('clip-path', 'circle(12px)');
      // Label below icon
      g.append('text').attr('text-anchor','middle').attr('dy','18px')
       .attr('font-family','Caveat, cursive').attr('font-size','11px')
       .attr('fill', d.color).attr('font-weight','700')
       .text(d.label.length > 10 ? d.label.slice(0,10) + '…' : d.label);
    } else {
      const label = d.label.length > 10 ? d.label.slice(0,10) + '…' : d.label;
      g.append('text').attr('text-anchor','middle').attr('dy', d.collapsed ? '0' : '4px')
       .attr('font-family','Caveat, cursive').attr('font-size','14px')
       .attr('fill', d.color).attr('font-weight','700').text(label);
    }

    // Show count badge if collapsed or has hidden links
    if (d.collapsed || d.hiddenCount > 0) {
      const countText = d.collapsed ? d.totalCount : '+' + d.hiddenCount;
      const badgeY = catIconUrl ? '28px' : (d.collapsed ? '16px' : '18px');
      g.append('text').attr('text-anchor','middle').attr('dy', badgeY)
       .attr('font-family','Inter, sans-serif').attr('font-size','10px')
       .attr('fill', d.color).attr('opacity', 0.6).text(countText);
    }
  });

  // Click category to collapse/expand
  catSel.on('click', (event, d) => {
    event.stopPropagation();
    const catName = d.label;
    if (collapsedCategories.has(catName)) {
      collapsedCategories.delete(catName);
    } else {
      collapsedCategories.add(catName);
    }
    renderMindMap();
  });

  // Link nodes with featured/new badges
  const linkSel = nodeSel.filter(d => d.type === 'link');
  linkSel.each(function(d) {
    const g = d3.select(this);
    const isFeatured = d.link.featured;
    const isNew = isRecentlyAdded(d.link);
    const nodeR = isFeatured ? 24 : 20;

    // Hover glow bg
    g.append('circle').attr('r', nodeR + 2).attr('fill', 'rgba(0,0,0,0)')
     .attr('stroke', 'none').attr('class', 'hover-bg');

    // Featured outer glow ring
    if (isFeatured) {
      g.append('circle').attr('r', nodeR + 4).attr('fill', 'none')
       .attr('stroke', d.color).attr('stroke-width', 1.5).attr('opacity', 0.5)
       .attr('filter', 'url(#featGlow)');
    }

    // "New" pulsing ring
    if (isNew && !highPerf) {
      const newRing = g.append('circle').attr('r', nodeR).attr('fill','none')
        .attr('stroke', '#34d399').attr('stroke-width', 2).attr('opacity', 0.7);
      newRing.append('animate').attr('attributeName','r').attr('values', `${nodeR};${nodeR+8};${nodeR}`).attr('dur','2s').attr('repeatCount','indefinite');
      newRing.append('animate').attr('attributeName','opacity').attr('values','0.7;0;0.7').attr('dur','2s').attr('repeatCount','indefinite');
    }

    // Main circle
    g.append('circle').attr('r', nodeR).attr('fill', 'rgba(10,10,10,0.75)')
     .attr('stroke', d.color).attr('stroke-width', isFeatured ? 2 : 1.2).attr('opacity', 0.9)
     .attr('filter', highPerf ? null : 'url(#glow)');

    // Favicon or emoji
    if (d.link.favicon_url) {
      g.append('image').attr('href', d.link.favicon_url)
       .attr('x', -10).attr('y', -10).attr('width', 20).attr('height', 20)
       .attr('clip-path', 'circle(10px)');
    } else {
      g.append('text').attr('text-anchor','middle').attr('dy','5px')
       .attr('font-size','15px').text(d.link.icon || '🔗');
    }

    // Notes indicator dot
    if (d.link.notes) {
      g.append('circle').attr('r', 4).attr('cx', nodeR - 4).attr('cy', -(nodeR - 4))
       .attr('fill', d.color).attr('opacity', 0.8);
    }

    // "NEW" text badge
    if (isNew) {
      g.append('text').attr('x', 0).attr('y', nodeR + 14)
       .attr('text-anchor','middle').attr('font-size','8px')
       .attr('fill','#34d399').attr('font-family','Inter,sans-serif')
       .attr('font-weight','600').text('NEW');
    }
  });

  // Hover interactions for link nodes
  linkSel
    .on('mouseenter', function(event, d) {
      const nodeR = d.link.featured ? 24 : 20;
      d3.select(this).select('circle:nth-child(2)')
        .attr('stroke-width', 2.5).attr('opacity', 1);
      d3.select(this).select('.hover-bg').attr('fill', `${d.color}22`);

      ttTitle.textContent = d.link.title;
      ttDesc.textContent = d.link.description || '';
      const tagsStr = d.link.tags ? d.link.tags.split(',').map(t => t.trim()).filter(Boolean).join(' · ') : '';
      ttUrl.textContent = d.link.url.replace(/^https?:\/\//, '') + (tagsStr ? ' | ' + tagsStr : '');
      positionTooltip(event);
      tooltip.classList.add('visible');
    })
    .on('mousemove', positionTooltip)
    .on('mouseleave', function(event, d) {
      const isFeatured = d.link.featured;
      d3.select(this).select('circle:nth-child(2)')
        .attr('stroke-width', isFeatured ? 2 : 1.2).attr('opacity', 0.9);
      d3.select(this).select('.hover-bg').attr('fill', 'rgba(0,0,0,0)');
      tooltip.classList.remove('visible');
    })
    .on('click', (event, d) => {
      fetch(`${API}/links/${d.link.id}/click`, { method: 'POST' }).catch(() => {});
      window.open(d.link.url, '_blank', 'noopener,noreferrer');
    })
    .on('dblclick', (event, d) => {
      event.preventDefault();
      showQrCode(d.link);
    })
    .on('contextmenu', (event, d) => {
      if (d.link.notes) {
        event.preventDefault();
        openNotesPanel(d.link);
      }
    });

  function positionTooltip(event) {
    const x = event.clientX + 16;
    const y = event.clientY - 10;
    tooltip.style.left = (x + 220 > window.innerWidth ? x - 252 : x) + 'px';
    tooltip.style.top = y + 'px';
  }

  // Simulation tick (throttled in high perf mode)
  let frame = 0;
  sim.on('tick', () => {
    frame++;
    // Throttle DOM updates in high perf mode
    if (highPerf && frame % 2 !== 0) return;

    edgeSel
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);

    nodeSel.attr('transform', d => `translate(${d.x},${d.y})`);

    // Pulse dots (only in normal mode)
    if (!highPerf) {
      pulseDots.forEach(({ dot, edge, phase }) => {
        const t = ((frame * 0.008 + phase) % 1);
        const sx = edge.source.x, sy = edge.source.y;
        const tx = edge.target.x, ty = edge.target.y;
        dot.attr('cx', sx + (tx - sx) * t).attr('cy', sy + (ty - sy) * t)
           .attr('opacity', Math.sin(t * Math.PI) * 0.85);
      });
    }
  });

  // Resize handler
  window.addEventListener('resize', () => renderMindMap(), { once: true });

  // Zoom reset button
  let resetBtn = document.getElementById('zoom-reset-btn');
  if (!resetBtn) {
    resetBtn = document.createElement('button');
    resetBtn.id = 'zoom-reset-btn';
    resetBtn.className = 'zoom-reset';
    resetBtn.textContent = '⟲';
    resetBtn.title = 'Reset zoom';
    resetBtn.onclick = () => svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
    document.body.appendChild(resetBtn);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadTheme().then(() => fetchLinks().then(() => {
  loadSiteHeader();
  renderLinkOfDay();
  const savedView = localStorage.getItem('il_view') || 'map';
  switchView(savedView);
}));

// ── Notes Panel ──────────────────────────────────────────────────────────────
function openNotesPanel(link) {
  const panel = document.getElementById('notes-panel');
  document.getElementById('notes-panel-title').textContent = link.title;
  document.getElementById('notes-panel-meta').textContent = `${link.category} · ${link.url.replace(/^https?:\/\//, '')}`;
  const content = document.getElementById('notes-panel-content');
  if (typeof marked !== 'undefined') {
    content.innerHTML = marked.parse(link.notes);
  } else {
    content.textContent = link.notes;
  }
  panel.classList.add('open');
}

function closeNotesPanel() {
  document.getElementById('notes-panel').classList.remove('open');
}

// ── Sort Bar ─────────────────────────────────────────────────────────────────
function buildSortBar() {
  const bar = document.getElementById('mobile-sort-bar');
  bar.innerHTML = '';
  const sorts = [
    { id: 'default', label: 'Default' },
    { id: 'name', label: 'A–Z' },
    { id: 'clicks', label: 'Popular' },
    { id: 'recent', label: 'Recent' },
  ];
  sorts.forEach(s => {
    const btn = document.createElement('button');
    btn.className = 'sort-btn' + (mobileSortMode === s.id ? ' active' : '');
    btn.textContent = s.label;
    btn.onclick = () => {
      mobileSortMode = s.id;
      mobileVisibleCount = MOBILE_PAGE_SIZE;
      renderMobileGrid();
    };
    bar.appendChild(btn);
  });
}

// ── Alpha Nav ────────────────────────────────────────────────────────────────
function buildAlphaNav(links) {
  const nav = document.getElementById('alpha-nav');
  nav.innerHTML = '';
  const letters = new Set(links.map(l => l.title.charAt(0).toUpperCase()).filter(c => /[A-Z]/.test(c)));
  const sorted = [...letters].sort();
  if (sorted.length < 3) { nav.style.display = 'none'; return; }

  sorted.forEach(letter => {
    const span = document.createElement('span');
    span.textContent = letter;
    span.onclick = () => {
      const card = document.querySelector(`.link-card[data-title^="${letter}"], .link-card[data-title^="${letter.toLowerCase()}"]`);
      if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };
    nav.appendChild(span);
  });
}

// ── QR Code ──────────────────────────────────────────────────────────────────
function showQrCode(link) {
  const modal = document.getElementById('qr-modal');
  document.getElementById('qr-title').textContent = link.title;
  document.getElementById('qr-url').textContent = link.url;

  // Clear previous QR
  const container = document.getElementById('qr-canvas');
  container.innerHTML = '';

  if (typeof QRCode !== 'undefined') {
    new QRCode(container, {
      text: link.url,
      width: 200,
      height: 200,
      colorDark: '#FF7A29',
      colorLight: '#ffffff',
      correctLevel: QRCode.CorrectLevel.M
    });
  }
  modal.classList.add('open');
}

function closeQrModal() {
  document.getElementById('qr-modal').classList.remove('open');
}

// ── View Switching ───────────────────────────────────────────────────────────
let currentView = 'map';

function switchView(view) {
  currentView = view;
  localStorage.setItem('il_view', view);
  const canvas = document.getElementById('mindmap-canvas');
  const board = document.getElementById('pinboard-view');
  const tags = document.getElementById('tagcloud-view');
  const catBar = document.getElementById('cat-bar');

  if (canvas) canvas.style.display = view === 'map' ? 'block' : 'none';
  if (board) board.style.display = view === 'board' ? 'block' : 'none';
  if (tags) tags.style.display = view === 'tags' ? 'flex' : 'none';
  if (catBar) catBar.style.display = view !== 'tags' ? 'flex' : 'none';

  document.querySelectorAll('.view-btn').forEach(b => b.classList.toggle('active', b.dataset && b.dataset.view === view));

  if (view === 'board') renderPinboard();
  if (view === 'tags') renderTagCloud();
  if (view === 'map') renderMindMap();
}

// ── Pinboard View ────────────────────────────────────────────────────────────
function renderPinboard() {
  const grid = document.getElementById('pinboard-grid');
  if (!grid) return;
  const links = filteredLinks();
  grid.innerHTML = links.map(l => {
    const tags = l.tags ? l.tags.split(',').filter(t => t.trim()).map(t => `<span class="tag-badge">${t.trim()}</span>`).join('') : '';
    return `<div class="pin-card ${l.featured ? 'featured' : ''}" onclick="trackAndOpen(${l.id},'${l.url.replace(/'/g, "\\'")}')" oncontextmenu="event.preventDefault();openNotesPanelById(${l.id})">
      ${l.favicon_url ? `<img src="${l.favicon_url}" style="width:20px;height:20px;border-radius:4px;margin-bottom:8px" onerror="this.style.display='none'">` : `<span style="font-size:20px">${l.icon}</span>`}
      <div class="pin-title">${l.title}</div>
      ${l.description ? `<div class="pin-desc">${l.description}</div>` : ''}
      <div class="pin-cat">${l.category}</div>
      ${tags ? `<div class="pin-tags">${tags}</div>` : ''}
    </div>`;
  }).join('');
}

function trackAndOpen(id, url) {
  fetch(`${API}/links/${id}/click`, { method: 'POST' }).catch(() => {});
  window.open(url, '_blank', 'noopener,noreferrer');
}

function openNotesPanelById(id) {
  const link = allLinks.find(l => l.id === id);
  if (link && link.notes) openNotesPanel(link);
}

// ── Tag Cloud View ───────────────────────────────────────────────────────────
function renderTagCloud() {
  const inner = document.getElementById('tagcloud-inner');
  if (!inner) return;
  const tagCounts = {};
  allLinks.forEach(l => {
    if (!l.tags) return;
    l.tags.split(',').forEach(t => { t = t.trim(); if (t) tagCounts[t] = (tagCounts[t] || 0) + 1; });
  });
  const tags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]);
  const max = tags[0]?.[1] || 1;
  inner.innerHTML = tags.map(([tag, count]) => {
    const size = 14 + (count / max) * 32;
    const opacity = 0.5 + (count / max) * 0.5;
    return `<span onclick="filterByTag('${tag}')" style="font-family:'Caveat',cursive;font-size:${size}px;color:var(--accent);opacity:${opacity};cursor:pointer;padding:4px 8px;border-radius:8px;transition:all 0.2s" onmouseover="this.style.background='rgba(255,122,41,0.15)'" onmouseout="this.style.background=''" title="${count} link${count > 1 ? 's' : ''}">${tag}</span>`;
  }).join('');
  if (tags.length === 0) inner.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:14px;">No tags yet. Add tags to links in admin.</div>';
}

function filterByTag(tag) {
  activeCategory = 'All';
  switchView('board');
  const grid = document.getElementById('pinboard-grid');
  if (!grid) return;
  const filtered = allLinks.filter(l => l.tags && l.tags.split(',').map(t => t.trim()).includes(tag));
  grid.innerHTML = filtered.map(l => `<div class="pin-card" onclick="trackAndOpen(${l.id},'${l.url.replace(/'/g, "\\'")}')">
    <span style="font-size:20px">${l.icon}</span>
    <div class="pin-title">${l.title}</div>
    ${l.description ? `<div class="pin-desc">${l.description}</div>` : ''}
    <div class="pin-cat">${l.category}</div>
  </div>`).join('');
}

// ── Link of the Day ──────────────────────────────────────────────────────────
function renderLinkOfDay() {
  const featured = allLinks.filter(l => l.featured);
  if (!featured.length) return;
  const dayIndex = Math.floor(Date.now() / 86400000);
  const link = featured[dayIndex % featured.length];
  const el = document.getElementById('link-of-day');
  if (!el) return;
  el.innerHTML = `
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,163,92,0.5);margin-bottom:4px">✨ Link of the Day</div>
    <a href="${link.url}" onclick="trackAndOpen(${link.id},'${link.url.replace(/'/g, "\\'")}');return false;" style="font-family:'Caveat',cursive;font-size:22px;color:var(--accent-light);font-weight:700;text-decoration:none;">${link.icon} ${link.title}</a>
    ${link.description ? `<div style="font-size:11px;color:#aaa;margin-top:2px">${link.description}</div>` : ''}
  `;
  el.style.display = 'block';
}

// ── Site Header ──────────────────────────────────────────────────────────────
async function loadSiteHeader() {
  try {
    const res = await fetch(`${API}/settings/header`);
    if (!res.ok) return;
    const h = await res.json();
    if (h.site_name) document.title = `${h.site_name} · Links`;
    const strip = document.getElementById('site-header-strip');
    if (strip && (h.site_name || h.site_bio)) {
      strip.innerHTML = `
        ${h.site_avatar ? `<span style="font-size:24px">${h.site_avatar}</span>` : ''}
        <span style="font-family:'Caveat',cursive;font-size:20px;color:var(--accent)">${h.site_name || 'Memex'}</span>
        ${h.site_bio ? `<span style="font-size:11px;color:#aaa;margin-left:8px">${h.site_bio}</span>` : ''}
      `;
      strip.style.display = 'flex';
    }
  } catch(e) {}
}

// ── Mobile Tag Filter ────────────────────────────────────────────────────────
let mobileTagFilter = null;

function toggleMobileTags() {
  const bar = document.getElementById('mobile-tag-bar');
  const colBar = document.getElementById('mobile-collections-bar');
  if (bar.style.display === 'flex') {
    bar.style.display = 'none';
    mobileTagFilter = null;
    mobileVisibleCount = MOBILE_PAGE_SIZE;
    renderMobileGrid();
    return;
  }
  colBar.style.display = 'none';
  bar.style.display = 'flex';
  buildMobileTagBar();
}

function buildMobileTagBar() {
  const bar = document.getElementById('mobile-tag-bar');
  const tagCounts = {};
  allLinks.forEach(l => {
    if (!l.tags) return;
    l.tags.split(',').forEach(t => { t = t.trim(); if (t) tagCounts[t] = (tagCounts[t] || 0) + 1; });
  });
  const tags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]);
  bar.innerHTML = `<span class="tag-pill ${!mobileTagFilter ? 'active' : ''}" onclick="setMobileTagFilter(null)">All</span>` +
    tags.map(([tag]) => `<span class="tag-pill ${mobileTagFilter === tag ? 'active' : ''}" onclick="setMobileTagFilter('${tag}')">${tag}</span>`).join('');
}

function setMobileTagFilter(tag) {
  mobileTagFilter = tag;
  mobileVisibleCount = MOBILE_PAGE_SIZE;
  buildMobileTagBar();
  renderMobileGrid();
}

// ── Mobile Collections Browser ───────────────────────────────────────────────
let mobileCollectionLinks = null;

function toggleMobileCollections() {
  const bar = document.getElementById('mobile-collections-bar');
  const tagBar = document.getElementById('mobile-tag-bar');
  if (bar.style.display === 'flex') {
    bar.style.display = 'none';
    mobileCollectionLinks = null;
    mobileVisibleCount = MOBILE_PAGE_SIZE;
    renderMobileGrid();
    return;
  }
  tagBar.style.display = 'none';
  bar.style.display = 'flex';
  loadMobileCollections();
}

async function loadMobileCollections() {
  const bar = document.getElementById('mobile-collections-bar');
  try {
    const cols = await fetch(`${API}/collections`).then(r => r.json());
    if (cols.length === 0) {
      bar.innerHTML = '<span style="font-size:11px;color:rgba(255,255,255,0.3)">No collections yet</span>';
      return;
    }
    bar.innerHTML = `<span class="col-pill ${!mobileCollectionLinks ? 'active' : ''}" onclick="clearMobileCollection()">All</span>` +
      cols.map(c => `<span class="col-pill" onclick="loadMobileCollection('${c.slug}')">${c.name}</span>`).join('');
  } catch(e) {
    bar.innerHTML = '<span style="font-size:11px;color:rgba(255,255,255,0.3)">Error loading</span>';
  }
}

async function loadMobileCollection(slug) {
  try {
    const data = await fetch(`${API}/collections/${slug}`).then(r => r.json());
    mobileCollectionLinks = data.links || [];
    mobileVisibleCount = MOBILE_PAGE_SIZE;
    // Highlight active pill
    document.querySelectorAll('#mobile-collections-bar .col-pill').forEach(p => p.classList.remove('active'));
    event.target.classList.add('active');
    renderMobileGrid();
  } catch(e) {}
}

function clearMobileCollection() {
  mobileCollectionLinks = null;
  mobileVisibleCount = MOBILE_PAGE_SIZE;
  document.querySelectorAll('#mobile-collections-bar .col-pill').forEach(p => p.classList.remove('active'));
  document.querySelector('#mobile-collections-bar .col-pill')?.classList.add('active');
  renderMobileGrid();
}

// ── Search Overlay (Ctrl+K or /) ─────────────────────────────────────────────
(function initSearch() {
  const overlay = document.createElement('div');
  overlay.id = 'search-overlay';
  overlay.innerHTML = `
    <div class="search-backdrop"></div>
    <div class="search-modal">
      <div class="search-input-wrap">
        <span class="search-icon">🔍</span>
        <input type="text" id="search-input-public" placeholder="Search links…" autocomplete="off">
        <kbd class="search-kbd">ESC</kbd>
      </div>
      <div id="search-results" class="search-results"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  const input = document.getElementById('search-input-public');
  const results = document.getElementById('search-results');

  function openSearch() {
    overlay.classList.add('open');
    input.value = '';
    results.innerHTML = '';
    setTimeout(() => input.focus(), 50);
  }

  function closeSearch() {
    overlay.classList.remove('open');
    input.blur();
  }

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); openSearch(); }
    else if (e.key === '/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) { e.preventDefault(); openSearch(); }
    else if (e.key === 'Escape') { closeSearch(); }
  });

  overlay.querySelector('.search-backdrop').addEventListener('click', closeSearch);

  input.addEventListener('input', () => {
    const q = input.value.toLowerCase().trim();
    results.innerHTML = '';
    if (!q) return;
    const matches = allLinks.filter(l =>
      l.title.toLowerCase().includes(q) ||
      l.category.toLowerCase().includes(q) ||
      l.description.toLowerCase().includes(q) ||
      l.url.toLowerCase().includes(q) ||
      (l.tags && l.tags.toLowerCase().includes(q))
    ).slice(0, 8);

    if (matches.length === 0) {
      results.innerHTML = '<div class="search-empty">No results found</div>';
      return;
    }
    matches.forEach(link => {
      const item = document.createElement('a');
      item.className = 'search-result-item';
      item.href = link.url;
      item.target = '_blank';
      item.rel = 'noopener noreferrer';
      item.addEventListener('click', () => {
        fetch(`${API}/links/${link.id}/click`, { method: 'POST' }).catch(() => {});
        closeSearch();
      });
      item.innerHTML = `
        <span class="search-result-icon">${link.icon}</span>
        <div class="search-result-info">
          <div class="search-result-title">${link.title}</div>
          <div class="search-result-meta">${link.category}${link.description ? ' · ' + link.description : ''}</div>
        </div>
      `;
      results.appendChild(item);
    });
  });

  input.addEventListener('keydown', (e) => {
    const items = results.querySelectorAll('.search-result-item');
    if (!items.length) return;
    const active = results.querySelector('.search-result-item.active');
    let idx = active ? [...items].indexOf(active) : -1;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (active) active.classList.remove('active');
      idx = (idx + 1) % items.length;
      items[idx].classList.add('active');
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (active) active.classList.remove('active');
      idx = (idx - 1 + items.length) % items.length;
      items[idx].classList.add('active');
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (active) active.click();
      else if (items[0]) items[0].click();
    }
  });
})();
