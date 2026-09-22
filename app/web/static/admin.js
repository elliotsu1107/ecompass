const state = { stores: [], operators: [], categories: [], products: [] };

const message = document.querySelector('#global-message');

function notify(text, kind = 'success') {
  if (!message) return;
  message.className = `message ${kind}`;
  message.textContent = text;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `请求失败（${response.status}）`);
  }
  return body;
}

function cell(text) {
  const td = document.createElement('td');
  td.textContent = text;
  return td;
}

function emptyNote(container, text) {
  container.textContent = '';
  const p = document.createElement('p');
  p.className = 'empty';
  p.textContent = text;
  container.append(p);
}

function renderTable(container, headers, rows) {
  if (!rows.length) {
    emptyNote(container, '暂无数据');
    return;
  }
  container.textContent = '';
  const table = document.createElement('table');
  const head = document.createElement('thead');
  const headRow = document.createElement('tr');
  headers.forEach((header) => {
    const th = document.createElement('th');
    th.textContent = header;
    headRow.append(th);
  });
  head.append(headRow);
  const body = document.createElement('tbody');
  rows.forEach((values) => {
    const tr = document.createElement('tr');
    values.forEach((value) => tr.append(cell(value)));
    body.append(tr);
  });
  table.append(head, body);
  container.append(table);
}

function fillSelect(select, items, toValue, toLabel, placeholder) {
  if (!select) return;
  const previous = select.value;
  select.textContent = '';
  if (placeholder) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = placeholder;
    select.append(option);
  }
  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = String(toValue(item));
    option.textContent = toLabel(item);
    select.append(option);
  });
  if (previous && [...select.options].some((option) => option.value === previous)) {
    select.value = previous;
  }
}

function operatorName(id) {
  const found = state.operators.find((item) => String(item.id) === String(id));
  return found ? found.name : `#${id}`;
}

function storeName(id) {
  const found = state.stores.find((item) => String(item.id) === String(id));
  return found ? found.name : `#${id}`;
}

function categoryName(id) {
  const found = state.categories.find((item) => String(item.id) === String(id));
  return found ? found.name : `#${id}`;
}

function actionButton(label, handler, kind = '') {
  const button = document.createElement('button');
  button.type = 'button'; button.textContent = label;
  if (kind) button.className = kind;
  button.addEventListener('click', handler); return button;
}

async function removeDimension(table, item) {
  if (!window.confirm(`确定删除${item.name}吗？`)) return;
  await api(`/api/admin/${table}/${item.id}`, { method: 'DELETE' });
  await loadDimensions(); await loadTargets(); notify('删除成功');
}

async function editDimension(table, item) {
  const name = window.prompt('名称', item.name); if (name === null) return;
  const values = { name: name.trim() }; if (!values.name) return notify('名称不能为空', 'error');
  if (table === 'stores') values.platform = window.prompt('平台', item.platform) || item.platform;
  if (table === 'categories') values.operator_id = Number(window.prompt('负责运营编号', item.operator_id) || item.operator_id);
  await api(`/api/admin/${table}/${item.id}`, { method: 'PUT', body: JSON.stringify(values) });
  await loadDimensions(); await loadTargets(); notify('修改成功');
}

function renderDimensionTable(container, headers, rows, table) {
  if (!rows.length) return emptyNote(container, '暂无数据');
  container.textContent = ''; const element = document.createElement('table');
  element.innerHTML = `<thead><tr>${[...headers, '操作'].map((h) => `<th>${h}</th>`).join('')}</tr></thead>`;
  const body = document.createElement('tbody');
  rows.forEach((item) => {
    const tr = document.createElement('tr');
    const values = table === 'operators' ? [item.name, item.id] : table === 'stores' ? [item.name, item.platform, item.id] : [item.name, operatorName(item.operator_id), item.id];
    values.forEach((value) => tr.append(cell(value)));
    const actions = document.createElement('td');
    actions.append(actionButton('编辑', () => editDimension(table, item)), actionButton('删除', () => removeDimension(table, item), 'danger'));
    tr.append(actions); body.append(tr);
  });
  element.append(body); container.append(element);
}

