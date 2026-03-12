"use strict";

/* ── CONSTANTS ──────────────────────────────────────────────────────────── */
const CATEGORIES = [
  { id: "food",          label: "Food & Drink", icon: "🍜", color: "#FF6B6B" },
  { id: "transport",     label: "Transport",    icon: "🚌", color: "#4ECDC4" },
  { id: "shopping",      label: "Shopping",     icon: "🛍️", color: "#45B7D1" },
  { id: "health",        label: "Health",       icon: "💊", color: "#96CEB4" },
  { id: "entertainment", label: "Fun",          icon: "🎬", color: "#FFEAA7" },
  { id: "bills",         label: "Bills",        icon: "🧾", color: "#DDA0DD" },
  { id: "other",         label: "Other",        icon: "📦", color: "#F0A500" },
];
const WEEK_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFEAA7", "#DDA0DD"];

/* ── STATE ──────────────────────────────────────────────────────────────── */
const now = new Date();
let navYear      = now.getFullYear();
let navMonth     = now.getMonth(); // 0-indexed
let activeView   = "list";
let activeFilter = "all";
let expenses     = [];
let isNavigating = false; // prevent double-clicks

/* ── HELPERS ────────────────────────────────────────────────────────────── */
const fmt = (n) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

const navStr    = () => `${navYear}-${String(navMonth + 1).padStart(2, "0")}`;
const navLabel  = () => new Date(navYear, navMonth, 1).toLocaleDateString("en-IN", { month: "long", year: "numeric" });
const navShort  = () => new Date(navYear, navMonth, 1).toLocaleDateString("en-IN", { month: "short" });
const isCurrent = () => navYear === now.getFullYear() && navMonth === now.getMonth();
const todayStr  = () => new Date().toISOString().split("T")[0];
const getCat    = (id) => CATEGORIES.find((c) => c.id === id) || CATEGORIES[6];

