let summary = {
  total_bookings: 0,
  canceled_bookings: 0,
  cancel_rate: 0,
  avg_adr: 0,
  high_risk_count: 0,
  latest_event_time: "加载中",
};
let trend = [];
let channels = [];
let countries = [];
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

function renderTrend() {
  const rows = trend.slice(-12);
  const chart = document.querySelector("#dashboard-trend");
  if (!rows.length) {
    chart.innerHTML = `<div class="log-line">暂无趋势数据</div>`;
    return;
  }
  const max = Math.max(...rows.map(([, count]) => count), 1);
  chart.style.setProperty("--bars", rows.length);
  chart.innerHTML = rows.map(([period, count, rate], index) => `
    <button class="bar-slot" data-period="${period}" title="跳转查询 ${period}">
      <span class="bar ${index % 2 ? "green" : ""} ${index === rows.length - 1 ? "is-selected" : ""}" style="height:${Math.max(20, count / max * 100)}%">
        <i class="bar-dot" style="top:${Math.max(-12, 95 - rate * 145)}%"></i>
      </span>
      <span class="bar-label">${period}</span>
    </button>
  `).join("");
  chart.querySelectorAll(".bar-slot").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.href = `/visualization?month=${encodeURIComponent(button.dataset.period)}`;
    });
  });
}

function renderRanks(selector, rows, mode) {
  const max = Math.max(...rows.map((row) => row[2]), 1);
  document.querySelector(selector).innerHTML = rows.map(([value, label, count, rate]) => {
    const query = mode === "country" ? `country_code=${value}` : `market_segment=${encodeURIComponent(value)}`;
    return `
      <div class="rank-row">
        <button type="button" data-query="${query}">${label}</button>
        <span class="track"><b class="${rate > .5 ? "warn" : ""}" style="width:${count / max * 100}%"></b></span>
        <strong>${formatPercent(rate)}</strong>
      </div>
    `;
  }).join("");
  document.querySelectorAll(`${selector} button`).forEach((button) => {
    button.addEventListener("click", () => { window.location.href = `/bookings?${button.dataset.query}`; });
  });
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
  const [summaryData, trendData, overviewData, realtimeData] = await Promise.all([
    apiGet("/api/dashboard/summary"),
    apiGet("/api/dashboard/trend?granularity=month"),
    apiGet("/api/visualization/overview"),
    apiGet("/api/realtime/recent-predictions"),
  ]);

  summary = summaryData;
  trend = (trendData.points || []).map((row) => [row.period, row.booking_count, row.cancel_rate]);
  channels = (overviewData.channel_ranking || []).slice(0, 5).map((row) => [
    row.market_segment,
    row.name,
    row.booking_count,
    row.cancel_rate,
  ]);
  countries = (overviewData.country_map || []).slice(0, 5).map((row) => [
    row.code,
    row.name,
    row.booking_count,
    row.value,
  ]);
  recent = realtimeData.items || [];

  renderSummary();
  renderTrend();
  renderRanks("#channel-risk", channels, "channel");
  renderRanks("#country-risk", countries, "country");
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
