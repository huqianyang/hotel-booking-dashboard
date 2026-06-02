async function renderPyeChart(selector, url, options = {}) {
  const element = document.querySelector(selector);
  if (!element || !window.echarts) return null;
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.message || `chart request failed: ${url}`);
  }
  const chartData = payload.data || {};
  const chartOptions = chartData.options ? JSON.parse(chartData.options) : {};
  const chart = echarts.getInstanceByDom(element) || echarts.init(element);
  chart.clear();
  chart.setOption(chartOptions, true);
  if (chartData.status === "waiting" && chartData.message) {
    element.dataset.emptyMessage = chartData.message;
  } else {
    delete element.dataset.emptyMessage;
  }
  if (options.onClick) {
    chart.off("click");
    chart.on("click", options.onClick);
  }
  window.addEventListener("resize", () => chart.resize(), { once: true });
  return { chart, data: chartData };
}
