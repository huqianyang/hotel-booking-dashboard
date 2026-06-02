let filters = {};
const percent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;

async function apiGet(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) throw new Error(payload.message || "请求失败");
  return payload.data;
}

function queryString() {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  return params.toString();
}

async function setFilter(key, value) {
  filters[key] = value;
  await loadOverview();
}

function renderChips(dataFilters) {
  const active = Object.entries(dataFilters || {}).filter(([, value]) => value);
  document.querySelector("#viz-filter-chips").innerHTML = active.length
    ? active.map(([key, value]) => `<span class="chip is-active">${key}=${value}</span>`).join("")
    : `<span class="chip">全部</span>`;
}

function renderSummary(summary) {
  document.querySelector("#viz-summary").innerHTML = [
    ["当前订单数", Number(summary.booking_count || 0).toLocaleString(), "booking_count"],
    ["当前取消率", percent(summary.cancel_rate), "cancel_rate"],
    ["已取消订单", Number(summary.cancel_count || 0).toLocaleString(), "cancel_count"],
    ["平均 ADR", Number(summary.avg_adr || 0).toFixed(2), "avg_adr"],
  ].map(([name, value, note]) => `<article class="metric-card"><small>${name}</small><strong>${value}</strong><em>${note}</em></article>`).join("");
}

function renderTrend(rows) {
  rows = rows && rows.length ? rows.slice(-12) : [];
  const chart = document.querySelector("#viz-trend");
  if (!rows || !rows.length) {
    chart.innerHTML = "<div class='log-line'>暂无趋势数据</div>";
    return;
  }
  const max = Math.max(...rows.map((row) => row.booking_count || 1), 1);
  chart.style.setProperty("--bars", rows.length);
  chart.innerHTML = rows.map((row, index) => `
    <button class="bar-slot" data-month="${row.period}" type="button">
      <span class="bar ${index % 2 ? "green" : ""} ${filters.month === row.period ? "is-selected" : ""}" style="height:${(row.booking_count || 1) / max * 100}%"><i class="bar-dot"></i></span>
      <span class="bar-label">${row.period}</span>
    </button>`).join("");
  chart.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => setFilter("month", button.dataset.month)));
}

function renderRank(selector, rows, key) {
  const container = document.querySelector(selector);
  if (!rows || !rows.length) {
    container.innerHTML = "<div class='log-line'>暂无数据</div>";
    return;
  }
  const max = Math.max(...rows.map((row) => row.cancel_rate || row.value || 1), 1);
  container.innerHTML = rows.map((row) => {
    const value = row[key] || row.name || row.code;
    return `
      <div class="rank-row">
        <button type="button" data-value="${value}">${row.name || value}</button>
        <span class="track"><b class="${Number(row.cancel_rate || row.value || 0) > .5 ? "warn" : ""}" style="width:${Number(row.cancel_rate || row.value || 0) / max * 100}%"></b></span>
        <strong>${percent(row.cancel_rate ?? row.value)}</strong>
      </div>`;
  }).join("");
  container.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => setFilter(key, button.dataset.value)));
}

function renderDonut(summary) {
  document.querySelector("#cancel-donut").dataset.label = `取消率\n${percent(summary.cancel_rate)}`;
}

function renderTags(rows) {
  document.querySelector("#risk-tags").innerHTML = (rows || []).map((tag, index) => `
    <button type="button" class="${index % 3 === 0 ? "big" : index % 2 === 0 ? "mid" : ""}" data-value="${tag.name}">${tag.name}<br>${tag.value}</button>
  `).join("");
  document.querySelectorAll("#risk-tags button").forEach((button) => button.addEventListener("click", () => setFilter("risk_tag", button.dataset.value)));
}

function renderMap(rows) {
  const max = Math.max(...(rows || []).map((country) => country.booking_count || 1), 1);
  document.querySelector("#country-map").innerHTML = (rows || []).slice(0, 12).map((country, index) => {
    const left = 15 + (index % 4) * 24;
    const top = 24 + Math.floor(index / 4) * 24;
    const size = 8 + (country.booking_count || 1) / max * 12;
    return `
      <button type="button" class="map-point" style="left:${left}%;top:${top}%;font-size:${size}px" data-code="${country.code}">
        ${country.code} ${percent(country.value)}
      </button>`;
  }).join("");
  document.querySelectorAll(".map-point").forEach((button) => button.addEventListener("click", () => setFilter("country_code", button.dataset.code)));
}

function renderOrders(rows) {
  document.querySelector("#viz-orders").innerHTML = rows && rows.length ? rows.map((row) => `
    <tr><td>${row.booking_id}</td><td>${row.hotel_name || "-"}</td><td>${row.country_name || "-"}</td><td>${row.lead_time}</td><td>${Number(row.adr || 0).toFixed(1)}</td><td>${row.is_canceled_label || "-"}</td></tr>
  `).join("") : "<tr><td colspan='6'>暂无订单</td></tr>";
}

async function loadOverview() {
  const suffix = queryString();
  const data = await apiGet(`/api/visualization/overview${suffix ? `?${suffix}` : ""}`);
  renderChips(data.filters);
  renderSummary(data.summary);
  renderTrend(data.trend);
  renderRank("#factor-bars", data.factor_bars, "name");
  renderDonut(data.summary);
  renderTags(data.risk_tags);
  renderRank("#channel-ranking", data.channel_ranking, "name");
  renderMap(data.country_map);
  renderOrders(data.sample_orders);
}

document.querySelector("#viz-reset").addEventListener("click", async () => {
  filters = {};
  await loadOverview();
});

loadOverview().catch((error) => {
  document.querySelector("#viz-summary").innerHTML = `<div class="log-line">${error.message}</div>`;
});
