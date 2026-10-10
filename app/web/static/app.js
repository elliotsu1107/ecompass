const app = document.getElementById('dashboard-app');
const monthInput = document.getElementById('month');
const startInput = document.getElementById('start');
const endInput = document.getElementById('end');
const granularity = document.getElementById('granularity');
const storeFilter = document.getElementById('store-filter');
const refreshButton = document.getElementById('refresh');

const PALETTE = ['#1f6bff', '#21c3f3', '#ffc60a', '#7c3aed', '#34c724'];
const charts = [];
let storeOptionsLoaded = false;

const now = new Date();
const monthText = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
const dateText = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

monthInput.value = monthText;
startInput.value = `${monthText}-01`;
endInput.value = dateText(new Date(now.getFullYear(), now.getMonth() + 1, 0));

const fmt = (value) => value == null ? '—' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
const money = (value) => `¥${fmt(value)}`;
const percent = (value) => value == null ? '—' : `${(value * 100).toFixed(2)}%`;

function syncGranularity() {
  const monthly = granularity.value === 'month';
  document.getElementById('day-range').hidden = monthly;
  monthInput.hidden = !monthly;
  monthInput.previousElementSibling.hidden = !monthly;
}

function range() {
  if (granularity.value === 'month') {
    const month = monthInput.value || monthText;
    return [`${month}-01`, dateText(new Date(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0))];
  }
  return [startInput.value, endInput.value];
}

function disposeCharts() {
  charts.forEach((chart) => chart.dispose());
  charts.length = 0;
}

function createChart(element) {
  if (typeof echarts === 'undefined' || !element) return null;
  const chart = echarts.init(element);
  charts.push(chart);
  return chart;
}

function ringOption(rate, color, hasTarget) {
  const done = Math.max(0, Math.min(Number(rate) || 0, 1)) * 100;
  const label = hasTarget ? `${done.toFixed(0)}%` : '—';
  return {
    series: [{
      type: 'pie',
      radius: ['70%', '94%'],
      silent: true,
      labelLine: { show: false },
      data: [
        {
          value: hasTarget ? done : 0,
          name: '完成',
          itemStyle: { color },
          label: { show: true, position: 'center', formatter: label, fontSize: 18, fontWeight: 700, color: '#1f2329' },
        },
        { value: hasTarget ? 100 - done : 100, name: '剩余', itemStyle: { color: '#eef1f5' }, label: { show: false } },
      ],
    }],
    animation: false,
  };
}

function trendOption(stores) {
  const periods = [...new Set(stores.flatMap((store) => (store.timeline || []).map((item) => item.period)))].sort();
  return {
    tooltip: { trigger: 'axis', valueFormatter: (value) => `¥${fmt(value)}`, textStyle: { fontSize: 12 } },
    legend: { bottom: 0, itemHeight: 8, itemWidth: 14, textStyle: { color: '#646a73', fontSize: 12 } },
    grid: { left: 8, right: 18, top: 18, bottom: 44, containLabel: true },
    xAxis: {
      type: 'category',
      data: periods,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e5eaf0' } },
      axisTick: { show: false },
      axisLabel: { color: '#646a73', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0f2f5' } },
      axisLabel: {
        color: '#646a73',
        fontSize: 12,
        formatter: (value) => (Math.abs(value) >= 10000 ? `${(value / 10000).toFixed(1)}万` : value),
      },
    },
    series: stores.map((store, index) => ({
      name: store.store_name || `店铺 ${store.store_id}`,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2 },
      itemStyle: { color: PALETTE[index % PALETTE.length] },
      data: periods.map((period) => {
        const hit = (store.timeline || []).find((item) => item.period === period);
        return hit ? Number(Number(hit.settlement_amount).toFixed(2)) : 0;
      }),
    })),
  };
}