function renderDimensions() {
  renderDimensionTable(document.querySelector('#operator-list'), ['运营', '编号'], state.operators, 'operators');
  renderDimensionTable(document.querySelector('#store-list'), ['店铺', '平台', '编号'], state.stores, 'stores');
  renderDimensionTable(document.querySelector('#category-list'), ['类目', '负责运营', '编号'], state.categories, 'categories');
  renderProductTabs();

  fillSelect(document.querySelector('#category-operator'), state.operators, (item) => item.id, (item) => item.name, '请选择运营');
  fillSelect(document.querySelector('#product-operator'), state.operators, (item) => item.id, (item) => item.name, '请选择运营');
  fillSelect(document.querySelector('#product-store'), state.stores, (item) => item.id, (item) => item.name, '请选择店铺');
  fillSelect(document.querySelector('#product-category'), state.categories, (item) => item.id, (item) => `${item.name}（${operatorName(item.operator_id)}）`, '请选择类目');
}

function renderProductTabs() {
  const container = document.querySelector('#product-list');
  if (!container) return;
  container.textContent = '';
  if (!state.products.length) return emptyNote(container, '暂无数据');
  const tabs = document.createElement('div');
  tabs.className = 'product-store-tabs';
  const tableBox = document.createElement('div');
  const stores = state.stores.filter((store) => state.products.some((item) => String(item.store_id) === String(store.id)));
  const renderStore = (storeId) => {
    const rows = state.products.filter((item) => String(item.store_id) === String(storeId));
    tableBox.textContent = ''; if (!rows.length) return emptyNote(tableBox, '暂无数据');
    const table = document.createElement('table');
    table.innerHTML = '<thead><tr><th>商品 ID</th><th>商品名称</th><th>店铺</th><th>类目</th><th>运营</th><th>操作</th></tr></thead>';
    const body = document.createElement('tbody');
    rows.forEach((item) => {
      const tr = document.createElement('tr');
      [item.product_id, item.name, storeName(item.store_id), categoryName(item.category_id), operatorName(item.operator_id)].forEach((value) => tr.append(cell(value)));
      const actions = document.createElement('td');
      actions.append(actionButton('编辑', async () => { const name = window.prompt('商品名称', item.name); if (name === null) return; await api(`/api/admin/products/${item.store_id}/${encodeURIComponent(item.product_id)}`, { method: 'PUT', body: JSON.stringify({ name: name.trim(), category_id: item.category_id, operator_id: item.operator_id }) }); await loadDimensions(); notify('修改成功'); }), actionButton('删除', async () => { if (!window.confirm(`确定删除商品 ${item.product_id} 吗？`)) return; await api(`/api/admin/products/${item.store_id}/${encodeURIComponent(item.product_id)}`, { method: 'DELETE' }); await loadDimensions(); notify('删除成功'); }, 'danger'));
      tr.append(actions); body.append(tr);
    });
    table.append(body); tableBox.append(table);
    [...tabs.children].forEach((button) => button.classList.toggle('active', button.dataset.storeId === String(storeId)));
  };
  stores.forEach((store, index) => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'product-store-tab'; button.dataset.storeId = store.id; button.textContent = store.name;
    button.addEventListener('click', () => renderStore(store.id)); tabs.append(button);
    if (index === 0) renderStore(store.id);
  });
  container.append(tabs, tableBox);
}

async function loadDimensions() {
  const [operators, stores, categories, products] = await Promise.all([
    api('/api/admin/operators'),
    api('/api/admin/stores'),
    api('/api/admin/categories'),
    api('/api/admin/products'),
  ]);
  state.operators = operators.items;
  state.stores = stores.items;
  state.categories = categories.items;
  state.products = products.items;
  renderDimensions();
}

function monthValue() {
  const input = document.querySelector('#target-month');
  return input ? input.value : '';
}

