const overview = {
  filters: {},
  summary: { booking_count: 8642, cancel_count: 4890, cancel_rate: 0.566, avg_adr: 96.25 },
  trend: [
    { period: "2017-01", booking_count: 3200, cancel_rate: 0.4531 },
    { period: "2017-02", booking_count: 2860, cancel_rate: 0.387 },
    { period: "2017-03", booking_count: 4100, cancel_rate: 0.566 },
    { period: "2017-04", booking_count: 3620, cancel_rate: 0.421 },
    { period: "2017-05", booking_count: 4960, cancel_rate: 0.371 },
  ],
  cancel_structure: [{ name: "已取消", value: 4890 }, { name: "未取消", value: 3752 }],
  factor_bars: [
    { name: "提前预订超过 120 天", risk_tag: "lead_time_high", cancel_rate: 0.61 },
    { name: "不可退订金", risk_tag: "non_refund", cancel_rate: 0.72 },
    { name: "无特殊需求", risk_tag: "no_special_request", cancel_rate: 0.43 },
  ],
  channel_ranking: [
    { name: "Groups", market_segment: "Groups", booking_count: 1920, cancel_rate: 0.611 },
    { name: "Online TA", market_segment: "Online TA", booking_count: 5406, cancel_rate: 0.436 },
    { name: "Direct", market_segment: "Direct", booking_count: 870, cancel_rate: 0.189 },
  ],
  country_map: [
    { code: "PRT", name: "葡萄牙", value: 0.566, booking_count: 8642, left: 28, top: 47 },
    { code: "FRA", name: "法国", value: 0.185, booking_count: 1880, left: 48, top: 36 },
    { code: "DEU", name: "德国", value: 0.167, booking_count: 1420, left: 66, top: 52 },
  ],
  risk_tags: [
    { name: "Portugal", value: 520 }, { name: "Online TA", value: 430 }, { name: "提前预订长", value: 610 },
    { name: "无特殊需求", value: 260 }, { name: "Groups", value: 340 }, { name: "ADR 偏高", value: 190 },
  ],
  sample_orders: [
    { booking_id: 1001, hotel_name: "城市酒店", country_name: "葡萄牙", lead_time: 120, adr: 98.5, is_canceled_label: "已取消" },
    { booking_id: 1002, hotel_name: "度假酒店", country_name: "葡萄牙", lead_time: 84, adr: 115.2, is_canceled_label: "已取消" },
    { booking_id: 1003, hotel_name: "城市酒店", country_name: "葡萄牙", lead_time: 42, adr: 88.0, is_canceled_label: "未取消" },
  ],
};
let filters = { country_code: "PRT", risk_tag: "high" };
const percent = (value) => `${(value * 100).toFixed(1)}%`;
function setFilter(key, value) { filters[key] = value; renderAll(); }
function renderChips() {
  const labels = Object.entries(filters).map(([key, value]) => `<span class="chip is-active">${key}=${value}</span>`);
  document.querySelector("#viz-filter-chips").innerHTML = labels.length ? labels.join("") : `<span class="chip">全部</span>`;
}
function renderSummary() {
  const s = overview.summary;
  document.querySelector("#viz-summary").innerHTML = [
    ["当前订单数", s.booking_count.toLocaleString(), "booking_count"],
    ["当前取消率", percent(s.cancel_rate), "cancel_rate"],
    ["已取消订单", s.cancel_count.toLocaleString(), "cancel_count"],
    ["平均 ADR", s.avg_adr.toFixed(2), "avg_adr"],
  ].map(([n, v, note]) => `<article class="metric-card"><small>${n}</small><strong>${v}</strong><em>${note}</em></article>`).join("");
}
function renderTrend() {
  const max = Math.max(...overview.trend.map((row) => row.booking_count));
  const chart = document.querySelector("#viz-trend");
  chart.style.setProperty("--bars", overview.trend.length);
  chart.innerHTML = overview.trend.map((row, index) => `
    <button class="bar-slot" data-month="${row.period}">
      <span class="bar ${index % 2 ? "green" : ""} ${filters.month === row.period ? "is-selected" : ""}" style="height:${row.booking_count / max * 100}%"><i class="bar-dot"></i></span>
      <span class="bar-label">${row.period.slice(5)}月</span>
    </button>`).join("");
  chart.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => setFilter("month", button.dataset.month)));
}
function renderRank(selector, rows, key) {
  const max = Math.max(...rows.map((row) => row.cancel_rate));
  document.querySelector(selector).innerHTML = rows.map((row) => `
    <div class="rank-row">
      <button type="button" data-value="${row[key]}">${row.name}</button>
      <span class="track"><b class="${row.cancel_rate > .5 ? "warn" : ""}" style="width:${row.cancel_rate / max * 100}%"></b></span>
      <strong>${percent(row.cancel_rate)}</strong>
    </div>`).join("");
  document.querySelectorAll(`${selector} button`).forEach((button) => button.addEventListener("click", () => setFilter(key, button.dataset.value)));
}
function renderDonut() {
  document.querySelector("#cancel-donut").dataset.label = `取消率\n${percent(overview.summary.cancel_rate)}`;
}
function renderTags() {
  document.querySelector("#risk-tags").innerHTML = overview.risk_tags.map((tag, index) => `
    <button type="button" class="${index % 3 === 0 ? "big" : index % 2 === 0 ? "mid" : ""}" data-value="${tag.name}">${tag.name}</button>
  `).join("");
  document.querySelectorAll("#risk-tags button").forEach((button) => button.addEventListener("click", () => setFilter("risk_tag", button.dataset.value)));
}
function renderMap() {
  document.querySelector("#country-map").innerHTML = overview.country_map.map((country) => `
    <button type="button" class="map-point" style="left:${country.left}%;top:${country.top}%" data-code="${country.code}">
      ${country.name} ${percent(country.value)}
    </button>`).join("");
  document.querySelectorAll(".map-point").forEach((button) => button.addEventListener("click", () => setFilter("country_code", button.dataset.code)));
}
function renderOrders() {
  document.querySelector("#viz-orders").innerHTML = overview.sample_orders.map((row) => `
    <tr><td>${row.booking_id}</td><td>${row.hotel_name}</td><td>${row.country_name}</td><td>${row.lead_time}</td><td>${row.adr.toFixed(1)}</td><td>${row.is_canceled_label}</td></tr>
  `).join("");
}
function renderAll() {
  renderChips(); renderSummary(); renderTrend(); renderRank("#factor-bars", overview.factor_bars, "risk_tag");
  renderDonut(); renderTags(); renderRank("#channel-ranking", overview.channel_ranking, "market_segment"); renderMap(); renderOrders();
}
document.querySelector("#viz-reset").addEventListener("click", () => { filters = {}; renderAll(); });
renderAll();
