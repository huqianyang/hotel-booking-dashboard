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

function renderOrders() {
  document.querySelector("#viz-orders").innerHTML = overview.sample_orders.length ? overview.sample_orders.map((row) => `
    <tr><td>${row.booking_id}</td><td>${row.hotel_name}</td><td>${row.country_name}</td><td>${row.lead_time}</td><td>${Number(row.adr || 0).toFixed(1)}</td><td>${row.is_canceled_label}</td></tr>
  `).join("") : `<tr><td colspan="6">暂无订单</td></tr>`;
}

async function renderAll() {
  const suffix = queryString();
  const query = suffix ? `?${suffix}` : "";
  renderChips();
  renderSummary();
  renderOrders();
  await Promise.all([
    renderPyeChart("#viz-trend", `/api/charts/visualization-trend${query}`, {
      onClick: (params) => setFilter("month", params.name),
    }),
    renderPyeChart("#factor-bars", `/api/charts/visualization-factor-bars${query}`, {
      onClick: (params) => setFilter("risk_tag", params.name),
    }),
    renderPyeChart("#cancel-donut", `/api/charts/visualization-cancel-structure${query}`),
    renderPyeChart("#risk-tags", `/api/charts/visualization-risk-tags${query}`, {
      onClick: (params) => setFilter("risk_tag", params.name),
    }),
    renderPyeChart("#channel-ranking", `/api/charts/visualization-channel-ranking${query}`, {
      onClick: (params) => setFilter("market_segment", params.name),
    }),
    renderPyeChart("#country-map", `/api/charts/visualization-country-risk${query}`),
  ]);
}

async function loadOverview() {
  const suffix = queryString();
  overview = await apiGet(`/api/visualization/overview${suffix ? `?${suffix}` : ""}`);
  await renderAll();
}

function showError(error) {
  document.querySelector("#viz-summary").innerHTML = `<article class="metric-card"><small>加载失败</small><strong>API</strong><em>${error.message}</em></article>`;
}

document.querySelector("#viz-reset").addEventListener("click", () => { filters = {}; loadOverview().catch(showError); });
applyQueryParams();
loadOverview().catch(showError);
