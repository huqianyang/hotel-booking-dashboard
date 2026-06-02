let summary = {
  total_bookings: 0,
  canceled_bookings: 0,
  cancel_rate: 0,
  avg_adr: 0,
  high_risk_count: 0,
  latest_event_time: "加载中",
};
let recent = [];

const formatPercent = (value) => `${(value * 100).toFixed(1)}%`;

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
    ["当前总预订量", summary.total_bookings.toLocaleString(), "真实 API 返回的活跃订单"],
    ["历史取消率", formatPercent(summary.cancel_rate), `${summary.canceled_bookings.toLocaleString()} 条已取消`],
    ["平均每日房价", Number(summary.avg_adr || 0).toFixed(2), "字段：avg_adr"],
    ["当前高风险订单", summary.high_risk_count.toLocaleString(), "lead_time >= 90"],
  ];
  document.querySelector("#dashboard-summary").innerHTML = cards.map(([name, value, note]) => `
    <article class="metric-card"><small>${name}</small><strong>${value}</strong><em>${note}</em></article>
  `).join("");
  document.querySelector("#latest-event-time").textContent = summary.latest_event_time || "暂无数据";
}

function renderRecent() {
  document.querySelector("#recent-predictions").innerHTML = recent.length ? recent.map((item) => `
    <tr>
      <td><a href="/prediction?booking_id=${item.booking_id}">#${item.booking_id}</a></td>
      <td>${item.country_name}</td>
      <td>${formatPercent(item.cancel_probability)}</td>
      <td><span class="risk-pill ${item.cancel_probability > .7 ? "" : item.cancel_probability > .35 ? "medium" : "low"}">${item.risk_level_name}</span></td>
    </tr>
  `).join("") : `<tr><td colspan="4">暂无预测记录</td></tr>`;
}

async function loadDashboard() {
  const [summaryData, realtimeData] = await Promise.all([
    apiGet("/api/dashboard/summary"),
    apiGet("/api/realtime/recent-predictions"),
  ]);

  summary = summaryData;
  recent = realtimeData.items || [];

  renderSummary();
  await Promise.all([
    renderPyeChart("#dashboard-trend", "/api/charts/dashboard-trend?granularity=month"),
    renderPyeChart("#channel-risk", "/api/charts/dashboard-channel-risk"),
    renderPyeChart("#country-risk", "/api/charts/dashboard-country-risk"),
  ]);
  renderRecent();
}

document.querySelector("#toggle-simulation")?.addEventListener("click", (event) => {
  const status = document.querySelector("#simulation-status");
  const running = status.textContent === "运行中";
  status.textContent = running ? "已暂停" : "运行中";
  event.currentTarget.textContent = running ? "启动模拟" : "暂停模拟";
});

loadDashboard().catch((error) => {
  document.querySelector("#dashboard-summary").innerHTML = `<article class="metric-card"><small>加载失败</small><strong>API</strong><em>${error.message}</em></article>`;
});
