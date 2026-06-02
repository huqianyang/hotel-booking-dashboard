let overview = {
  filters: {},
  summary: { booking_count: 0, cancel_count: 0, cancel_rate: 0, avg_adr: 0 },
  trend: [],
  cancel_structure: [],
  factor_bars: [],
  channel_ranking: [],
  country_map: [],
  risk_tags: [],
  sample_orders: [],
};
let filters = {};

const percent = (value) => `${(value * 100).toFixed(1)}%`;

async function apiGet(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.message || `请求失败：${url}`);
  }
  return payload.data;
}

function queryString() {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  return params.toString();
}

function setFilter(key, value) {
  filters[key] = value;
  loadOverview().catch(showError);
}

function applyQueryParams() {
  const params = new URLSearchParams(window.location.search);
  ["country_code", "month", "market_segment", "customer_type", "risk_tag"].forEach((key) => {
    const value = params.get(key);
    if (value) filters[key] = value;
  });
}

function renderChips() {
  const active = Object.entries(overview.filters || {}).filter(([, value]) => value);
  document.querySelector("#viz-filter-chips").innerHTML = active.length
    ? active.map(([key, value]) => `<span class="chip is-active">${key}=${value}</span>`).join("")
    : `<span class="chip">全部</span>`;
}

function renderSummary() {
  const s = overview.summary;
  document.querySelector("#viz-summary").innerHTML = [
    ["当前订单数", s.booking_count.toLocaleString(), "booking_count"],
    ["当前取消率", percent(s.cancel_rate), "cancel_rate"],
    ["已取消订单", s.cancel_count.toLocaleString(), "cancel_count"],
    ["平均 ADR", Number(s.avg_adr || 0).toFixed(2), "avg_adr"],
  ].map(([n, v, note]) => `<article class="metric-card"><small>${n}</small><strong>${v}</strong><em>${note}</em></article>`).join("");
}

function renderTrend() {
  const rows = overview.trend.slice(-12);
  const max = Math.max(...rows.map((row) => row.booking_count), 1);
  const chart = document.querySelector("#viz-trend");
  chart.style.setProperty("--bars", rows.length || 1);
  chart.innerHTML = rows.length ? rows.map((row, index) => `
    <button class="bar-slot" data-month="${row.period}">
      <span class="bar ${index % 2 ? "green" : ""} ${filters.month === row.period ? "is-selected" : ""}" style="height:${Math.max(20, row.booking_count / max * 100)}%"><i class="bar-dot"></i></span>
      <span class="bar-label">${row.period}</span>
    </button>`).join("") : `<div class="log-line">暂无趋势数据</div>`;
  chart.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => setFilter("month", button.dataset.month)));
}

function renderRank(selector, rows, key) {
  const max = Math.max(...rows.map((row) => row.cancel_rate), 1);
  document.querySelector(selector).innerHTML = rows.length ? rows.map((row) => `
    <div class="rank-row">
      <button type="button" data-value="${row[key] || row.name}">${row.name}</button>
      <span class="track"><b class="${row.cancel_rate > .5 ? "warn" : ""}" style="width:${row.cancel_rate / max * 100}%"></b></span>
      <strong>${percent(row.cancel_rate)}</strong>
    </div>`).join("") : `<div class="log-line">暂无排行数据</div>`;
  document.querySelectorAll(`${selector} button`).forEach((button) => button.addEventListener("click", () => setFilter(key, button.dataset.value)));
}

function renderDonut() {
  document.querySelector("#cancel-donut").dataset.label = `取消率\n${percent(overview.summary.cancel_rate)}`;
}

function renderTags() {
  document.querySelector("#risk-tags").innerHTML = overview.risk_tags.map((tag, index) => `
    <button type="button" class="${index % 3 === 0 ? "big" : index % 2 === 0 ? "mid" : ""}" data-value="${tag.name}">${tag.name}<br>${tag.value}</button>
  `).join("");
  document.querySelectorAll("#risk-tags button").forEach((button) => button.addEventListener("click", () => setFilter("risk_tag", button.dataset.value)));
}

function renderMap() {
  const max = Math.max(...overview.country_map.map((country) => country.booking_count), 1);
  document.querySelector("#country-map").innerHTML = overview.country_map.slice(0, 12).map((country, index) => {
    const left = 15 + (index % 4) * 24;
    const top = 24 + Math.floor(index / 4) * 24;
    const size = 8 + country.booking_count / max * 12;
    return `
      <button type="button" class="map-point" style="left:${left}%;top:${top}%;font-size:${size}px" data-code="${country.code}">
        ${country.name} ${percent(country.value)}
      </button>`;
  }).join("");
  document.querySelectorAll(".map-point").forEach((button) => button.addEventListener("click", () => setFilter("country_code", button.dataset.code)));
}

function renderOrders() {
  document.querySelector("#viz-orders").innerHTML = overview.sample_orders.length ? overview.sample_orders.map((row) => `
    <tr><td>${row.booking_id}</td><td>${row.hotel_name}</td><td>${row.country_name}</td><td>${row.lead_time}</td><td>${Number(row.adr || 0).toFixed(1)}</td><td>${row.is_canceled_label}</td></tr>
  `).join("") : `<tr><td colspan="6">暂无订单</td></tr>`;
}

function renderAll() {
  renderChips(); renderSummary(); renderTrend(); renderRank("#factor-bars", overview.factor_bars, "risk_tag");
  renderDonut(); renderTags(); renderRank("#channel-ranking", overview.channel_ranking, "market_segment"); renderMap(); renderOrders();
}

async function loadOverview() {
  const suffix = queryString();
  overview = await apiGet(`/api/visualization/overview${suffix ? `?${suffix}` : ""}`);
  renderAll();
}

function showError(error) {
  document.querySelector("#viz-summary").innerHTML = `<article class="metric-card"><small>加载失败</small><strong>API</strong><em>${error.message}</em></article>`;
}

document.querySelector("#viz-reset").addEventListener("click", () => { filters = {}; loadOverview().catch(showError); });
applyQueryParams();
loadOverview().catch(showError);
