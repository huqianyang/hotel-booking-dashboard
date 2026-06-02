let selectedId = null;
let candidateRows = [];
const p = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;

async function apiGet(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) throw new Error(payload.message || "请求失败");
  return payload.data;
}

async function apiPost(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok || payload.success === false) throw new Error(payload.message || "请求失败");
  return payload.data;
}

async function loadCandidates() {
  const keyword = document.querySelector("#candidate-keyword").value;
  const data = await apiGet(`/api/prediction/candidate-bookings?page=1&page_size=10&keyword=${encodeURIComponent(keyword)}`);
  candidateRows = data.items || [];
  if (!selectedId && candidateRows[0]) selectedId = candidateRows[0].booking_id;
  renderCandidates();
  if (selectedId) await renderSingle();
}

function renderCandidates() {
  document.querySelector("#candidate-table").innerHTML = candidateRows.length ? candidateRows.map((row) => `
    <tr>
      <td><button type="button" data-id="${row.booking_id}">${row.booking_id === selectedId ? "已选" : "选择"}</button></td>
      <td>${row.booking_id}</td><td>${row.hotel_name || "-"}</td><td>${row.country_name || "-"}</td>
      <td>${row.lead_time}</td><td>${Number(row.adr || 0).toFixed(1)}</td><td>${row.customer_type_name || "-"}</td>
    </tr>
  `).join("") : "<tr><td colspan='7'>暂无候选订单</td></tr>";
  document.querySelectorAll("#candidate-table button").forEach((button) => button.addEventListener("click", async () => {
    selectedId = Number(button.dataset.id);
    renderCandidates();
    await renderSingle();
  }));
}

async function renderSingle() {
  const row = candidateRows.find((item) => item.booking_id === selectedId) || candidateRows[0];
  if (!row) return;
  const prediction = await apiPost("/api/prediction/single", { booking_id: row.booking_id });
  document.querySelector("#single-result").innerHTML = `
    <div class="panel-head"><h3>订单风险预测</h3><span>${prediction.model_version}</span></div>
    <div class="detail-list">
      <div class="detail-item"><span>booking_id</span><strong>${row.booking_id}</strong></div>
      <div class="detail-item"><span>hotel_name</span><strong>${row.hotel_name || "-"}</strong></div>
      <div class="detail-item"><span>country_name</span><strong>${row.country_name || "-"}</strong></div>
      <div class="detail-item"><span>lead_time</span><strong>${row.lead_time} 天</strong></div>
    </div>
    <div class="result-box"><span>cancel_probability</span><strong>${p(prediction.cancel_probability)}</strong><span>${prediction.risk_level_name}：${prediction.predicted_label_name}</span></div>
  `;
  document.querySelector("#reason-tags").innerHTML = `
    <div class="panel-head"><h3>风险原因解释</h3><span>reason_tags</span></div>
    <div class="reason-list">${(prediction.reason_tags || []).map((tag, index) => `<div class="reason-card"><b>${index + 1}</b><strong>${tag}</strong><span>影响较高</span></div>`).join("")}</div>
    <div class="log-line">预测时间：${prediction.predicted_at}</div>
  `;
}

async function renderMetrics() {
  const metrics = await apiGet("/api/prediction/model-metrics");
  document.querySelector("#current-model").textContent = metrics.selected_model.model_name;
  const metricLabels = [["准确率", "accuracy"], ["精确率", "precision_score"], ["召回率", "recall_score"], ["F1 值", "f1_score"]];
  document.querySelector("#model-metrics").innerHTML = metricLabels.map(([label, key]) => `
    <article class="metric-card"><small>${label}</small><strong>${p(metrics.metrics[key])}</strong><em>${key}</em></article>
  `).join("");
  const comparison = metrics.model_comparison || [];
  document.querySelector("#model-comparison").innerHTML = comparison.length ? comparison.map((row) => `
    <tr><td>${row.model_name}</td><td>${p(row.accuracy)}</td><td>${p(row.precision_score)}</td><td>${p(row.recall_score)}</td><td>${p(row.f1_score)}</td></tr>
  `).join("") : "<tr><td colspan='5'>暂无模型对比数据</td></tr>";
  const m = metrics.confusion_matrix;
  document.querySelector("#confusion-matrix").innerHTML = `
    <div class="panel-head"><h3>混淆矩阵</h3><span>confusion_matrix</span></div>
    <div class="matrix"><div class="head"></div><div class="head">预测未取消</div><div class="head">预测取消</div><div class="head">实际未取消</div><div class="good">预测正确<br>${m.true_negative}</div><div class="bad">误报<br>${m.false_positive}</div><div class="head">实际取消</div><div class="bad">漏报<br>${m.false_negative}</div><div class="good">预测正确<br>${m.true_positive}</div></div>
  `;
}

async function renderBatches() {
  const data = await apiGet("/api/prediction/batch-records?page=1&page_size=10");
  const rows = data.items || [];
  document.querySelector("#batch-records").innerHTML = rows.length ? rows.map((row) => `
    <tr><td>${row.batch_id}</td><td>${row.business_date}</td><td>${row.time_window}</td><td>${row.total_count}</td><td>${row.high_risk_count}</td><td>${p(row.avg_cancel_probability)}</td><td>${row.source}</td></tr>
  `).join("") : "<tr><td colspan='7'>暂无批量预测记录</td></tr>";
}

document.querySelectorAll("#prediction-tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("#prediction-tabs button").forEach((item) => item.classList.toggle("is-active", item === button));
    document.querySelectorAll(".tab-page").forEach((page) => page.classList.toggle("is-active", page.id === `tab-${button.dataset.tab}`));
  });
});
document.querySelector("#candidate-keyword").addEventListener("input", () => loadCandidates().catch(console.error));

Promise.all([loadCandidates(), renderMetrics(), renderBatches()]).catch((error) => {
  document.querySelector("#single-result").innerHTML = `<div class="log-line">${error.message}</div>`;
});