function okrOption(rows, nameOf) {
  const sorted = [...rows].sort((a, b) => a.settlement_amount - b.settlement_amount);
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (value) => `¥${fmt(value)}`, textStyle: { fontSize: 12 } },
    legend: { bottom: 0, itemHeight: 8, itemWidth: 14, textStyle: { color: '#646a73', fontSize: 12 } },
    grid: { left: 8, right: 24, top: 12, bottom: 44, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0f2f5' } },
      axisLabel: {
        color: '#646a73',
        fontSize: 12,
        formatter: (value) => (Math.abs(value) >= 10000 ? `${(value / 10000).toFixed(1)}万` : value),
      },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((row) => nameOf(row.operator_id)),
      axisLine: { lineStyle: { color: '#e5eaf0' } },
      axisTick: { show: false },
      axisLabel: { color: '#1f2329', fontSize: 12 },
    },
    series: [
      {
        name: '结算销售额',
        type: 'bar',
        barMaxWidth: 14,
        itemStyle: { color: '#1f6bff', borderRadius: [0, 4, 4, 0] },
        data: sorted.map((row) => Number(Number(row.settlement_amount).toFixed(2))),
      },
      {
        name: '目标',
        type: 'bar',
        barMaxWidth: 14,
        itemStyle: { color: '#dbe4f5', borderRadius: [0, 4, 4, 0] },
        data: sorted.map((row) => Number(Number(row.target_amount || 0).toFixed(2))),
      },
    ],
  };
}

function storeTrendOption(store) {
  const rows = store.timeline || [];
  const color = PALETTE[(Number(store.store_id) || 0) % PALETTE.length];
  const showLabel = rows.length > 0 && rows.length <= 16;
  return {
    tooltip: { trigger: 'axis', valueFormatter: (value) => `¥${fmt(value)}`, textStyle: { fontSize: 12 } },
    grid: { left: 8, right: 18, top: showLabel ? 26 : 18, bottom: 28, containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map((item) => item.period),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e5eaf0' } },
      axisTick: { show: false },
      axisLabel: { color: '#646a73', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0f2f5' } },
      axisLabel: {
        color: '#646a73',
        fontSize: 12,
        formatter: (value) => (Math.abs(value) >= 10000 ? `${(value / 10000).toFixed(1)}万` : value),
      },
    },
    series: [{
      name: '结算销售额',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2.5, color },
      itemStyle: { color },
      label: { show: showLabel, position: 'top', color: '#1f2329', fontSize: 11, formatter: (p) => fmt(p.value) },
      areaStyle: { color, opacity: 0.05 },
      data: rows.map((item) => Number(Number(item.settlement_amount).toFixed(2))),
    }],
    animation: false,
  };
}

function categoryOption(group, categoryNames, color) {
  const rows = group.rows || [];
  const axisColor = '#646a73';
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, textStyle: { fontSize: 12 } },
    legend: { bottom: 0, itemHeight: 8, itemWidth: 14, textStyle: { color: axisColor, fontSize: 12 } },
    grid: { left: 8, right: 8, top: 24, bottom: 44, containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map((row) => categoryNames.get(String(row.category_id)) || `类目 ${row.category_id}`),
      axisLine: { lineStyle: { color: '#e5eaf0' } },
      axisTick: { show: false },
      axisLabel: { color: '#1f2329', fontSize: 12, interval: 0, rotate: rows.length > 6 ? 24 : 0 },
    },
    yAxis: [
      {
        type: 'value',
        splitLine: { lineStyle: { color: '#f0f2f5' } },
        axisLabel: {
          color: axisColor,
          fontSize: 12,
          formatter: (value) => (Math.abs(value) >= 10000 ? `${(value / 10000).toFixed(1)}万` : value),
        },
      },
      {
        type: 'value',
        splitLine: { show: false },
        axisLabel: { color: axisColor, fontSize: 12, formatter: (value) => `${value}%` },
      },
    ],
    series: [
      {
        name: '结算销售额',
        type: 'bar',
        barMaxWidth: 26,
        itemStyle: { color, borderRadius: [4, 4, 0, 0] },
        label: { show: rows.length <= 12, position: 'top', color: '#1f2329', fontSize: 11, formatter: (p) => fmt(p.value) },
        data: rows.map((row) => Number(Number(row.settlement_amount).toFixed(2))),
      },
      {
        name: '推广费比',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: '#21c3f3' },
        itemStyle: { color: '#21c3f3' },
        data: rows.map((row) => row.cost_ratio == null ? null : Number((row.cost_ratio * 100).toFixed(2))),
      },
    ],
    animation: false,
  };
}

