let state = { page: 1, pageSize: 20, filters: {}, totalPages: 1, rows: [], realtimeTotal: null };
const pct = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;

async function apiGet(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.message || `请求失败：${url}`);
  }
  return payload.data;
}

function fillSelect(selector, rows) {
  const select = document.querySelector(selector);
  const first = select.querySelector("option");
  select.innerHTML = "";
  select.appendChild(first);
  rows.forEach((row) => {
    const option = document.createElement("option");
    option.value = row.value;
    option.textContent = row.label;
    select.appendChild(option);
  });
}

async function loadFilterOptions() {
  const options = await apiGet("/api/bookings/filter-options");
  fillSelect('select[name="hotel"]', options.hotels || []);
  fillSelect('select[name="country_code"]', options.countries || []);
  fillSelect('select[name="market_segment"]', options.market_segments || []);
  fillSelect('select[name="customer_type"]', options.customer_types || []);
  fillSelect('select[name="is_canceled"]', options.cancel_statuses || []);
}

async function loadRealtimeTotal() {
  const summary = await apiGet("/api/dashboard/summary");
  state.realtimeTotal = Number(summary.total_bookings || 0);
}

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

function collectFilters() {
  const form = document.querySelector("#booking-filters");
  const data = new FormData(form);
  state.filters = Object.fromEntries([...data].filter(([, value]) => value !== ""));
}

function queryString() {
  const params = new URLSearchParams(state.filters);
  params.set("page", state.page);
  params.set("page_size", state.pageSize);
  return params.toString();
}

function displayTotal(result) {
  return Object.keys(state.filters).length ? result.pagination.total : (state.realtimeTotal ?? result.pagination.total);
}

function renderStats(result) {
  const rows = result.items || [];
  const canceled = rows.filter((row) => Number(row.is_canceled) === 1).length;
  const avgAdr = rows.reduce((sum, row) => sum + Number(row.adr || 0), 0) / Math.max(rows.length, 1);
  document.querySelector("#booking-stats").innerHTML = [
    ["当前页结果数", rows.length, "当前分页内"],
    ["当前页取消率", pct(canceled / Math.max(rows.length, 1)), "基于当前页 is_canceled"],
    ["当前页平均 ADR", avgAdr.toFixed(1), "平均每日房价"],
    ["总匹配记录", displayTotal(result).toLocaleString(), Object.keys(state.filters).length ? "筛选结果" : "80008 + 实时处理量"],
  ].map(([name, value, note]) => `<article class="metric-card"><small>${name}</small><strong>${value}</strong><em>${note}</em></article>`).join("");
}

function renderTable(result) {
  const rows = result.items || [];
  state.rows = rows;
  state.totalPages = result.pagination.total_pages || 1;
  renderStats(result);
  document.querySelector("#booking-count").textContent = `${displayTotal(result).toLocaleString()} 条记录`;
  document.querySelector("#booking-table").innerHTML = rows.length ? rows.map((row) => `
    <tr>
      <td>${row.booking_id}</td><td>${row.hotel_name}</td><td>${row.country_name}</td><td>${row.market_segment_name}</td>
      <td>${row.customer_type_name}</td><td>${row.lead_time}</td><td>${Number(row.adr || 0).toFixed(1)}</td><td>${row.is_canceled_label}</td>
      <td><button data-id="${row.booking_id}" class="detail-link" type="button">详情</button></td>
    </tr>
  `).join("") : `<tr><td colspan="9">暂无记录</td></tr>`;
  document.querySelector("#page-copy").textContent = `第 ${state.page} 页 / 共 ${state.totalPages} 页`;
  document.querySelector("#prev-page").disabled = state.page <= 1;
  document.querySelector("#next-page").disabled = state.page >= state.totalPages;
  document.querySelectorAll(".detail-link").forEach((button) => button.addEventListener("click", () => selectBooking(Number(button.dataset.id))));
  selectBooking(rows[0]?.booking_id);
}

async function loadTable() {
  collectFilters();
  await loadRealtimeTotal();
  const result = await apiGet(`/api/bookings?${queryString()}`);
  renderTable(result);
}

async function selectBooking(bookingId) {
  if (!bookingId) {
    document.querySelector("#booking-detail").innerHTML = "<p>暂无记录</p>";
    document.querySelector("#operation-log").innerHTML = "";
    return;
  }
  const row = await apiGet(`/api/bookings/${bookingId}`);
  const fields = [
    ["订单编号", "booking_id"],
    ["酒店类型", "hotel_name"],
    ["到店日期", "arrival_date"],
    ["国家/地区", "country_name"],
    ["市场渠道", "market_segment_name"],
    ["客户类型", "customer_type_name"],
    ["餐食类型", "meal_name"],
    ["押金类型", "deposit_type_name"],
    ["历史取消次数", "previous_cancellations"],
    ["特殊需求数", "total_of_special_requests"],
  ];
  document.querySelector("#booking-detail").innerHTML = fields.map(([label, key]) => `
    <div class="detail-item"><span>${label}</span><strong>${row[key] ?? "-"}</strong></div>
  `).join("");
  document.querySelector("#operation-log").innerHTML = "";
}

document.querySelector("#booking-filters").addEventListener("submit", (event) => {
  event.preventDefault();
  state.page = 1;
  loadTable().catch(showError);
});
document.querySelector("#booking-filters").addEventListener("reset", () => setTimeout(() => { state.page = 1; loadTable().catch(showError); }, 0));
document.querySelector("#prev-page").addEventListener("click", () => { if (state.page > 1) { state.page -= 1; loadTable().catch(showError); } });
document.querySelector("#next-page").addEventListener("click", () => { if (state.page < state.totalPages) { state.page += 1; loadTable().catch(showError); } });
document.querySelector("#clear-linkage").addEventListener("click", () => {
  history.replaceState(null, "", "/bookings");
  document.querySelector("#booking-filters").reset();
  document.querySelector("#linkage-copy").textContent = "当前查看全部订单，可通过筛选条件缩小范围。";
  state.page = 1;
  loadTable().catch(showError);
});
document.querySelector("#export-bookings").addEventListener("click", () => {
  if (!state.rows.length) return;
  const headers = Object.keys(state.rows[0]);
  const csv = [headers.join(","), ...state.rows.map((row) => headers.map((key) => JSON.stringify(row[key] ?? "")).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "bookings-current-page.csv";
  link.click();
  URL.revokeObjectURL(link.href);
});

function showError(error) {
  document.querySelector("#operation-log").innerHTML = `<div class="log-line">加载失败：${error.message}</div>`;
}

loadFilterOptions()
  .then(() => {
    applyQueryParams();
    return loadTable();
  })
  .catch(showError);
