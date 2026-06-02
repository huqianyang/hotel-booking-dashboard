const bookings = [
  { booking_id: 80242, hotel: "City Hotel", hotel_name: "城市酒店", is_canceled: 1, is_canceled_label: "已取消", arrival_date: "2017-01-14", country_code: "PRT", country_name: "葡萄牙", market_segment: "Online TA", market_segment_name: "线上旅行社", customer_type: "Transient", customer_type_name: "散客", lead_time: 132, total_guests: 2, total_nights: 3, adr: 118.5, meal_name: "含早餐", deposit_type_name: "不可退款订金", previous_cancellations: 2, total_of_special_requests: 0 },
  { booking_id: 80243, hotel: "Resort Hotel", hotel_name: "度假酒店", is_canceled: 1, is_canceled_label: "已取消", arrival_date: "2017-01-14", country_code: "PRT", country_name: "葡萄牙", market_segment: "Groups", market_segment_name: "团队", customer_type: "Group", customer_type_name: "团队客户", lead_time: 96, total_guests: 3, total_nights: 5, adr: 91.2, meal_name: "半餐", deposit_type_name: "无订金", previous_cancellations: 1, total_of_special_requests: 1 },
  { booking_id: 80244, hotel: "City Hotel", hotel_name: "城市酒店", is_canceled: 0, is_canceled_label: "未取消", arrival_date: "2017-01-14", country_code: "FRA", country_name: "法国", market_segment: "Direct", market_segment_name: "直接预订", customer_type: "Transient", customer_type_name: "散客", lead_time: 38, total_guests: 2, total_nights: 2, adr: 104.0, meal_name: "含早餐", deposit_type_name: "无订金", previous_cancellations: 0, total_of_special_requests: 2 },
  { booking_id: 80245, hotel: "Resort Hotel", hotel_name: "度假酒店", is_canceled: 0, is_canceled_label: "未取消", arrival_date: "2017-01-15", country_code: "GBR", country_name: "英国", market_segment: "Online TA", market_segment_name: "线上旅行社", customer_type: "Contract", customer_type_name: "合约客户", lead_time: 64, total_guests: 2, total_nights: 4, adr: 126.8, meal_name: "不含餐", deposit_type_name: "可退订金", previous_cancellations: 0, total_of_special_requests: 3 },
];

let state = { page: 1, pageSize: 3, filters: {} };
const pct = (value) => `${(value * 100).toFixed(1)}%`;

function applyQueryParams() {
  const params = new URLSearchParams(window.location.search);
  const form = document.querySelector("#booking-filters");
  params.forEach((value, key) => {
    const field = form.elements[key];
    if (field) field.value = value;
  });
  if ([...params].length) {
    document.querySelector("#linkage-copy").textContent = `已接收联动条件：${[...params].map(([k, v]) => `${k}=${v}`).join("，")}`;
  }
}

function getFiltered() {
  const form = document.querySelector("#booking-filters");
  const data = new FormData(form);
  state.filters = Object.fromEntries([...data].filter(([, value]) => value !== ""));
  return bookings.filter((item) => {
    return Object.entries(state.filters).every(([key, value]) => {
      if (key === "keyword") {
        const haystack = `${item.booking_id} ${item.country_name} ${item.hotel_name}`;
        return haystack.toLowerCase().includes(value.toLowerCase());
      }
      if (key === "is_canceled") return String(item.is_canceled) === value;
      return String(item[key]) === value;
    });
  });
}

function renderStats(rows) {
  const canceled = rows.filter((row) => row.is_canceled === 1).length;
  const avgAdr = rows.reduce((sum, row) => sum + row.adr, 0) / Math.max(rows.length, 1);
  document.querySelector("#booking-stats").innerHTML = [
    ["当前结果数", rows.length, "符合筛选条件"],
    ["筛选取消率", pct(canceled / Math.max(rows.length, 1)), "基于 is_canceled"],
    ["平均 ADR", avgAdr.toFixed(1), "平均每日房价"],
    ["高提前期订单", rows.filter((row) => row.lead_time > 90).length, "lead_time > 90"],
  ].map(([name, value, note]) => `<article class="metric-card"><small>${name}</small><strong>${value}</strong><em>${note}</em></article>`).join("");
}

function renderTable() {
  const rows = getFiltered();
  renderStats(rows);
  const start = (state.page - 1) * state.pageSize;
  const pageRows = rows.slice(start, start + state.pageSize);
  document.querySelector("#booking-count").textContent = `${rows.length} 条记录`;
  document.querySelector("#booking-table").innerHTML = pageRows.map((row) => `
    <tr>
      <td>${row.booking_id}</td><td>${row.hotel_name}</td><td>${row.country_name}</td><td>${row.market_segment_name}</td>
      <td>${row.customer_type_name}</td><td>${row.lead_time}</td><td>${row.adr.toFixed(1)}</td><td>${row.is_canceled_label}</td>
      <td><button data-id="${row.booking_id}" class="detail-link" type="button">详情</button></td>
    </tr>
  `).join("");
  const totalPages = Math.max(Math.ceil(rows.length / state.pageSize), 1);
  document.querySelector("#page-copy").textContent = `第 ${state.page} 页 / 共 ${totalPages} 页`;
  document.querySelector("#prev-page").disabled = state.page <= 1;
  document.querySelector("#next-page").disabled = state.page >= totalPages;
  document.querySelectorAll(".detail-link").forEach((button) => button.addEventListener("click", () => selectBooking(Number(button.dataset.id))));
  selectBooking(pageRows[0]?.booking_id);
}

function selectBooking(bookingId) {
  const row = bookings.find((item) => item.booking_id === bookingId);
  if (!row) {
    document.querySelector("#booking-detail").innerHTML = "<p>暂无记录</p>";
    return;
  }
  const fields = ["booking_id", "hotel_name", "arrival_date", "country_name", "market_segment_name", "customer_type_name", "meal_name", "deposit_type_name", "previous_cancellations", "total_of_special_requests"];
  document.querySelector("#booking-detail").innerHTML = fields.map((field) => `
    <div class="detail-item"><span>${field}</span><strong>${row[field]}</strong></div>
  `).join("");
  document.querySelector("#operation-log").innerHTML = `
    <div class="log-line">查询 hotel_bookings：booking_id=${row.booking_id}</div>
    <div class="log-line">演示编辑字段：customer_type、market_segment、deposit_type、adr、total_of_special_requests</div>
    <div class="log-line">删除策略：只更新 is_deleted = 1，不物理删除</div>
  `;
}

document.querySelector("#booking-filters").addEventListener("submit", (event) => {
  event.preventDefault();
  state.page = 1;
  renderTable();
});
document.querySelector("#booking-filters").addEventListener("reset", () => setTimeout(() => { state.page = 1; renderTable(); }, 0));
document.querySelector("#prev-page").addEventListener("click", () => { state.page -= 1; renderTable(); });
document.querySelector("#next-page").addEventListener("click", () => { state.page += 1; renderTable(); });
document.querySelector("#clear-linkage").addEventListener("click", () => {
  history.replaceState(null, "", "/bookings");
  document.querySelector("#linkage-copy").textContent = "当前查看全部订单，可通过筛选条件缩小范围。";
});

applyQueryParams();
renderTable();