function storeRow(store, index) {
  const summary = store.summary || {};
  const target = Number(summary.target_amount || 0);
  const color = PALETTE[index % PALETTE.length];
  const timeline = store.timeline || [];
  const trendBody = timeline.length
    ? `<div class="chart" data-store-trend="${index}"></div>`
    : '<p class="empty-note">所选区间暂无结算数据</p>';
  return `<div class="store-row">
    <article class="kpi-card">
      <h3><span class="kpi-dot" style="background:${color}"></span>${store.store_name || `店铺 ${store.store_id}`}</h3>
      <div class="kpi-body">
        <div>
          <div class="kpi-ring" data-ring="${index}"></div>
          <div class="ring-caption"><span>当前 <b>${money(summary.settlement_amount)}</b></span><span class="sep">|</span><span>目标 <b>${target ? money(target) : '—'}</b></span></div>
        </div>
        <div class="kpi-figures">
          <div class="kpi-line"><span>支付金额</span><b>${money(summary.pay_amount)}</b></div>
          <div class="kpi-line"><span>退款金额</span><b>${money(summary.refund_amount)}</b></div>
          <div class="kpi-line"><span>推广费比</span><b>${percent(summary.cost_ratio)}</b></div>
          <div class="kpi-line"><span>目标完成</span><b>${target ? percent(Number(summary.settlement_amount || 0) / target) : '未设置'}</b></div>
        </div>
      </div>
    </article>
    <article class="trend-card">
      <h3>${store.store_name || `店铺 ${store.store_id}`} 结算额趋势</h3>
      ${trendBody}
    </article>
  </div>`;
}

function categoryColumn(storeName, rows, categoryNames) {
  const body = rows.map((row) => `<tr>
    <td>${categoryNames.get(String(row.category_id)) || `类目 ${row.category_id}`}</td>
    <td class="num">${money(row.settlement_amount)}</td>
    <td class="num">${percent(row.cost_ratio)}</td>
    <td class="num">${money(row.target_amount)}</td>
  </tr>`).join('');
  return `<table class="data-table">
    <thead><tr><th>类目</th><th class="num">结算销售额</th><th class="num">推广费比</th><th class="num">目标</th></tr></thead>
    <tbody>${body || '<tr><td colspan="4" class="empty-note">暂无类目数据</td></tr>'}</tbody>
  </table>`;
}

function fillStoreOptions(options) {
  if (storeOptionsLoaded || !storeFilter) return;
  const current = storeFilter.value;
  options.forEach((store) => {
    const option = document.createElement('option');
    option.value = String(store.id);
    option.textContent = store.name;
    storeFilter.append(option);
  });
  storeFilter.value = current;
  storeOptionsLoaded = true;
}

