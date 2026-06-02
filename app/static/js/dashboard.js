const summary = {
  total_bookings: 80256,
  canceled_bookings: 29722,
  cancel_rate: 0.3704,
  avg_adr: 101.83,
  high_risk_count: 58,
  latest_event_time: "2017-01-14 14:00:00",
};

const trend = [
  ["08:00-10:00", 56, 0.286],
  ["10:00-12:00", 88, 0.354],
  ["12:00-14:00", 156, 0.432],
  ["14:00-16:00", 112, 0.388],
  ["16:00-18:00", 190, 0.451],
  ["18:00-20:00", 164, 0.409],
];

const channels = [
  ["Online TA", 126, 0.436],
  ["Groups", 39, 0.611],
  ["Direct", 44, 0.189],
  ["Offline TA/TO", 35, 0.315],
];

const countries = [
  ["PRT", "葡萄牙", 86, 0.566],
  ["ESP", "西班牙", 38, 0.254],
  ["FRA", "法国", 31, 0.185],
  ["DEU", "德国", 22, 0.167],
];

const recent = [
  { booking_id: 80242, hotel_name: "城市酒店", country_name: "葡萄牙", cancel_probability: 0.82, risk_level_name: "高风险" },
  { booking_id: 80243, hotel_name: "度假酒店", country_name: "西班牙", cancel_probability: 0.61, risk_level_name: "中风险" },
  { booking_id: 80244, hotel_name: "城市酒店", country_name: "法国", cancel_probability: 0.48, risk_level_name: "中风险" },
];

const formatPercent = (value) => `${(value * 100).toFixed(1)}%`;

function renderSummary() {
  const cards = [
    ["当前总预订量", summary.total_bookings.toLocaleString(), "历史基线 + 已处理订单"],
    ["历史取消率", formatPercent(summary.cancel_rate), `${summary.canceled_bookings.toLocaleString()} 条已取消`],
    ["平均每日房价", summary.avg_adr.toFixed(2), "字段：avg_adr"],
    ["当前高风险订单", summary.high_risk_count, "点击查看明细 >"],
  ];
  document.querySelector("#dashboard-summary").innerHTML = cards.map(([name, value, note]) => `
    <article class="metric-card"><small>${name}</small><strong>${value}</strong><em>${note}</em></article>
  `).join("");
  document.querySelector("#latest-event-time").textContent = summary.latest_event_time;
}

function renderTrend() {
  const max = Math.max(...trend.map(([, count]) => count));
  const chart = document.querySelector("#dashboard-trend");
  chart.style.setProperty("--bars", trend.length);
  chart.innerHTML = trend.map(([period, count, rate], index) => `
    <button class="bar-slot" data-period="${period}" title="跳转查询 ${period}">
      <span class="bar ${index % 2 ? "green" : ""} ${index === 2 ? "is-selected" : ""}" style="height:${Math.max(20, count / max * 100)}%">
        <i class="bar-dot" style="top:${Math.max(-12, 95 - rate * 145)}%"></i>
      </span>
      <span class="bar-label">${period}</span>
    </button>
  `).join("");
  chart.querySelectorAll(".bar-slot").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.href = `/bookings?event_date=2017-01-14&period=${encodeURIComponent(button.dataset.period)}`;
    });
  });
}

function renderRanks(selector, rows) {
  const max = Math.max(...rows.map((row) => row[2]));
  document.querySelector(selector).innerHTML = rows.map(([codeOrName, labelOrCount, countOrRate, maybeRate]) => {
    const isCountry = maybeRate !== undefined;
    const label = isCountry ? labelOrCount : codeOrName;
    const count = isCountry ? countOrRate : labelOrCount;
    const rate = isCountry ? maybeRate : countOrRate;
    const query = isCountry ? `country_code=${codeOrName}` : `market_segment=${encodeURIComponent(label)}`;
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
  document.querySelector("#recent-predictions").innerHTML = recent.map((item) => `
    <tr>
      <td><a href="/prediction?booking_id=${item.booking_id}">#${item.booking_id}</a></td>
      <td>${item.country_name}</td>
      <td>${formatPercent(item.cancel_probability)}</td>
      <td><span class="risk-pill ${item.cancel_probability > .7 ? "" : "medium"}">${item.risk_level_name}</span></td>
    </tr>
  `).join("");
}

renderSummary();
renderTrend();
renderRanks("#channel-risk", channels);
renderRanks("#country-risk", countries);
renderRecent();

document.querySelector("#toggle-simulation")?.addEventListener("click", (event) => {
  const status = document.querySelector("#simulation-status");
  const running = status.textContent === "运行中";
  status.textContent = running ? "已暂停" : "运行中";
  event.currentTarget.textContent = running ? "启动模拟" : "停止模拟";
});