function fmtDate(d) {
  const dt   = new Date(d + "T12:00:00");
  const diff = Math.round((Date.now() - dt) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return dt.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

/* ── API ────────────────────────────────────────────────────────────────── */
async function apiFetch(path, opts = {}) {
  try {
    const res  = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
    const data = await res.json();
    if (!res.ok) {
      console.error("API error:", data);
      showToast(data.error || "Something went wrong");
      return null;
    }
    return data;
  } catch (err) {
    console.error("Fetch failed:", err);
    showToast("Network error — check your connection");
    return null;
  }
}

function showToast(msg) {
  let t = document.getElementById("toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.style.cssText = `
      position:fixed; bottom:90px; left:50%; transform:translateX(-50%);
      background:#2a2118; color:#faf8f5; padding:10px 20px; border-radius:10px;
      font-family:'DM Mono',monospace; font-size:12px; z-index:999;
      opacity:0; transition:opacity .2s; pointer-events:none; white-space:nowrap;
    `;
    document.body.appendChild(t);
  }
  t.textContent  = msg;
  t.style.opacity = "1";
  setTimeout(() => { t.style.opacity = "0"; }, 3000);
}

/* ── MONTH NAVIGATION ────────────────────────────────────────────────────── */
function goPrev() {
  if (navMonth === 0) { navYear--; navMonth = 11; }
  else { navMonth--; }
}

function goNext() {
  if (isCurrent()) return;
  if (navMonth === 11) { navYear++; navMonth = 0; }
  else { navMonth++; }
}

/* ── RENDER: HEADER ─────────────────────────────────────────────────────── */
function renderHeader(total) {
  document.getElementById("monthTitle").textContent  = navLabel();
  document.getElementById("monthLabel").textContent  = isCurrent() ? "this month" : "viewing";
  document.getElementById("headerTotal").textContent = fmt(total || 0);
  document.getElementById("prevMonth").disabled      = false;        // always re-enable
  document.getElementById("nextMonth").disabled      = isCurrent();  // disable only at current month
}

/* ── RENDER: FILTERS ────────────────────────────────────────────────────── */
function renderFilters() {
  const c = document.getElementById("categoryFilters");
  c.innerHTML = "";
  c.appendChild(makeFilterBtn("all", "all", activeFilter === "all", "#c0622a", "white"));
  CATEGORIES.forEach((cat) => {
    const active = activeFilter === cat.id;
    c.appendChild(makeFilterBtn(cat.id, `${cat.icon} ${cat.id}`, active,
      active ? cat.color : null, active ? "#2a2118" : null));
  });
}

function makeFilterBtn(cat, label, active, bg, color) {
  const b = document.createElement("button");
  b.className    = "filter-tag" + (active ? " active" : "");
  b.dataset.cat  = cat;
  b.textContent  = label;
  if (bg)     b.style.background   = bg;
  if (color)  b.style.color        = color;
  if (active) b.style.borderColor  = bg;
  return b;
}

/* ── RENDER: LIST ───────────────────────────────────────────────────────── */
function renderList() {
  const filtered    = activeFilter === "all" ? expenses : expenses.filter((e) => e.category === activeFilter);
  const grouped     = {};
  filtered.forEach((e) => { (grouped[e.date] = grouped[e.date] || []).push(e); });
  const sortedDates = Object.keys(grouped).sort((a, b) => b.localeCompare(a));

  const el = document.getElementById("expenseList");
  if (!sortedDates.length) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-icon">₹</div>
      <div class="empty-text">no expenses for ${navShort()}</div>
    </div>`;
    return;
  }

  el.innerHTML = "";
  sortedDates.forEach((date) => {
    const group    = grouped[date];
    const subtotal = group.reduce((s, e) => s + e.amount, 0);
    const groupEl  = document.createElement("div");
    groupEl.className = "date-group fade-in";
    groupEl.innerHTML = `
      <div class="date-header">
        <span class="date-label">${fmtDate(date)}</span>
        <span class="date-subtotal">${fmt(subtotal)}</span>
      </div>`;
    group.forEach((e) => {
      const cat  = getCat(e.category);
      const item = document.createElement("div");
      item.className = "expense-item";
      item.innerHTML = `
        <div class="cat-icon" style="background:${cat.color}22">${cat.icon}</div>
        <div class="expense-info">
          <div class="expense-note">${e.note}</div>
          <div class="expense-cat">${cat.label}</div>
        </div>
        <div class="expense-amount">${fmt(e.amount)}</div>
        <button class="del-btn" data-id="${e.id}">×</button>`;
      groupEl.appendChild(item);
    });
    el.appendChild(groupEl);
  });
}

/* ── SVG PIE CHART ──────────────────────────────────────────────────────── */
function drawPie(svgId, data, total) {
  const svg  = document.getElementById(svgId);
  svg.innerHTML = "";
  const CX = 74, CY = 74, R = 52;
  const pts  = data.filter((d) => d.value > 0);
  const tVal = pts.reduce((s, d) => s + d.value, 0);

  svg.appendChild(svgEl("circle", { cx: CX, cy: CY, r: R, fill: "none", stroke: "#ede8e0", "stroke-width": 20 }));

  if (!pts.length) {
    svg.appendChild(svgText(CX, CY + 4, "no data", "#b0a496", 10));
    return;
  }

  let angle = -Math.PI / 2;
  const slices = pts.map((d) => {
    const a = (d.value / tVal) * 2 * Math.PI;
    const s = angle; angle += a;
    return { ...d, a, start: s, end: angle,
      x1: CX + R * Math.cos(s),     y1: CY + R * Math.sin(s),
      x2: CX + R * Math.cos(angle), y2: CY + R * Math.sin(angle),
      large: a > Math.PI ? 1 : 0 };
  });

  const cg = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const tl = svgText(CX, 69, "TOTAL",            "#9a8e80", 8,  "'DM Mono',monospace",  1);
  const tv = svgText(CX, 84, fmt(total || tVal), "#c0622a", 12, "'Fraunces',serif", 0, "bold");
  cg.append(tl, tv);

  slices.forEach((s) => {
    const p = svgEl("path", {
      d: `M ${s.x1} ${s.y1} A ${R} ${R} 0 ${s.large} 1 ${s.x2} ${s.y2}`,
      fill: "none", stroke: s.color, "stroke-width": 20, "stroke-linecap": "butt",
    });
    p.style.cursor = "pointer";
    p.style.transition = "stroke-width .15s";
    p.addEventListener("mouseenter", () => {
      p.setAttribute("stroke-width", "26");
      tl.textContent = s.icon; tl.setAttribute("font-size", 14); tl.setAttribute("fill", s.color);
      tv.textContent = `${Math.round((s.value / tVal) * 100)}%`; tv.setAttribute("fill", s.color);
    });
    p.addEventListener("mouseleave", () => {
      p.setAttribute("stroke-width", "20");
      tl.textContent = "TOTAL"; tl.setAttribute("font-size", 8); tl.setAttribute("fill", "#9a8e80");
      tv.textContent = fmt(total || tVal); tv.setAttribute("fill", "#c0622a");
    });
    svg.appendChild(p);
    svg.appendChild(svgEl("line", {
      x1: CX + (R-12)*Math.cos(s.start), y1: CY + (R-12)*Math.sin(s.start),
      x2: CX + (R+12)*Math.cos(s.start), y2: CY + (R+12)*Math.sin(s.start),
      stroke: "#faf8f5", "stroke-width": 2,
    }));
  });
  svg.appendChild(cg);
}

function svgEl(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}
function svgText(x, y, text, fill, size, family = "'DM Mono',monospace", spacing = 0, weight = "normal") {
  const t = svgEl("text", { x, y, "text-anchor": "middle", fill, "font-size": size,
    "font-family": family, "letter-spacing": spacing, "font-weight": weight });
  t.textContent = text;
  return t;
}

/* ── RENDER: SUMMARY ────────────────────────────────────────────────────── */
async function renderSummary() {
  const data = await apiFetch(`/api/summary?month=${navStr()}`);
  if (!data) return;
  const { categories, total, all_time, count, weekly } = data;

  document.getElementById("statAllTime").textContent    = fmt(all_time);
  document.getElementById("statMonth").textContent      = fmt(total);
  document.getElementById("statMonthLabel").textContent = navShort();
  document.getElementById("statCount").textContent      = count;
  document.getElementById("statAvg").textContent        = count ? fmt(total / count) : "₹0";

  const catMap     = Object.fromEntries(categories.map((c) => [c.category, c.total]));
  const catPieData = CATEGORIES.map((c) => ({ ...c, value: catMap[c.id] || 0 })).filter((c) => c.value > 0);
  drawPie("catPie", catPieData, total);

  document.getElementById("catLegend").innerHTML =
    CATEGORIES.map((c) => ({ ...c, v: catMap[c.id] || 0 }))
      .filter((c) => c.v > 0).sort((a, b) => b.v - a.v).slice(0, 5)
      .map((c) => legendRow(c.color, `${c.icon} ${c.id}`, Math.round((c.v / (total || 1)) * 100)))
      .join("");

  const weekPieData = (weekly || []).map((w) => ({
    icon: ["①","②","③","④","⑤"][w.week_num - 1] || `W${w.week_num}`,
    value: w.total, color: WEEK_COLORS[(w.week_num - 1) % WEEK_COLORS.length], week_num: w.week_num,
  }));
  drawPie("weekPie", weekPieData, total);

  const daysInMonth = new Date(navYear, navMonth + 1, 0).getDate();
  document.getElementById("weekLegend").innerHTML = weekPieData.length
    ? weekPieData.map((w) => {
        const s = (w.week_num - 1) * 7 + 1;
        const e = Math.min(w.week_num * 7, daysInMonth);
        return legendRow(w.color, `${navShort()} ${s}–${e}`, Math.round((w.value / (total || 1)) * 100));
      }).join("")
    : `<div class="legend-item"><span class="legend-name" style="color:#b0a496">no data</span></div>`;

  const allCats = CATEGORIES.map((c) => ({ ...c, total: catMap[c.id] || 0 })).sort((a, b) => b.total - a.total);
  const maxVal  = allCats[0]?.total || 1;
  document.getElementById("barList").innerHTML = allCats.map((c) => `
    <div class="bar-item">
      <div class="bar-header">
        <span class="bar-name">${c.icon} ${c.label}</span>
        <span class="bar-amount ${c.total ? "" : "zero"}">${fmt(c.total)}</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:${(c.total / maxVal) * 100}%;background:${c.color}"></div>
      </div>
    </div>`).join("");
}

function legendRow(color, name, pct) {
  return `<div class="legend-item">
    <div class="legend-dot" style="background:${color}"></div>
    <span class="legend-name">${name}</span>
    <span class="legend-pct">${pct}%</span>
  </div>`;
}

/* ── FULL REFRESH ───────────────────────────────────────────────────────── */
async function refresh() {
  const data = await apiFetch(`/api/expenses?month=${navStr()}`);
  expenses   = data || [];
  const total = expenses.reduce((s, e) => s + e.amount, 0);
  renderHeader(total);
  renderFilters();
  if (activeView === "list") renderList();
  else await renderSummary();
}

/* ── MODAL ──────────────────────────────────────────────────────────────── */
function buildCatGrid() {
  const grid = document.getElementById("catGrid");
  grid.innerHTML = "";
  CATEGORIES.forEach((cat) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "cat-btn"; b.dataset.cat = cat.id;
    b.innerHTML = `<span class="cat-emoji">${cat.icon}</span><span class="cat-name">${cat.id}</span>`;
    b.addEventListener("click", () => {
      grid.querySelectorAll(".cat-btn").forEach((x) => {
        x.style.borderColor = ""; x.style.background = ""; x.style.color = "";
      });
      b.style.borderColor = cat.color;
      b.style.background  = cat.color + "22";
      b.style.color       = cat.color;
    });
    grid.appendChild(b);
  });
  grid.querySelector(".cat-btn").click();
}

function openModal() {
  document.getElementById("inputAmount").value = "";
  document.getElementById("inputNote").value   = "";
  document.getElementById("inputDate").value   = todayStr();
  buildCatGrid();
  document.getElementById("overlay").classList.remove("hidden");
  setTimeout(() => document.getElementById("inputAmount").focus(), 50);
}
function closeModal() {
  document.getElementById("overlay").classList.add("hidden");
}

async function submitExpense() {
  const amount = parseFloat(document.getElementById("inputAmount").value);
  if (!amount || amount <= 0) {
    document.getElementById("inputAmount").focus();
    showToast("Please enter a valid amount");
    return;
  }
  const note      = document.getElementById("inputNote").value.trim();
  const date      = document.getElementById("inputDate").value || todayStr();
  const activeCat = document.querySelector(".cat-btn[style*='border-color']");
  const category  = activeCat ? activeCat.dataset.cat : "other";

  const btn = document.getElementById("submitBtn");
  btn.textContent = "Saving…"; btn.disabled = true;

  const result = await apiFetch("/api/expenses", {
    method: "POST",
    body: JSON.stringify({ amount, note, category, date }),
  });

  btn.textContent = "Add Expense"; btn.disabled = false;
  if (!result) return;

  closeModal();
  const [y, m] = date.slice(0, 7).split("-").map(Number);
  navYear = y; navMonth = m - 1;
  await refresh();
}

/* ── EVENT LISTENERS ────────────────────────────────────────────────────── */
document.getElementById("prevMonth").addEventListener("click", async () => {
  if (isNavigating) return;
  isNavigating = true;
  document.getElementById("prevMonth").disabled = true;
  document.getElementById("nextMonth").disabled = true;
  goPrev();
  await refresh();
  isNavigating = false;
});

document.getElementById("nextMonth").addEventListener("click", async () => {
  if (isNavigating || isCurrent()) return;
  isNavigating = true;
  document.getElementById("prevMonth").disabled = true;
  document.getElementById("nextMonth").disabled = true;
  goNext();
  await refresh();
  isNavigating = false;
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", async () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    activeView = tab.dataset.tab;
    document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
    document.getElementById(`view-${activeView}`).classList.remove("hidden");
    if (activeView === "summary") await renderSummary(); else renderList();
  });
});

document.getElementById("categoryFilters").addEventListener("click", (e) => {
  const b = e.target.closest(".filter-tag");
  if (!b) return;
  activeFilter = b.dataset.cat;
  renderFilters();
  renderList();
});

document.getElementById("expenseList").addEventListener("click", async (e) => {
  const b = e.target.closest(".del-btn");
  if (!b) return;
  await apiFetch(`/api/expenses/${b.dataset.id}`, { method: "DELETE" });
  await refresh();
});

document.getElementById("openForm").addEventListener("click", openModal);
document.getElementById("closeForm").addEventListener("click", closeModal);
document.getElementById("submitBtn").addEventListener("click", submitExpense);
document.getElementById("overlay").addEventListener("click", (e) => {
  if (e.target.id === "overlay") closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
  if (e.key === "Enter" && !document.getElementById("overlay").classList.contains("hidden"))
    submitExpense();
});

/* ── INIT ───────────────────────────────────────────────────────────────── */
refresh();