function render(data, periodText, storeLabel) {
  const categoryNames = new Map((data.dimensions?.categories || []).map((item) => [String(item.id), item.name]));
  const operatorNames = new Map((data.dimensions?.operators || []).map((item) => [String(item.id), item.name]));
  const stores = data.stores || [];
  const categoryGroups = data.categories || [];
  const categoryBlocks = categoryGroups.map((group, index) => {
    const name = stores.find((store) => String(store.store_id) === String(group.store_id))?.store_name
      || `店铺 ${group.store_id}`;
    const rows = group.rows || [];
    const chartBody = rows.length
      ? `<div class="chart chart-sm" data-category-chart="${index}"></div>`
      : '';
    return `<div class="col-card">
      <div class="col-title"><span>${name} · 品类结算额及费比</span><span>合计 ${money(rows.reduce((sum, row) => sum + Number(row.settlement_amount || 0), 0))}</span></div>
      ${chartBody}
      ${categoryColumn(name, rows, categoryNames)}
    </div>`;
  }).join('');

  app.innerHTML = `<div class="panel">
      <div class="panel-head"><h2>店铺经营概览</h2><span class="panel-note">${periodText}</span></div>
      <div class="store-rows">${stores.map(storeRow).join('') || '<p class="empty-note">暂无店铺数据，请先在后台建立店铺并导入报表。</p>'}</div>
    </div>
    <div class="panel">
      <div class="panel-head"><h2>结算趋势</h2><span class="panel-note">按${granularity.value === 'month' ? '月' : '日'}统计</span></div>
      <div class="chart" id="trend-chart"></div>
    </div>
    <div class="panel">
      <div class="panel-head"><h2>类目明细</h2><span class="panel-note">按店铺并列对比</span></div>
      <details class="fold" open>
        <summary>展开 / 收起类目明细</summary>
        <div class="fold-body"><div class="two-col">${categoryBlocks || '<p class="empty-note">暂无类目数据</p>'}</div></div>
      </details>
    </div>
    <div class="panel">
      <div class="panel-head"><h2>运营 OKR</h2><span class="panel-note">${storeLabel}</span></div>
      <div class="chart" id="okr-chart"></div>
    </div>`;

  disposeCharts();
  app.querySelectorAll('[data-ring]').forEach((element) => {
    const store = stores[Number(element.dataset.ring)];
    if (!store) return;
    const summary = store.summary || {};
    const target = Number(summary.target_amount || 0);
    const rate = target ? Number(summary.settlement_amount || 0) / target : 0;
    const chart = createChart(element);
    if (chart) chart.setOption(ringOption(rate, PALETTE[Number(element.dataset.ring) % PALETTE.length], target > 0));
  });
  app.querySelectorAll('[data-store-trend]').forEach((element) => {
    const store = stores[Number(element.dataset.storeTrend)];
    const chart = createChart(element);
    if (store && chart) chart.setOption(storeTrendOption(store));
  });
  app.querySelectorAll('[data-category-chart]').forEach((element) => {
    const group = categoryGroups[Number(element.dataset.categoryChart)];
    const chart = createChart(element);
    if (group && chart) chart.setOption(categoryOption(group, categoryNames, PALETTE[Number(element.dataset.categoryChart) % PALETTE.length]));
  });
  const trendChart = createChart(document.getElementById('trend-chart'));
  if (trendChart) trendChart.setOption(trendOption(stores));
  const okrChart = createChart(document.getElementById('okr-chart'));
  if (okrChart) okrChart.setOption(okrOption(data.operators || [], (id) => operatorNames.get(String(id)) || `运营 ${id}`));
}

async function load() {
  const [start, end] = range();
  if (!start || !end || start > end) {
    app.innerHTML = '<p class="status">请选择有效的开始和结束日期。</p>';
    return;
  }
  const query = new URLSearchParams({ start, end, granularity: granularity.value });
  if (storeFilter && storeFilter.value) query.set('store_id', storeFilter.value);
  app.innerHTML = '<p class="muted">正在加载数据…</p>';
  try {
    const response = await fetch(`/api/dashboard?${query}`);
    if (!response.ok) throw new Error(`加载失败（${response.status}）`);
    const data = await response.json();
    fillStoreOptions(data.store_options || []);
    const storeLabel = storeFilter && storeFilter.value
      ? ((data.store_options || []).find((item) => String(item.id) === storeFilter.value)?.name || '所选店铺')
      : '全部店铺合计';
    render(data, `${start} ~ ${end}`, storeLabel);
  } catch (error) {
    app.innerHTML = `<p class="status">数据加载失败：${error.message}</p>`;
  }
}

granularity.addEventListener('change', () => { syncGranularity(); load(); });
monthInput.addEventListener('change', load);
startInput.addEventListener('change', load);
endInput.addEventListener('change', load);
storeFilter.addEventListener('change', load);
refreshButton.addEventListener('click', load);
window.addEventListener('resize', () => charts.forEach((chart) => chart.resize()));

syncGranularity();
load();
