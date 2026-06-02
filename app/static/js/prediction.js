const candidates = [
  { booking_id: 1001, hotel_name: "城市酒店", arrival_date: "2017-01-14", country_name: "葡萄牙", lead_time: 120, adr: 98.5, customer_type_name: "散客" },
  { booking_id: 1002, hotel_name: "度假酒店", arrival_date: "2017-01-15", country_name: "英国", lead_time: 88, adr: 115.2, customer_type_name: "团队客户" },
  { booking_id: 1003, hotel_name: "城市酒店", arrival_date: "2017-01-16", country_name: "法国", lead_time: 42, adr: 88.0, customer_type_name: "合约客户" },
];
const prediction = {
  booking_id: 1001, model_version: "random_forest_v1", cancel_probability: 0.7825, predicted_label: 1,
  predicted_label_name: "可能取消", risk_level: "high", risk_level_name: "高风险",
  reason_tags: ["提前预订时间较长", "无特殊需求", "历史取消次数较高"], predicted_at: "2026-06-01 20:30:00",
};
const metrics = {
  selected_model: { model_name: "随机森林", model_version: "random_forest_v1", reason: "测试集 F1 值和召回率表现更稳定。" },
  metrics: { accuracy: 0.8721, precision_score: 0.841, recall_score: 0.8032, f1_score: 0.8217, train_score: 0.9012, test_score: 0.8721 },
  model_comparison: [
    { model_name: "逻辑回归", accuracy: 0.812, precision_score: 0.78, recall_score: 0.742, f1_score: 0.7605 },
    { model_name: "随机森林", accuracy: 0.8721, precision_score: 0.841, recall_score: 0.8032, f1_score: 0.8217 },
  ],
  confusion_matrix: { true_negative: 13000, false_positive: 1200, false_negative: 1700, true_positive: 8000 },
};
const batches = [
  { batch_id: "20170114-1200-1400", business_date: "2017-01-14", time_window: "12:00-14:00", total_count: 420, high_risk_count: 72, avg_cancel_probability: 0.438, source: "realtime_simulation" },
  { batch_id: "20170114-1000-1200", business_date: "2017-01-14", time_window: "10:00-12:00", total_count: 288, high_risk_count: 44, avg_cancel_probability: 0.354, source: "realtime_simulation" },
];
const p = (value) => `${(value * 100).toFixed(1)}%`;
let selectedId = 1001;
function renderCandidates() {
  const keyword = document.querySelector("#candidate-keyword").value.toLowerCase();
  const rows = candidates.filter((row) => `${row.booking_id} ${row.country_name} ${row.hotel_name}`.toLowerCase().includes(keyword));
  document.querySelector("#candidate-table").innerHTML = rows.map((row) => `
    <tr><td><button type="button" data-id="${row.booking_id}">${row.booking_id === selectedId ? "●" : "○"}</button></td><td>${row.booking_id}</td><td>${row.hotel_name}</td><td>${row.country_name}</td><td>${row.lead_time}</td><td>${row.adr.toFixed(1)}</td><td>${row.customer_type_name}</td></tr>
  `).join("");
  document.querySelectorAll("#candidate-table button").forEach((button) => button.addEventListener("click", () => { selectedId = Number(button.dataset.id); renderSingle(); renderCandidates(); }));
}
function renderSingle() {
  const row = candidates.find((item) => item.booking_id === selectedId) || candidates[0];
  document.querySelector("#single-result").innerHTML = `
    <div class="panel-head"><h3>订单风险预测</h3><span>${prediction.model_version}</span></div>
    <div class="detail-list">
      <div class="detail-item"><span>booking_id</span><strong>${row.booking_id}</strong></div>
      <div class="detail-item"><span>hotel_name</span><strong>${row.hotel_name}</strong></div>
      <div class="detail-item"><span>country_name</span><strong>${row.country_name}</strong></div>
      <div class="detail-item"><span>lead_time</span><strong>${row.lead_time} 天</strong></div>
    </div>
    <div class="result-box"><span>cancel_probability</span><strong>${p(prediction.cancel_probability)}</strong><span>${prediction.risk_level_name}，${prediction.predicted_label_name}</span></div>
  `;
  document.querySelector("#reason-tags").innerHTML = `
    <div class="panel-head"><h3>风险原因解释</h3><span>reason_tags</span></div>
    <div class="reason-list">${prediction.reason_tags.map((tag, index) => `<div class="reason-card"><b>${index + 1}</b><strong>${tag}</strong><span>影响较高</span></div>`).join("")}</div>
    <div class="log-line">建议动作：入住前 3 天进行二次确认，并准备候补订单策略。</div>
  `;
}
function renderMetrics() {
  const metricLabels = [["准确率", "accuracy"], ["精确率", "precision_score"], ["召回率", "recall_score"], ["F1 值", "f1_score"]];
  document.querySelector("#model-metrics").innerHTML = metricLabels.map(([label, key]) => `
    <article class="metric-card"><small>${label}</small><strong>${p(metrics.metrics[key])}</strong><em>${key}</em></article>
  `).join("");
  document.querySelector("#model-comparison").innerHTML = metrics.model_comparison.map((row) => `
    <tr><td>${row.model_name}</td><td>${p(row.accuracy)}</td><td>${p(row.precision_score)}</td><td>${p(row.recall_score)}</td><td>${p(row.f1_score)}</td></tr>
  `).join("");
  const m = metrics.confusion_matrix;
  document.querySelector("#confusion-matrix").innerHTML = `
    <div class="panel-head"><h3>混淆矩阵</h3><span>confusion_matrix</span></div>
    <div class="matrix"><div class="head"></div><div class="head">预测未取消</div><div class="head">预测取消</div><div class="head">实际未取消</div><div class="good">预测正确<br>${m.true_negative}</div><div class="bad">误报<br>${m.false_positive}</div><div class="head">实际取消</div><div class="bad">漏报<br>${m.false_negative}</div><div class="good">预测正确<br>${m.true_positive}</div></div>
  `;
}
function renderBatches() {
  document.querySelector("#batch-records").innerHTML = batches.map((row) => `
    <tr><td>${row.batch_id}</td><td>${row.business_date}</td><td>${row.time_window}</td><td>${row.total_count}</td><td>${row.high_risk_count}</td><td>${p(row.avg_cancel_probability)}</td><td>${row.source}</td></tr>
  `).join("");
}
document.querySelectorAll("#prediction-tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("#prediction-tabs button").forEach((item) => item.classList.toggle("is-active", item === button));
    document.querySelectorAll(".tab-page").forEach((page) => page.classList.toggle("is-active", page.id === `tab-${button.dataset.tab}`));
  });
});
document.querySelector("#candidate-keyword").addEventListener("input", renderCandidates);
renderCandidates();
renderSingle();
renderMetrics();
renderBatches();
