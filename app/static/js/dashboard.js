let summary = {
  total_bookings: 0,
  realtime_processed_count: 0,
  average_cancel_probability: 0,
  high_risk_count: 0,
  updated_at: null,
  latest_event_time: "加载中",
  status: "waiting",
  message: "等待实时链路数据",
};
let recentPayload = { items: [], status: "waiting", message: "等待实时链路数据" };
let currentGranularity = "day";

const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;
const formatNumber = (value) => Number(value || 0).toLocaleString();

async function apiGet(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.message || `请求失败：${url}`);
  }
  return payload.data;
}

function renderSummary() {
  const cards = [
    ["当前总预订量", formatNumber(summary.total_bookings), "80008 + 实时处理量"],
    ["实时处理量", formatNumber(summary.realtime_processed_count), summary.status === "waiting" ? summary.message : "realtime_processed_count"],
    ["平均取消概率", formatPercent(summary.average_cancel_probability), "实时预测均值"],
    ["当前高风险订单", formatNumber(summary.high_risk_count), "实时高风险订单"],
  ];
  document.querySelector("#dashboard-summary").innerHTML = cards.map(([name, value, note]) => `
    <article class="metric-card"><small>${name}</small><strong>${value}</strong><em>${note}</em></article>
  `).join("");
  document.querySelector("#latest-event-time").textContent = summary.updated_at || summary.latest_event_time || summary.message || "暂无数据";
}

function renderRecent() {
  const rows = recentPayload.items || [];
  if (recentPayload.status === "waiting" || !rows.length) {
    document.querySelector("#recent-predictions").innerHTML = `<tr><td colspan="4">等待实时链路数据</td></tr>`;
    return;
  }
  document.querySelector("#recent-predictions").innerHTML = rows.map((item) => `
    <tr>
      <td><a href="/prediction?booking_id=${item.booking_id}">#${item.booking_id}</a></td>
      <td>${item.country_name || item.country_code || "-"}</td>
      <td>${formatPercent(item.cancel_probability)}</td>
      <td><span class="risk-pill ${item.cancel_probability > .7 ? "" : item.cancel_probability > .35 ? "medium" : "low"}">${item.risk_level_name || item.risk_level || "-"}</span></td>
    </tr>
  `).join("");
}

async function renderDashboardCharts() {
  await Promise.all([
    renderPyeChart("#dashboard-trend", `/api/charts/dashboard-trend?granularity=${currentGranularity}`),
    renderPyeChart("#channel-risk", "/api/charts/dashboard-channel-risk"),
    renderPyeChart("#country-risk", "/api/charts/dashboard-country-risk"),
  ]);
}

async function loadDashboard() {
  const [summaryData, realtimeData] = await Promise.all([
    apiGet("/api/dashboard/summary"),
    apiGet("/api/realtime/recent-predictions"),
  ]);

  summary = { ...summary, ...summaryData };
  recentPayload = realtimeData;

  renderSummary();
  renderRecent();
  await renderDashboardCharts();
}

document.querySelectorAll("#trend-granularity button").forEach((button) => {
  button.addEventListener("click", () => {
    currentGranularity = button.dataset.granularity;
    document.querySelectorAll("#trend-granularity button").forEach((item) => item.classList.toggle("is-active", item === button));
    renderPyeChart("#dashboard-trend", `/api/charts/dashboard-trend?granularity=${currentGranularity}`).catch(showError);
  });
});

function showError(error) {
  document.querySelector("#dashboard-summary").innerHTML = `<article class="metric-card"><small>加载失败</small><strong>API</strong><em>${error.message}</em></article>`;
}

loadDashboard().catch(showError);
setInterval(() => loadDashboard().catch(showError), 5000);