function renderTargetGroup(container, title, rows, scope, month) {
  if (!container) return;
  container.textContent = '';
  const heading = document.createElement('p');
  heading.className = 'group-title';
  heading.textContent = title;
  container.append(heading);
  if (!rows.length) {
    const note = document.createElement('p');
    note.className = 'empty';
    note.textContent = '请先建立对应资料';
    container.append(note);
    return;
  }
  const table = document.createElement('table');
  const head = document.createElement('thead');
  const row = document.createElement('tr');
  ['名称', '月目标（元）', ''].forEach((label) => {
    const th = document.createElement('th');
    th.textContent = label;
    row.append(th);
  });
  head.append(row);
  const body = document.createElement('tbody');
  rows.forEach((item) => {
    const tr = document.createElement('tr');
    tr.append(cell(item.label));

    const inputCell = document.createElement('td');
    const input = document.createElement('input');
    input.type = 'number';
    input.min = '0';
    input.step = '0.01';
    input.value = item.amount ? String(item.amount) : '';
    input.placeholder = '0';
    input.setAttribute('aria-label', `${item.label} 月目标`);
    inputCell.append(input);
    tr.append(inputCell);

    const actionCell = document.createElement('td');
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '保存';
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        await api(`/api/admin/targets/${scope}`, {
          method: 'PUT',
          body: JSON.stringify({
            month,
            amount: input.value === '' ? 0 : Number(input.value),
            ...item.keys,
          }),
        });
        notify(`已保存：${item.label} ${month} 目标 ${input.value || 0} 元`);
      } catch (error) {
        notify(`保存失败：${error.message}`, 'error');
      } finally {
        button.disabled = false;
      }
    });
    actionCell.append(button);
    tr.append(actionCell);
    body.append(tr);
  });
  table.append(head, body);
  container.append(table);
}

async function loadTargets() {
  const month = monthValue();
  const storeBox = document.querySelector('#target-store-list');
  const categoryBox = document.querySelector('#target-category-list');
  const operatorBox = document.querySelector('#target-operator-list');
  if (!storeBox || !categoryBox || !operatorBox) return;
  if (!month) {
    for (const box of [storeBox, categoryBox, operatorBox]) box.textContent = '';
    return;
  }
  const data = await api(`/api/admin/targets?month=${encodeURIComponent(month)}`);
  renderTargetGroup(
    storeBox,
    `店铺目标 · ${month}`,
    state.stores.map((item) => ({
      label: item.name,
      amount: data.store[String(item.id)],
      keys: { store_id: item.id },
    })),
    'store',
    month
  );
  const categoryRows = [];
  state.stores.forEach((store) => {
    state.categories.forEach((category) => {
      categoryRows.push({
        label: `${store.name} / ${category.name}（${operatorName(category.operator_id)}）`,
        amount: data.category[`${store.id}:${category.id}`],
        keys: { store_id: store.id, category_id: category.id },
      });
    });
  });
  renderTargetGroup(categoryBox, `类目目标 · ${month}`, categoryRows, 'category', month);
  renderTargetGroup(
    operatorBox,
    `运营目标 · ${month}（两店合计）`,
    state.operators.map((item) => ({
      label: `${item.name}`,
      amount: data.operator[String(item.id)],
      keys: { operator_id: item.id },
    })),
    'operator',
    month
  );
}

function bindForm(selector, submit) {
  const form = document.querySelector(selector);
  if (!form) return;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button');
    button.disabled = true;
    try {
      await submit(new FormData(form));
      form.reset();
      await loadDimensions();
      await loadTargets();
      notify('保存成功');
    } catch (error) {
      notify(`保存失败：${error.message}`, 'error');
    } finally {
      button.disabled = false;
    }
  });
}

bindForm('#operator-form', (data) => api('/api/admin/operators', {
  method: 'POST',
  body: JSON.stringify({ name: data.get('name') }),
}));

bindForm('#store-form', (data) => api('/api/admin/stores', {
  method: 'POST',
  body: JSON.stringify({ name: data.get('name'), platform: data.get('platform') }),
}));

bindForm('#category-form', (data) => api('/api/admin/categories', {
  method: 'POST',
  body: JSON.stringify({ name: data.get('name'), operator_id: Number(data.get('operator_id')) }),
}));

