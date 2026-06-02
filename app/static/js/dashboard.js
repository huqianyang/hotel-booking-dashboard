const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;
const apiGet = async (url) => {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.message || `请求失败：${url}`);
  }
  return payload.data;
};

function showError(selector, message) {
  const target = document.querySelector(selector);
  if (target) target.innerHTML = `<div class="log-line">${message}</div>`;
}

function renderSummary(summary) {
  const cards = [
    ["总预订量", Number(summary.total_bookings || 0).toLocaleString(), "active bookings"],
    ["取消率", formatPercent(summary.cancel_rate), `${Number(summary.canceled_bookings || 0).toLocaleString()} 条已取消`],
    ["平均 ADR", Number(summary.avg_adr || 0).toFixed(2), "平均每日房价"],
    ["高风险订单", Number(summary.high_risk_count || 0).toLocaleString(), "lead_time >= 90"],
  ];
  document.querySelector("#dashboard-summary").innerHTML = cards.map(([name, value, note]) => `
    <article class="metric-card"><small>${name}</small><strong>${value}</strong><em>${note}</em></article>
  `).join("");
  document.querySelector("#latest-event-time").textContent = summary.latest_event_time || "暂无数据";
  document.querySelector("#sidebar-latest-date").textContent = (summary.latest_event_time || "暂无").slice(0, 10);
}

function renderTrend(points) {
  const rows = points && points.length ? points.slice(-12) : [];
  const chart = document.querySelector("#dashboard-trend");
  if (!rows.length) {
    chart.innerHTML = "<div class='log-line'>暂无趋势数据</div>";
    return;
  }
  const max = Math.max(...rows.map((row) => row.booking_count || 0), 1);
  chart.style.setProperty("--bars", rows.length);
  chart.innerHTML = rows.map((row, index) => `
    <button class="bar-slot" data-period="${row.period}" title="查看 ${row.period}">
      <span class="bar ${index % 2 ? "green" : ""}" style="height:${Math.max(18, (row.booking_count || 0) / max * 100)}%">
        <i class="bar-dot" style="top:${Math.max(-10, 92 - Number(row.cancel_rate || 0) * 135)}%"></i>
      </span>
      <span class="bar-label">${row.period}</span>
    </button>
  `).join("");
  chart.querySelectorAll(".bar-slot").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.href = `/bookings?keyword=${encodeURIComponent(button.dataset.period)}`;
    });
  });
}

function renderRanks(selector, rows, mode) {
  const container = document.querySelector(selector);
  if (!rows || !rows.length) {
    container.innerHTML = "<div class='log-line'>暂无排行数据</div>";
    return;
  }
  const max = Math.max(...rows.map((row) => row.booking_count || 1), 1);
  container.innerHTML = rows.slice(0, 5).map((row) => {
    const label = row.name || row.code || "未知";
    const query = mode === "country"
      ? `country_code=${encodeURIComponent(row.code || "")}`
      : `market_segment=${encodeURIComponent(row.name || "")}`;
    return `
      <div class="rank-row">
        <button type="button" data-query="${query}">${label}</button>
        <span class="track"><b class="${Number(row.cancel_rate || row.value || 0) > .5 ? "warn" : ""}" style="width:${(row.booking_count || 1) / max * 100}%"></b></span>
        <strong>${formatPercent(row.cancel_rate ?? row.value)}</strong>
      </div>
    `;
  }).join("");
  container.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => { window.location.href = `/bookings?${button.dataset.query}`; });
  });
}

function renderRecent(items) {
  const rows = items || [];
  document.querySelector("#recent-predictions").innerHTML = rows.length ? rows.map((item) => `
    <tr>
      <td><a href="/prediction?booking_id=${item.booking_id}">#${item.booking_id}</a></td>
      <td>${item.country_name || "-"}</td>
      <td>${formatPercent(item.cancel_probability)}</td>
      <td><span class="risk-pill ${item.cancel_probability > .7 ? "" : item.cancel_probability > .35 ? "medium" : "low"}">${item.risk_level_name || "-"}</span></td>
    </tr>
  `).join("") : "<tr><td colspan='4'>暂无实时预测记录</td></tr>";
}

async function loadTrend(granularity = "month") {
  const data = await apiGet(`/api/dashboard/trend?granularity=${granularity}`);
  renderTrend(data.points);
}

async function initDashboard() {
  try {
    const [summary, overview, realtime] = await Promise.all([
      apiGet("/api/dashboard/summary"),
      apiGet("/api/visualization/overview"),
      apiGet("/api/realtime/recent-predictions"),
    ]);
    renderSummary(summary);
    renderRanks("#channel-risk", overview.channel_ranking, "channel");
    renderRanks("#country-risk", overview.country_map, "country");
    renderRecent(realtime.items);
    await loadTrend("month");
  } catch (error) {
    showError("#dashboard-summary", error.message);
  }
}

document.querySelector("#trend-granularity")?.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-granularity]");
  if (!button) return;
  document.querySelectorAll("#trend-granularity button").forEach((item) => item.classList.toggle("is-active", item === button));
  await loadTrend(button.dataset.granularity);
});

document.querySelector("#toggle-simulation")?.addEventListener("click", (event) => {
  const status = document.querySelector("#simulation-status");
  const running = status.textContent === "运行中";
  status.textContent = running ? "已暂停" : "运行中";
  event.currentTarget.textContent = running ? "启动模拟" : "暂停模拟";
});

initDashboard();
