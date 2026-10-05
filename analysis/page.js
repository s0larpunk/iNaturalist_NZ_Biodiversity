/* Charts and the gap finder for site/nz-biodiversity.html. Reads the inline
   #nz-results block; the gap finder loads nz-species.json on first use.
   Everything is SVG drawn from the site's CSS variables. */
(function () {
  const R = JSON.parse(document.getElementById('nz-results').textContent);
  const NS = 'http://www.w3.org/2000/svg';
  const fmt = n => n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'k' : String(n);
  const pct = v => Math.round(v * 100) + '%';
  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function svg(host, w, h) { const s = el('svg', { viewBox: `0 0 ${w} ${h}`, class: 'mt-svg', role: 'img' }); host.appendChild(s); return s; }
  function text(s, x, y, t, cls, anchor) { const e = el('text', { x, y, class: cls || 'mt-t', 'text-anchor': anchor || 'start' }, s); e.textContent = t; return e; }
  function tip(node, t) { el('title', {}, node).textContent = t; }

  /* ------------------------------------------------ 1. growth over time */
  function growth(host) {
    const Y = R.years.filter(r => r.year >= 2008);
    const w = 680, h = 300, L = 54, Rr = 54, B = 34, T = 16;
    const s = svg(host, w, h);
    const x = i => L + (w - L - Rr) * i / (Y.length - 1);
    const maxS = Math.max(...Y.map(r => r.species)) * 1.08;
    const maxO = Math.max(...Y.map(r => r.observations)) * 1.08;
    const ys = v => T + (h - T - B) * (1 - v / maxS);
    const yo = v => T + (h - T - B) * (1 - v / maxO);
    [0, .25, .5, .75, 1].forEach(f => {
      el('line', { x1: L, x2: w - Rr, y1: ys(maxS * f), y2: ys(maxS * f), class: 'mt-grid' }, s);
      text(s, L - 8, ys(maxS * f) + 4, fmt(Math.round(maxS * f)), 'mt-t mt-ax mt-k1', 'end');
      text(s, w - Rr + 8, yo(maxO * f) + 4, fmt(Math.round(maxO * f)), 'mt-t mt-ax mt-k2', 'start');
    });
    Y.forEach((r, i) => { if (r.year % 2 === 0) text(s, x(i), h - 12, String(r.year), 'mt-t mt-ax', 'middle'); });
    const i24 = Y.findIndex(r => r.year === 2023);
    el('line', { x1: x(i24) + (x(1) - x(0)) * .08, x2: x(i24) + (x(1) - x(0)) * .08, y1: T, y2: h - B, class: 'mt-base' }, s);
    text(s, x(i24) - 4, T + 10, '2024 study', 'mt-t mt-note', 'end');
    el('polyline', { points: Y.map((r, i) => `${x(i)},${yo(r.observations)}`).join(' '), class: 'mt-l2' }, s);
    el('polyline', { points: Y.map((r, i) => `${x(i)},${ys(r.species)}`).join(' '), class: 'mt-l1' }, s);
    Y.forEach((r, i) => tip(el('circle', { cx: x(i), cy: ys(r.species), r: 3.5, class: 'mt-d1' }, s),
      `${r.year}: ${r.species.toLocaleString()} species, ${r.observations.toLocaleString()} observations, ${r.observers.toLocaleString()} observers that year`));
  }

  /* ------------------------------------------------ 2. how many species */
  function estimates(host) {
    const n = R.now, st = R.study_2024;
    const bars = [
      ['Seen by the crowd, Feb 2024', st.species, 'mt-b2'],
      ['Estimated from the crowd, 2024', st.chao1, 'mt-b1'],
      ['Seen by the crowd, Oct 2026', n.species, 'mt-b2'],
      ['Estimated from the crowd, 2026', n.chao1, 'mt-b3'],
      ['Known to science in New Zealand', R.known_total, 'mt-b4'],
    ];
    const w = 680, rowH = 38, L = 230, h = bars.length * rowH + 30;
    const s = svg(host, w, h);
    const max = R.known_total * 1.05;
    const x = v => L + (w - L - 70) * v / max;
    [0, 10000, 20000, 30000, 40000, 50000].forEach(v => {
      el('line', { x1: x(v), x2: x(v), y1: 6, y2: h - 22, class: 'mt-grid' }, s);
      text(s, x(v), h - 6, fmt(v), 'mt-t mt-ax', 'middle');
    });
    bars.forEach(([lab, v, cls], i) => {
      const y = 10 + i * rowH;
      text(s, L - 12, y + 17, lab, 'mt-t', 'end');
      el('rect', { x: x(0), y: y + 4, width: x(v) - x(0), height: 20, rx: 3, class: cls }, s);
      text(s, x(v) + 7, y + 18, Math.round(v).toLocaleString(), 'mt-t mt-val');
    });
    const ci = n.chao1_ci, y3 = 10 + 3 * rowH + 14;
    el('line', { x1: x(ci[0]), x2: x(ci[1]), y1: y3, y2: y3, class: 'mt-ci' }, s);
  }

  /* ------------------------------------------------ 3. attention per group */
  const GL = { Aves: 'Birds', Plantae: 'Plants', Insecta: 'Insects', Fungi: 'Fungi', Mollusca: 'Molluscs', Arachnida: 'Spiders & kin',
    Mammalia: 'Mammals', Reptilia: 'Reptiles', Amphibia: 'Amphibians', Actinopterygii: 'Fish', Animalia: 'Other animals',
    Chromista: 'Seaweeds & kin', Protozoa: 'Slime moulds & kin', Other: 'Other' };
  function attention(host) {
    const rows = Object.entries(R.groups).filter(([, v]) => v.species >= 20).sort((a, b) => b[1].obs_per_species - a[1].obs_per_species);
    const w = 680, rowH = 28, L = 150, h = rows.length * rowH + 30;
    const s = svg(host, w, h);
    const lmax = Math.log10(Math.max(...rows.map(r => r[1].obs_per_species)) * 1.3);
    const x = v => L + (w - L - 80) * Math.log10(Math.max(v, 1)) / lmax;
    [1, 10, 100, 1000].forEach(v => { if (Math.log10(v) <= lmax) {
      el('line', { x1: x(v), x2: x(v), y1: 6, y2: h - 22, class: 'mt-grid' }, s);
      text(s, x(v), h - 6, String(v), 'mt-t mt-ax', 'middle'); } });
    rows.forEach(([g, v], i) => {
      const y = 8 + i * rowH;
      text(s, L - 12, y + 15, GL[g] || g, 'mt-t', 'end');
      const r = el('rect', { x: x(1), y: y + 3, width: Math.max(2, x(v.obs_per_species) - x(1)), height: 16, rx: 2,
        class: i === 0 ? 'mt-b3' : (g === 'Fungi' || g === 'Insecta' ? 'mt-b1' : 'mt-b2') }, s);
      tip(r, `${v.species.toLocaleString()} species, ${v.observations.toLocaleString()} observations`);
      text(s, x(v.obs_per_species) + 7, y + 16, Math.round(v.obs_per_species).toLocaleString(), 'mt-t mt-val');
    });
  }

  /* ------------------------------------------------ 4. threat categories */
  function threat(host) {
    const order = ['Threatened', 'At Risk', 'Not Threatened', 'Data Deficient', 'Introduced and Naturalised', 'Non-resident Native'];
    const rows = order.filter(k => R.categories[k]).map(k => [k, R.categories[k]]);
    const w = 680, rowH = 36, L = 200, h = rows.length * rowH + 30;
    const s = svg(host, w, h);
    const x = v => L + (w - L - 70) * v;
    [0, .25, .5, .75, 1].forEach(v => { el('line', { x1: x(v), x2: x(v), y1: 6, y2: h - 22, class: 'mt-grid' }, s);
      text(s, x(v), h - 6, pct(v), 'mt-t mt-ax', 'middle'); });
    rows.forEach(([k, v], i) => {
      const y = 8 + i * rowH;
      text(s, L - 12, y + 13, k, 'mt-t', 'end');
      text(s, L - 12, y + 26, `${v.n.toLocaleString()} species`, 'mt-t mt-ax', 'end');
      el('rect', { x: x(0), y: y + 4, width: x(v.seen) - x(0), height: 20, rx: 3, class: k === 'Data Deficient' ? 'mt-b3' : 'mt-b2' }, s);
      el('rect', { x: x(0), y: y + 4, width: x(v.seen5) - x(0), height: 20, rx: 3, class: 'mt-over' }, s);
      text(s, x(v.seen) + 7, y + 19, pct(v.seen), 'mt-t mt-val');
    });
  }

  /* ------------------------------------------------ 5. map */
  function map(host) {
    const cells = R.grid;
    const lats = cells.map(c => c[0]), lngs = cells.map(c => c[1]);
    const la0 = Math.min(...lats), la1 = Math.max(...lats) + .5, lo0 = Math.min(...lngs), lo1 = Math.max(...lngs) + .5;
    const sc = 30, w = (lo1 - lo0) * sc * Math.cos(41 * Math.PI / 180) + 20, h = (la1 - la0) * sc + 20;
    const s = svg(host, w, h);
    const X = lng => 10 + (lng - lo0) * sc * Math.cos(41 * Math.PI / 180);
    const Y = lat => 10 + (la1 - lat) * sc;
    const lmax = Math.log10(Math.max(...cells.map(c => c[2])));
    cells.forEach(([lat, lng, n]) => {
      const k = Math.log10(n) / lmax;
      const r = 1.6 + 7.4 * k;
      const c = el('circle', { cx: X(lng + .25), cy: Y(lat + .25), r: r.toFixed(2), class: 'nz-dot', style: `--k:${k.toFixed(3)}` }, s);
      tip(c, `${n.toLocaleString()} observations`);
    });
  }

  /* ------------------------------------------------ 6. gap finder */
  function finder(host) {
    host.innerHTML = `<div class="mt-tool nz-tool">
      <div class="nz-filters">
        <label class="mt-search"><span class="ui">Search New Zealand's assessed species</span>
          <input type="search" placeholder="Common, Māori or scientific name…" autocomplete="off"></label>
        <div class="mt-presets"><span class="ui">Show</span>
          <button type="button" data-v="gap" aria-pressed="true">Data Deficient, seen by the crowd</button>
          <button type="button" data-v="threat">Threatened</button>
          <button type="button" data-v="unseen">Threatened, never seen</button>
          <button type="button" data-v="all">All</button></div>
        <div class="mt-presets nz-king"><span class="ui">Kingdom</span>
          ${['All', 'Animalia', 'Plantae', 'Fungi', 'Chromista'].map((k, i) => `<button type="button" data-k="${k}" aria-pressed="${!i}">${k === 'All' ? 'All' : k}</button>`).join('')}</div>
      </div>
      <p class="nz-count"></p>
      <ol class="nz-list"></ol>
    </div>`;
    const input = host.querySelector('input'), list = host.querySelector('.nz-list'), count = host.querySelector('.nz-count');
    let rows = null, view = 'gap', king = 'All';
    function draw() {
      if (!rows) return;
      const q = input.value.trim().toLowerCase();
      let r = rows;
      if (view === 'gap') r = r.filter(x => x[9] && x[3] === 'Data Deficient' && x[8] > 0);
      if (view === 'threat') r = r.filter(x => x[3] === 'Threatened');
      if (view === 'unseen') r = r.filter(x => x[9] && x[3] === 'Threatened' && x[8] === 0);
      if (king !== 'All') r = r.filter(x => x[5] === king);
      if (q.length > 1) r = r.filter(x => (x[0] + ' ' + x[1] + ' ' + x[2]).toLowerCase().includes(q));
      r = r.slice().sort((a, b) => b[8] - a[8]);
      count.textContent = `${r.length.toLocaleString()} species`;
      list.innerHTML = '';
      r.slice(0, 40).forEach(x => {
        const li = document.createElement('li');
        const name = x[1] || x[2] || x[0];
        li.innerHTML = `<div><b></b> <span class="nz-sci"></span><span class="nz-meta"></span></div><a class="nz-obs" target="_blank" rel="noopener"></a>`;
        li.querySelector('b').textContent = name;
        li.querySelector('.nz-sci').textContent = x[0] !== name ? x[0] : '';
        li.querySelector('.nz-meta').textContent = [x[4], x[6], x[7]].filter(Boolean).join(' · ');
        const a = li.querySelector('.nz-obs');
        a.textContent = x[8] ? `${x[8].toLocaleString()} crowd records${x[9] ? '' : ' (whole species)'} ↗` : 'no crowd records yet';
        a.href = 'https://www.inaturalist.org/observations?place_id=6803&taxon_name=' + encodeURIComponent(x[0].split(' ').slice(0, 2).join(' '));
        list.appendChild(li);
      });
      if (r.length > 40) { const li = document.createElement('li'); li.className = 'nz-more'; li.textContent = `and ${(r.length - 40).toLocaleString()} more — refine the search to see them`; list.appendChild(li); }
    }
    host.querySelectorAll('[data-v]').forEach(b => b.addEventListener('click', () => {
      view = b.dataset.v; host.querySelectorAll('[data-v]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); draw(); }));
    host.querySelectorAll('[data-k]').forEach(b => b.addEventListener('click', () => {
      king = b.dataset.k; host.querySelectorAll('[data-k]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); draw(); }));
    input.addEventListener('input', draw);
    count.textContent = 'Loading the species list…';
    fetch('nz-species.json').then(r => r.json()).then(j => { rows = j; draw(); })
      .catch(() => { count.textContent = 'The species list needs the site served over http.'; });
  }

  const on = (id, fn) => { const h = document.getElementById(id); if (h) fn(h); };
  on('nz-growth', growth); on('nz-est', estimates); on('nz-att', attention);
  on('nz-threat', threat); on('nz-map', map); on('nz-finder', finder);
})();
