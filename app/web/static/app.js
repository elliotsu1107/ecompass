const app = document.getElementById('dashboard-app');
const fmt = (value) => value == null ? '—' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
const now = new Date();
const monthText = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
const monthInput = document.getElementById('month');
const startInput = document.getElementById('start');
const endInput = document.getElementById('end');
const granularity = document.getElementById('granularity');
const dateText = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

monthInput.value = monthText;
startInput.value = `${monthText}-01`;
endInput.value = dateText(new Date(now.getFullYear(), now.getMonth() + 1, 0));

function syncGranularity() {
  const monthly = granularity.value === 'month';
  document.getElementById('day-range').hidden = monthly;
  monthInput.hidden = !monthly;
  monthInput.previousElementSibling.hidden = !monthly;
}

function percent(value) {
  return value == null ? '—' : `${(value * 100).toFixed(2)}%`;
}

function card(store) {
  const summary = store.summary || {};
  const label = store.store_name || `店铺 ${store.store_id}`;
  return `<article class="card"><h3>${label}</h3><div class="metrics"><div class="metric"><small>结算销售额</small><div class="value">¥${fmt(summary.settlement_amount)}</div></div><div class="metric"><small>推广费比</small><div class="value">${percent(summary.cost_ratio)}</div></div><div>支付 ¥${fmt(summary.pay_amount)}</div><div>退款 ¥${fmt(summary.refund_amount)}</div></div>${store.reconciliation?.alert ? '<p class="status">对账告警：店铺日报与商品日报存在差异</p>' : ''}</article>`;
}

async function load() {
  const monthly = granularity.value === 'month';
  const month = monthInput.value || monthText;
  const start = monthly ? `${month}-01` : startInput.value;
  const end = monthly
    ? dateText(new Date(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0))
    : endInput.value;
  if (!start || !end || start > end) {
    app.innerHTML = '<p class="status">请选择有效的开始和结束日期。</p>';
    return;
  }

  const query = new URLSearchParams({ start, end, granularity: granularity.value });
  app.innerHTML = '<p class="muted">正在加载数据…</p>';
  try {
    const response = await fetch(`/api/dashboard?${query}`);
    if (!response.ok) throw new Error(`加载失败（${response.status}）`);
    const data = await response.json();
    const categoryNames = new Map((data.dimensions?.categories || []).map((item) => [String(item.id), item.name]));
    const operatorNames = new Map((data.dimensions?.operators || []).map((item) => [String(item.id), item.name]));
    const storeNames = new Map(data.stores.map((item) => [String(item.store_id), item.store_name]));
    const categoryRows = data.categories.flatMap((item) => (item.rows || []).map((row) => `
      <tr><td>${storeNames.get(String(item.store_id)) || `店铺 ${item.store_id}`}</td>
      <td>${categoryNames.get(String(row.category_id)) || `类目 ${row.category_id}`}</td>
      <td>¥${fmt(row.settlement_amount)}</td><td>${percent(row.cost_ratio)}</td>
      <td>¥${fmt(row.target_amount)}</td></tr>`)).join('');
    const operatorCards = data.operators.map((operator) => {
      const label = operatorNames.get(String(operator.operator_id)) || `运营 ${operator.operator_id}`;
      const breakdown = (operator.stores || []).map((store) => {
        const name = storeNames.get(String(store.store_id)) || `店铺 ${store.store_id}`;
        return `${name} ${fmt(store.settlement_amount)}（${(store.share * 100).toFixed(1)}%）`;
      }).join(' / ');
      return `<article class="card"><h3>${label}</h3><div class="value">¥${fmt(operator.settlement_amount)}</div><p>推广费比：${percent(operator.cost_ratio)}</p><p>目标：¥${fmt(operator.target_amount)}</p><p class="muted">${breakdown}</p></article>`;
    }).join('');

    app.innerHTML = `<section class="section"><h2>店铺经营</h2><div class="grid">${data.stores.map(card).join('') || '<p class="muted">暂无店铺数据</p>'}</div></section>
      <section class="section"><h2>类目经营</h2><div class="table-wrap"><table><thead><tr><th>店铺</th><th>类目</th><th>结算销售额</th><th>推广费比</th><th>目标</th></tr></thead><tbody>${categoryRows || '<tr><td colspan="5" class="muted">暂无类目数据</td></tr>'}</tbody></table></div></section>
      <section class="section"><h2>运营 OKR</h2><div class="grid">${operatorCards || '<p class="muted">暂无运营数据</p>'}</div></section>`;
  } catch (error) {
    app.innerHTML = `<p class="status">数据加载失败：${error.message}</p>`;
  }
}

granularity.addEventListener('change', () => { syncGranularity(); load(); });
monthInput.addEventListener('change', load);
startInput.addEventListener('change', load);
endInput.addEventListener('change', load);
document.getElementById('refresh').addEventListener('click', load);
syncGranularity();
load();