bindForm('#product-form', (data) => api('/api/admin/products', {
  method: 'POST',
  body: JSON.stringify({
    store_id: Number(data.get('store_id')),
    product_id: data.get('product_id'),
    name: data.get('name'),
    category_id: Number(data.get('category_id')),
    operator_id: Number(data.get('operator_id')),
  }),
}));

const productImportForm = document.querySelector('#product-import-form');
const productImportResult = document.querySelector('#product-import-result');

if (productImportForm && productImportResult) {
  productImportForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = productImportForm.querySelector('button');
    button.disabled = true;
    productImportResult.className = 'message';
    productImportResult.textContent = '正在导入商品清单，请稍候...';
    try {
      const response = await fetch('/api/import/products-list', {
        method: 'POST',
        body: new FormData(productImportForm),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '导入失败');
      const stats = body.stats || {};
      const lines = [
        `导入完成：${body.file_name}`,
        `识别表头行：第 ${body.header_row} 行，读取 ${body.rows} 行`,
        `新增商品 ${stats['新增'] || 0}，更新商品 ${stats['更新'] || 0}，跳过 ${stats['跳过'] || 0}`,
        `自动新建运营 ${stats['新建运营'] || 0}，自动新建类目 ${stats['新建类目'] || 0}`,
      ];
      if (stats['未匹配店铺']) {
        lines.push(`未匹配店铺 ${stats['未匹配店铺']} 行：${(stats['未匹配店铺名称'] || []).join('、')}`);
        lines.push('请先在第 2 步建立这些店铺，再重新导入。');
      }
      productImportResult.className = 'message success';
      productImportResult.textContent = lines.join('\n');
      productImportForm.reset();
      await loadDimensions();
      await loadTargets();
    } catch (error) {
      productImportResult.className = 'message error';
      productImportResult.textContent = `导入失败：${error.message}`;
    } finally {
      button.disabled = false;
    }
  });
}

const monthInput = document.querySelector('#target-month');
if (monthInput) {
  const now = new Date();
  monthInput.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  monthInput.addEventListener('change', () => {
    loadTargets().catch((error) => notify(`读取目标失败：${error.message}`, 'error'));
  });
}

loadDimensions()
  .then(() => loadTargets())
  .catch((error) => notify(`读取资料失败：${error.message}`, 'error'));

document.querySelectorAll('.tab[data-tab]').forEach((tab) => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    document.querySelectorAll('.tab[data-tab]').forEach((item) => item.classList.toggle('active', item === tab));
    document.querySelectorAll('section[data-section]').forEach((section) => section.classList.toggle('is-hidden', section.dataset.section !== target));
  });
});
document.querySelectorAll('section[data-section]').forEach((section) => section.classList.toggle('is-hidden', section.dataset.section !== 'operators'));

const resetForm = document.querySelector('#reset-form');
const resetMessage = document.querySelector('#reset-message');

function formatCounts(counts) {
  return Object.entries(counts || {})
    .map(([table, count]) => `${table}: ${count}`)
    .join('\n');
}

if (resetForm && resetMessage) {
  resetForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const confirmation = new FormData(resetForm).get('confirmation');
    if (!window.confirm('此操作将删除全部业务数据，且不可撤销。确定继续吗？')) return;

    const button = resetForm.querySelector('button');
    button.disabled = true;
    resetMessage.className = 'message';
    resetMessage.textContent = '正在备份并清空，请稍候...';
    try {
      const response = await fetch('/api/admin/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '清空失败');
      resetMessage.className = 'message success';
      resetMessage.textContent = [
        '清空完成。',
        `备份路径：${body.backup_path}`,
        '删除前统计：',
        formatCounts(body.before),
        '删除后统计：',
        formatCounts(body.after),
      ].join('\n');
      resetForm.reset();
      await loadDimensions();
      await loadTargets();
    } catch (error) {
      resetMessage.className = 'message error';
      resetMessage.textContent = `清空失败：${error.message}`;
    } finally {
      button.disabled = false;
    }
  });
}
