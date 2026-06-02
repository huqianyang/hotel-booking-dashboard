const state = { page: 1, pageSize: 20, totalPages: 1, lastItems: [] };
const pct = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;

async function apiGet(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) throw new Error(payload.message || "请求失败");
  return payload.data;
}

function formParams() {
  const form = document.querySelector("#booking-filters");
  const params = new URLSearchParams();
  new FormData(form).forEach((value, key) => {
    if (value) params.set(key, value);
  });
  params.set("page", state.page);
  params.set("page_size", state.pageSize);
  return params;
}

function fillSelect(selector, options) {
  const select = document.querySelector(selector);
  const first = select.querySelector("option");
  select.innerHTML = "";
  select.appendChild(first);
  (options || []).forEach((option) => {
    const node = document.createElement("option");
    node.value = option.value;
    node.textContent = option.label;
    select.appendChild(node);
  });
}

function applyQueryParams() {
  const params = new URLSearchParams(window.location.search);
  const form = document.querySelector("#booking-filters");
  params.forEach((value, key) => {
    if (form.elements[key]) form.elements[key].value = value;
  });
  document.querySelector("#linkage-copy").textContent = [...params].length
    ? `已接收联动条件：${[...params].map(([key, value]) => `${key}=${value}`).join("，")}`
    : "当前查看全部订单，可通过筛选条件缩小范围。";
}

function renderStats(data) {
  const items = data.items || [];
  const canceled = items.filter((row) => Number(row.is_canceled) === 1).length;
  const avgAdr = items.reduce((sum, row) => sum + Number(row.adr || 0), 0) / Math.max(items.length, 1);
  document.querySelector("#booking-stats").innerHTML = [
    ["当前页记录", items.length, "当前分页内"],
    ["当前页取消率", pct(canceled / Math.max(items.length, 1)), "is_canceled"],
    ["当前页平均 ADR", avgAdr.toFixed(1), "平均每日房价"],
    ["总匹配记录", data.pagination.total, "筛选后的总数"],
  ].map(([name, value, note]) => `<article class="metric-card"><small>${name}</small><strong>${value}</strong><em>${note}</em></article>`).join("");
}

function renderTable(data) {
  state.lastItems = data.items || [];
  state.totalPages = data.pagination.total_pages || 1;
  renderStats(data);
  document.querySelector("#booking-count").textContent = `${data.pagination.total} 条记录`;
  document.querySelector("#booking-table").innerHTML = state.lastItems.length ? state.lastItems.map((row) => `
    <tr>
      <td>${row.booking_id}</td><td>${row.hotel_name || row.hotel || "-"}</td><td>${row.country_name || row.country_code || "-"}</td>
      <td>${row.market_segment_name || row.market_segment || "-"}</td><td>${row.customer_type_name || row.customer_type || "-"}</td>
      <td>${row.lead_time ?? "-"}</td><td>${Number(row.adr || 0).toFixed(1)}</td><td>${row.is_canceled_label || row.is_canceled}</td>
      <td><button data-id="${row.booking_id}" class="detail-link" type="button">详情</button></td>
    </tr>
  `).join("") : "<tr><td colspan='9'>暂无匹配记录</td></tr>";
  document.querySelector("#page-copy").textContent = `第 ${data.pagination.page} 页 / 共 ${state.totalPages} 页`;
  document.querySelector("#prev-page").disabled = state.page <= 1;
  document.querySelector("#next-page").disabled = state.page >= state.totalPages;
  document.querySelectorAll(".detail-link").forEach((button) => button.addEventListener("click", () => selectBooking(button.dataset.id)));
  if (state.lastItems[0]) selectBooking(state.lastItems[0].booking_id);
}

async function selectBooking(bookingId) {
  if (!bookingId) {
    document.querySelector("#booking-detail").innerHTML = "<p>暂无记录</p>";
    return;
  }
  const row = await apiGet(`/api/bookings/${bookingId}`);
  document.querySelector("#detail-booking-id").textContent = `#${row.booking_id}`;
  const fields = ["booking_id", "hotel_name", "arrival_date", "country_name", "market_segment_name", "customer_type_name", "meal_name", "deposit_type_name", "previous_cancellations", "total_of_special_requests", "reservation_status_date"];
  document.querySelector("#booking-detail").innerHTML = fields.map((field) => `
    <div class="detail-item"><span>${field}</span><strong>${row[field] ?? "-"}</strong></div>
  `).join("");
  document.querySelector("#operation-log").innerHTML = `
    <div class="log-line">已读取订单详情：booking_id=${row.booking_id}</div>
    <div class="log-line">演示更新接口：PUT /api/bookings/${row.booking_id}</div>
    <div class="log-line">逻辑删除接口：DELETE /api/bookings/${row.booking_id}</div>
  `;
}

async function loadBookings() {
  const data = await apiGet(`/api/bookings?${formParams().toString()}`);
  renderTable(data);
}

function exportCurrentRows() {
  const rows = state.lastItems;
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const csv = [headers.join(","), ...rows.map((row) => headers.map((key) => JSON.stringify(row[key] ?? "")).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "bookings-current-page.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}

async function initBookings() {
  const options = await apiGet("/api/bookings/filter-options");
  fillSelect("#filter-hotel", options.hotels);
  fillSelect("#filter-country", options.countries);
  fillSelect("#filter-market", options.market_segments);
  fillSelect("#filter-customer", options.customer_types);
  fillSelect("#filter-cancel", options.cancel_statuses);
  applyQueryParams();
  await loadBookings();
}

document.querySelector("#booking-filters").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.page = 1;
  await loadBookings();
});
document.querySelector("#booking-filters").addEventListener("reset", () => setTimeout(async () => { state.page = 1; await loadBookings(); }, 0));
document.querySelector("#prev-page").addEventListener("click", async () => { if (state.page > 1) { state.page -= 1; await loadBookings(); } });
document.querySelector("#next-page").addEventListener("click", async () => { if (state.page < state.totalPages) { state.page += 1; await loadBookings(); } });
document.querySelector("#clear-linkage").addEventListener("click", async () => {
  history.replaceState(null, "", "/bookings");
  document.querySelector("#booking-filters").reset();
  applyQueryParams();
  state.page = 1;
  await loadBookings();
});
document.querySelector("#export-bookings").addEventListener("click", exportCurrentRows);

initBookings().catch((error) => {
  document.querySelector("#booking-table").innerHTML = `<tr><td colspan="9">${error.message}</td></tr>`;
});
