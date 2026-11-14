(() => {
  const steps = [
    {
      title: "Kick off build & choose roots",
      html: `
        <p>You run <code>PYTHONPATH=src python -m index build</code>.</p>
        <p>That enters <code>main()</code> → <code>build(corpus, out)</code>:</p>
        <ul>
          <li><strong>corpus</strong> defaults to the repo root. The pack lives under <code>corpus/**/*.md</code>.</li>
          <li><strong>out</strong> defaults to <code>index/</code> — where files will be written at the end.</li>
        </ul>
        <p>No embeddings yet. Only “read from here, write the index there.”</p>`,
      viz: `
        <div class="file-stack" style="margin-top:1.5rem">
          <div class="file-card">corpus/ → source of truth (markdown pack)</div>
          <div class="file-card">index/ → empty / about to be rewritten</div>
          <div class="file-card" style="border-color:rgba(240,179,90,.45)">build(corpus, out) starts</div>
        </div>`,
    },
    {
      title: "Collect every policy markdown file",
      html: `
        <p><code>build</code> calls <code>load_chunks(corpus)</code>.</p>
        <ul>
          <li>Look under <code>{repo}/corpus/</code>.</li>
          <li>Recursively find every <code>*.md</code> (<code>rglob</code>).</li>
          <li>Sort paths so builds are deterministic.</li>
        </ul>
        <p>Still no embeddings — just a stable list of document paths (policy, annex, opinions, FAQ, not-in-force, …).</p>`,
      viz: `
        <div class="file-stack">
          <div class="file-card">corpus/policy/ONB-POL-001.md</div>
          <div class="file-card">corpus/annex/ONB-ANX-001.md</div>
          <div class="file-card">corpus/opinions/addendum/iso-not-dpa.md</div>
          <div class="file-card">corpus/faq/articles/….md</div>
          <div class="file-card">corpus/not-in-force/….md</div>
        </div>`,
    },
    {
      title: "Per file: read & pull metadata",
      html: `
        <p>For every path, before splitting:</p>
        <ul>
          <li><strong>document_id</strong> — from the <code>| Document ID |</code> table row, else filename stem.</li>
          <li><strong>title / heading</strong> — from top <code>#</code> headings.</li>
          <li><strong>folder</strong> — first segment under <code>corpus/</code> (used later for search tier bonuses).</li>
          <li><strong>in_force</strong> — false if under <code>not-in-force/</code> or Status says not in force.</li>
        </ul>`,
      viz: `
        <div class="meta-grid">
          <div class="meta-chip"><strong>document_id</strong>ONB-ADDENDUM-ISO-NOT-DPA</div>
          <div class="meta-chip"><strong>heading</strong>ISO/IEC 27001 is not the DPA</div>
          <div class="meta-chip"><strong>folder</strong>opinions</div>
          <div class="meta-chip"><strong>in_force</strong>true</div>
        </div>`,
    },
    {
      title: "Split into overlapping chunks",
      html: `
        <p>Defaults: <strong>800</strong> characters with <strong>120</strong> overlap (<code>ONB_CHUNK</code> / <code>ONB_OVERLAP</code>).</p>
        <ul>
          <li>If file ≤ 800 chars → one chunk.</li>
          <li>Else sliding window: take 800, advance by 680, repeat.</li>
          <li>Overlap keeps a clause on a boundary from being lost.</li>
        </ul>
        <p>A sanity check aborts if chunk count drifts from the formula.</p>`,
      viz: `
        <p class="overlap-label">overlap 120</p>
        <div class="chunk-track">
          <div class="chunk-window"></div>
          <div class="chunk-window second"></div>
        </div>
        <p style="margin:1rem 0 0;font-family:var(--mono);font-size:.75rem;color:var(--mist)">window slides · step = 800 − 120</p>`,
    },
    {
      title: "Build each chunk row + search_text",
      html: `
        <p>Each piece becomes a dict. Important fields:</p>
        <ul>
          <li><code>text</code> — raw window (what you may return/cite).</li>
          <li><code>search_text</code> — string generated <em>at build time</em> for embedding:<br>
            <code>document_id + heading + clean(piece)</code></li>
        </ul>
        <p><code>clean()</code> strips metadata tables, separators, and repeated “iPe is fictional…” boilerplate so vectors focus on substance.</p>
        <p>There is no user query yet — <code>search_text</code> is only a field name.</p>`,
      viz: `
        <div class="string-build">
          <span class="line hl">ONB-ADDENDUM-ISO-NOT-DPA</span>
          <span class="line hl">ISO/IEC 27001 is not the data-processing addendum</span>
          <span class="line dim">| Document ID | … |   ← removed by clean()</span>
          <span class="line">## Issue\\nWhether an ISO 27001 certificate…</span>
        </div>`,
    },
    {
      title: "Embed via Capstone API + L2-normalize",
      html: `
        <p>Collect every chunk’s <code>search_text</code> (same order as rows).</p>
        <ul>
          <li><code>POST /embeddings</code> with model <code>bge-small-en-v1.5</code></li>
          <li>Batches of 16; TLS via CA cert; Bearer <code>EMBEDDINGS_API_KEY</code></li>
          <li>One vector per string, then <strong>L2-normalize</strong> (divide by length so each vector has length 1)</li>
        </ul>
        <p>Why normalize? So similarity compares direction (meaning), not raw magnitude. After that, dot product = cosine similarity.</p>
        <p>Tiny example: <code>[3,4]</code> has length √(9+16)=5 → divide by 5 → <code>[0.6, 0.8]</code> (still same direction, now length 1).</p>`,
      viz: `
        <div class="embed-batch">
          <div class="batch-row"><span>batch 1</span><div class="batch-bar"><span></span></div><span>16</span></div>
          <div class="batch-row"><span>batch 2</span><div class="batch-bar"><span></span></div><span>16</span></div>
          <div class="batch-row"><span>batch n</span><div class="batch-bar"><span></span></div><span>…</span></div>
        </div>
        <div class="norm-panel">
          <svg class="norm-svg" viewBox="0 0 280 200" aria-hidden="true">
            <!-- axes -->
            <line x1="40" y1="170" x2="250" y2="170" stroke="rgba(157,181,171,.45)" stroke-width="1.5"/>
            <line x1="40" y1="170" x2="40" y2="20" stroke="rgba(157,181,171,.45)" stroke-width="1.5"/>
            <text x="246" y="186" fill="#9db5ab" font-size="11" font-family="IBM Plex Mono,monospace">x</text>
            <text x="20" y="28" fill="#9db5ab" font-size="11" font-family="IBM Plex Mono,monospace">y</text>

            <!-- unit circle (radius 30px = length 1 on this scale; 1 unit = 30px) -->
            <circle cx="40" cy="170" r="30" fill="none" stroke="rgba(94,224,181,.35)" stroke-width="1.5" stroke-dasharray="4 4"/>
            <text x="48" y="148" fill="#5ee0b5" font-size="9" font-family="IBM Plex Mono,monospace">unit circle</text>

            <!-- before [3,4]: scale 30px/unit → tip at (40+90, 170-120) = (130, 50) -->
            <line class="norm-before" x1="40" y1="170" x2="130" y2="50" stroke="#f0b35a" stroke-width="3" marker-end="url(#arrow-amber)"/>
            <circle cx="130" cy="50" r="4" fill="#f0b35a"/>
            <text x="138" y="46" fill="#f0b35a" font-size="11" font-family="IBM Plex Mono,monospace">[3, 4] len=5</text>

            <!-- after [0.6,0.8]: tip at (40+18, 170-24) = (58, 146) on the unit circle -->
            <line class="norm-after" x1="40" y1="170" x2="58" y2="146" stroke="#5ee0b5" stroke-width="3.5"/>
            <circle cx="58" cy="146" r="4.5" fill="#5ee0b5"/>
            <text x="66" y="138" fill="#5ee0b5" font-size="11" font-family="IBM Plex Mono,monospace">[0.6, 0.8] len=1</text>

            <defs>
              <marker id="arrow-amber" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="#f0b35a"/>
              </marker>
            </defs>
          </svg>
          <p class="norm-caption">Same direction · shorter arrow lands on the unit circle</p>
        </div>`,
    },
    {
      title: "Write the index to disk",
      html: `
        <p>Create <code>index/</code> (or <code>--out</code>) and write:</p>
        <ul>
          <li><code>chunks.jsonl</code> — one JSON object per line (chunk rows), same order as vectors</li>
          <li><code>vectors.npy</code> — matrix of normalized embeddings; row <em>i</em> matches line <em>i</em></li>
        </ul>
        <p>Print counts and exit. Keyword postings are <strong>not</strong> stored — they are rebuilt in memory when the server loads the index.</p>
        <p>On Render, this whole build runs during <strong>deploy</strong>; cold start only loads these files.</p>`,
      viz: `
        <div class="disk-out">
          <div class="disk-file">
            <div class="disk-ico">JL</div>
            <div>
              <strong>chunks.jsonl</strong>
              <span>metadata + text + search_text per chunk</span>
            </div>
          </div>
          <div class="disk-file">
            <div class="disk-ico">NP</div>
            <div>
              <strong>vectors.npy</strong>
              <span>aligned embedding matrix</span>
            </div>
          </div>
        </div>`,
    },
  ];

  const nav = document.getElementById("step-nav");
  const titleEl = document.getElementById("step-title");
  const copyEl = document.getElementById("step-copy");
  const vizEl = document.getElementById("step-viz");
  const prevBtn = document.getElementById("prev-step");
  const nextBtn = document.getElementById("next-step");
  const counter = document.getElementById("step-counter");
  let i = 0;

  function render(index) {
    i = Math.max(0, Math.min(steps.length - 1, index));
    const step = steps[i];
    titleEl.textContent = step.title;
    copyEl.innerHTML = step.html;
    vizEl.innerHTML = step.viz;
    counter.textContent = `${i + 1} / ${steps.length}`;
    prevBtn.disabled = i === 0;
    nextBtn.disabled = i === steps.length - 1;
    [...nav.querySelectorAll("button")].forEach((btn, idx) => {
      btn.setAttribute("aria-current", idx === i ? "true" : "false");
    });
  }

  steps.forEach((step, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.innerHTML = `<span class="num">${String(idx + 1).padStart(2, "0")}</span>${step.title}`;
    btn.addEventListener("click", () => render(idx));
    nav.appendChild(btn);
  });

  prevBtn.addEventListener("click", () => render(i - 1));
  nextBtn.addEventListener("click", () => render(i + 1));

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") render(i + 1);
    if (e.key === "ArrowLeft") render(i - 1);
  });

  render(0);

  const cards = document.querySelectorAll(".s-card");
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) entry.target.classList.add("in");
      });
    },
    { threshold: 0.2 }
  );
  cards.forEach((c) => io.observe(c));

  // Hero flowing dots along SVG paths
  const svg = document.getElementById("pipeline-svg");
  if (svg) {
    const paths = [
      "M80 70 C150 70 170 70 250 70",
      "M250 70 C320 70 340 70 420 70",
      "M420 70 C490 70 510 120 510 170",
      "M510 200 C510 250 420 280 340 280",
    ];
    paths.forEach((d, idx) => {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", d);
      path.setAttribute("class", "flow-path");
      path.setAttribute("pathLength", "100");
      svg.querySelector(".paths").appendChild(path);

      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("r", "4.5");
      dot.setAttribute("class", "flow-dot");
      svg.querySelector(".dots").appendChild(dot);

      const len = path.getTotalLength();
      let t = idx * 0.22;
      function tick() {
        t = (t + 0.0045) % 1;
        const pt = path.getPointAtLength(t * len);
        dot.setAttribute("cx", pt.x);
        dot.setAttribute("cy", pt.y);
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }
})();
