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
  try {
    await api(`/api/admin/${table}/${item.id}`, { method: 'DELETE' });
    await loadDimensions();
    await loadTargets();
    notify('删除成功');
  } catch (error) {
    notify(`删除失败：${error.message}`, 'error');
  }
}

async function editDimension(table, item) {
  const name = window.prompt('名称', item.name);
  if (name === null) return;
  const values = { name: name.trim() };
  if (!values.name) return notify('名称不能为空', 'error');
  if (table === 'stores') values.platform = window.prompt('平台', item.platform) || item.platform;
  if (table === 'categories') {
    const operators = state.operators.map((operator) => `${operator.id}: ${operator.name}`).join('\n');
    const operatorId = window.prompt(`负责运营编号：\n${operators}`, item.operator_id);
    if (operatorId === null) return;
    values.operator_id = Number(operatorId);
  }
  try {
    await api(`/api/admin/${table}/${item.id}`, { method: 'PUT', body: JSON.stringify(values) });
    await loadDimensions();
    await loadTargets();
    notify('修改成功');
  } catch (error) {
    notify(`修改失败：${error.message}`, 'error');
  }
}

function renderDimensionTable(container, headers, rows, table) {
  if (!rows.length) return emptyNote(container, '暂无数据');
  container.textContent = '';
  const element = document.createElement('table');
  const head = document.createElement('thead');
  const headRow = document.createElement('tr');
  const selectHead = document.createElement('th');
  const selectAll = document.createElement('input');
  selectAll.type = 'checkbox';
  selectAll.setAttribute('aria-label', '全选');
  selectHead.append(selectAll);
  headRow.append(selectHead);
  [...headers, '操作'].forEach((header) => {
    const th = document.createElement('th');
    th.textContent = header;
    headRow.append(th);
  });
  head.append(headRow);
  const body = document.createElement('tbody');
  rows.forEach((item) => {
    const tr = document.createElement('tr');
    const selectCell = document.createElement('td');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'row-select';
    checkbox.dataset.table = table;
    checkbox.dataset.id = item.id;
    selectCell.append(checkbox);
    tr.append(selectCell);
    const values = table === 'operators' ? [item.name, item.id] : table === 'stores' ? [item.name, item.platform, item.id] : [item.name, operatorName(item.operator_id), item.id];
    values.forEach((value) => tr.append(cell(value)));
    const actions = document.createElement('td');
    actions.append(actionButton('编辑', () => editDimension(table, item)), actionButton('删除', () => removeDimension(table, item), 'danger'));
    tr.append(actions);
    body.append(tr);
  });
  selectAll.addEventListener('change', () => body.querySelectorAll('.row-select').forEach((checkbox) => { checkbox.checked = selectAll.checked; }));
  element.append(head, body);
  container.append(element);
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

  fillSelect(document.querySelector('#product-filter-category'), state.categories, (item) => item.id, (item) => item.name, '全部类目');
  fillSelect(document.querySelector('#product-filter-operator'), state.operators, (item) => item.id, (item) => item.name, '全部运营');
  fillSelect(document.querySelector('#bulk-category'), state.categories, (item) => item.id, (item) => item.name, '不改变类目');
  fillSelect(document.querySelector('#bulk-operator'), state.operators, (item) => item.id, (item) => item.name, '不改变运营');
}

function productStatusLabel(status) {
  return status === 'inactive' ? '下架' : '在架';
}

function filteredProducts(storeId) {
  const keyword = (document.querySelector('#product-filter-keyword')?.value || '').trim().toLowerCase();
  const categoryId = document.querySelector('#product-filter-category')?.value || '';
  const operatorId = document.querySelector('#product-filter-operator')?.value || '';
  const status = document.querySelector('#product-filter-status')?.value || '';
  return state.products.filter((item) => {
    if (String(item.store_id) !== String(storeId)) return false;
    if (categoryId && String(item.category_id) !== String(categoryId)) return false;
    if (operatorId && String(item.operator_id) !== String(operatorId)) return false;
    if (status && (item.status || 'active') !== status) return false;
    if (keyword) {
      const haystack = `${item.product_id} ${item.name}`.toLowerCase();
      if (!haystack.includes(keyword)) return false;
    }
    return true;
  });
}

function selectedProducts() {
  return [...document.querySelectorAll('.product-row-select:checked')].map((checkbox) => ({
    store_id: Number(checkbox.dataset.storeId),
    product_id: checkbox.dataset.productId,
  }));
}

function updateSelectedCount() {
  const label = document.querySelector('#product-selected-count');
  if (label) label.textContent = `已选 ${selectedProducts().length} 条`;
}

function renderProductTabs() {
  const container = document.querySelector('#product-list');
  if (!container) return;
  container.textContent = '';
  if (!state.stores.length) return emptyNote(container, '请先建立店铺');
  const tabs = document.createElement('div');
  tabs.className = 'product-store-tabs';
  const tableBox = document.createElement('div');
  const renderStore = (storeId) => {
    const rows = filteredProducts(storeId);
    tableBox.textContent = '';
    const selectedStore = state.stores.find((store) => String(store.id) === String(storeId));
    if (!rows.length) emptyNote(tableBox, `${selectedStore?.name || '所选店铺'}暂无商品`);
    else {
      const table = document.createElement('table');
      const head = document.createElement('thead');
      const headRow = document.createElement('tr');
      const selectHead = document.createElement('th');
      const selectAll = document.createElement('input');
      selectAll.type = 'checkbox';
      selectAll.setAttribute('aria-label', '全选');
      selectHead.append(selectAll);
      headRow.append(selectHead);
      ['商品 ID', '商品名称', '类目', '运营', '状态', '操作'].forEach((label) => {
        const th = document.createElement('th');
        th.textContent = label;
        headRow.append(th);
      });
      head.append(headRow);
      const body = document.createElement('tbody');
      rows.forEach((item) => {
        const tr = document.createElement('tr');
        const selectCell = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'row-select product-row-select';
        checkbox.dataset.table = 'products';
        checkbox.dataset.storeId = item.store_id;
        checkbox.dataset.productId = item.product_id;
        selectCell.append(checkbox);
        tr.append(selectCell);
        [item.product_id, item.name, categoryName(item.category_id), operatorName(item.operator_id), productStatusLabel(item.status)].forEach((value) => tr.append(cell(value)));
        const actions = document.createElement('td');
        actions.append(actionButton('编辑', () => editProduct(item)), actionButton('删除', () => removeProduct(item), 'danger'));
        tr.append(actions);
        body.append(tr);
      });
      table.append(body);
      tableBox.append(table);
      selectAll.addEventListener('change', () => {
        body.querySelectorAll('.row-select').forEach((checkbox) => { checkbox.checked = selectAll.checked; });
        updateSelectedCount();
      });
      body.addEventListener('change', (event) => {
        if (event.target.classList.contains('product-row-select')) updateSelectedCount();
      });
    }
    updateSelectedCount();
    [...tabs.children].forEach((button) => button.classList.toggle('active', button.dataset.storeId === String(storeId)));
  };
  state.stores.forEach((store, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'product-store-tab';
    button.dataset.storeId = store.id;
    button.textContent = store.name;
    button.addEventListener('click', () => renderStore(store.id));
    tabs.append(button);
    if (index === 0) renderStore(store.id);
  });
  container.append(tabs, tableBox);
}

async function editProduct(item) {
  try {
    const name = window.prompt('商品名称', item.name);
    if (name === null) return;
    const productId = window.prompt('商品 ID', item.product_id);
    if (productId === null) return;
    const categoryChoices = state.categories.map((category) => `${category.id}: ${category.name}`).join('\n');
    const categoryId = window.prompt(`类目编号：\n${categoryChoices}`, item.category_id);
    if (categoryId === null) return;
    const operatorChoices = state.operators.map((operator) => `${operator.id}: ${operator.name}`).join('\n');
    const operatorId = window.prompt(`运营编号：\n${operatorChoices}`, item.operator_id);
    if (operatorId === null) return;
    const newProductId = productId.trim();
    if (!name.trim() || !newProductId || !categoryId || !operatorId) {
      notify('商品字段不能为空', 'error');
      return;
    }
    await api(`/api/admin/products/${item.store_id}/${encodeURIComponent(item.product_id)}`, {
      method: 'PUT',
      body: JSON.stringify({ product_id: newProductId, name: name.trim(), category_id: Number(categoryId), operator_id: Number(operatorId) }),
    });
    await loadDimensions();
    await loadTargets();
    notify('商品信息已更新');
  } catch (error) {
    notify(`修改失败：${error.message}`, 'error');
  }
}

async function removeProduct(item) {
  if (!window.confirm(`确定删除商品 ${item.product_id} 吗？`)) return;
  try {
    await api(`/api/admin/products/${item.store_id}/${encodeURIComponent(item.product_id)}`, { method: 'DELETE' });
    await loadDimensions();
    await loadTargets();
    notify('商品已删除');
  } catch (error) {
    notify(`删除失败：${error.message}`, 'error');
  }
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
        `新增商品 ${stats['新增商品'] || 0}，已存在商品 ${stats['已存在商品'] || 0}，重复商品行 ${stats['重复商品行'] || 0}，跳过 ${stats['跳过'] || 0}`,
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

function monthsBetween(start, end) {
  if (!start || !end) return [];
  const [startYear, startMonth] = start.split('-').map(Number);
  const [endYear, endMonth] = end.split('-').map(Number);
  const months = [];
  let cursor = startYear * 12 + startMonth;
  const last = endYear * 12 + endMonth;
  while (cursor <= last) {
    const year = Math.floor((cursor - 1) / 12);
    months.push(`${year}-${String(cursor - year * 12).padStart(2, '0')}`);
    cursor += 1;
  }
  return months;
}

function defaultMonthRange() {
  const now = new Date();
  const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  return [month, month];
}

const syncDailyToggle = document.querySelector('#bulk-sync-daily');
const monthRange = document.querySelector('#bulk-months');
const monthStartInput = document.querySelector('#bulk-month-start');
const monthEndInput = document.querySelector('#bulk-month-end');

if (syncDailyToggle && monthRange && monthStartInput && monthEndInput) {
  const [defaultStart, defaultEnd] = defaultMonthRange();
  monthStartInput.value = defaultStart;
  monthEndInput.value = defaultEnd;
  syncDailyToggle.addEventListener('change', () => { monthRange.hidden = !syncDailyToggle.checked; });
}

async function applyBulkUpdate() {
  const selected = selectedProducts();
  if (!selected.length) return notify('请先选择要修改的商品', 'error');
  const patch = {};
  const category = document.querySelector('#bulk-category')?.value;
  const operator = document.querySelector('#bulk-operator')?.value;
  const status = document.querySelector('#bulk-status')?.value;
  if (category) patch.category_id = Number(category);
  if (operator) patch.operator_id = Number(operator);
  if (status) patch.status = status;
  if (!Object.keys(patch).length) return notify('请选择要修改的类目、运营或状态', 'error');
  const syncDaily = Boolean(syncDailyToggle?.checked);
  const months = syncDaily ? monthsBetween(monthStartInput?.value, monthEndInput?.value) : [];
  if (syncDaily && !months.length) return notify('请选择要覆盖的月份区间', 'error');
  const confirmText = syncDaily
    ? `确定修改 ${selected.length} 条商品，并把 ${months[0]} 至 ${months[months.length - 1]}（共 ${months.length} 个月）的日报归属一并覆盖吗？此操作不可撤销。`
    : `确定修改 ${selected.length} 条商品吗？日报归属不会变化。`;
  if (!window.confirm(confirmText)) return;
  try {
    const result = await api('/api/admin/products/batch-update', {
      method: 'POST',
      body: JSON.stringify({ items: selected, patch, sync_daily: syncDaily, months }),
    });
    await loadDimensions();
    await loadTargets();
    const failed = result.failed || [];
    const detail = syncDaily ? `，同步日报 ${result.daily_rows} 行` : '';
    notify(failed.length
      ? `已修改 ${result.updated} 条，失败 ${failed.length} 条：${failed.map((item) => item.reason).join('；')}${detail}`
      : `已修改 ${result.updated} 条${detail}`, failed.length ? 'error' : 'success');
  } catch (error) {
    notify(`批量修改失败：${error.message}`, 'error');
  }
}

const bulkApplyButton = document.querySelector('#bulk-apply');
if (bulkApplyButton) bulkApplyButton.addEventListener('click', applyBulkUpdate);

document.querySelectorAll('#product-filter-category, #product-filter-operator, #product-filter-status').forEach((select) => {
  select.addEventListener('change', renderProductTabs);
});
document.querySelector('#product-filter-keyword')?.addEventListener('input', renderProductTabs);
document.querySelector('#product-filter-reset')?.addEventListener('click', () => {
  ['#product-filter-category', '#product-filter-operator', '#product-filter-status', '#product-filter-keyword'].forEach((selector) => {
    const element = document.querySelector(selector);
    if (element) element.value = '';
  });
  renderProductTabs();
});

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

document.querySelectorAll('.bulk-delete').forEach((button) => {
  button.addEventListener('click', async () => {
    const table = button.dataset.table;
    const selected = [...document.querySelectorAll(`.row-select[data-table="${table}"]:checked`)].map((checkbox) => table === 'products'
      ? { store_id: Number(checkbox.dataset.storeId), product_id: checkbox.dataset.productId }
      : { id: Number(checkbox.dataset.id) });
    if (!selected.length) return notify('请先选择要删除的记录', 'error');
    if (!window.confirm(`确定删除选中的 ${selected.length} 条记录吗？`)) return;
    try {
      const result = await api('/api/admin/bulk-delete', { method: 'POST', body: JSON.stringify({ table, items: selected }) });
      await loadDimensions();
      await loadTargets();
      const failed = result.failed || [];
      notify(failed.length ? `已删除 ${result.deleted.length} 条，失败 ${failed.length} 条：${failed.map((item) => item.reason).join('；')}` : `已删除 ${result.deleted.length} 条` , failed.length ? 'error' : 'success');
    } catch (error) {
      notify(`批量删除失败：${error.message}`, 'error');
    }
  });
});

const scopedClearMessage = document.querySelector('#scoped-clear-message');
document.querySelectorAll('.scoped-clear').forEach((button) => {
  button.addEventListener('click', async () => {
    const scope = button.dataset.scope;
    const confirmation = window.prompt(`此操作只清空“${button.textContent}”，不会自动删除其他数据。请输入 CLEAR：`);
    if (confirmation === null) return;
    try {
      const result = await api(`/api/admin/clear/${scope}`, { method: 'POST', body: JSON.stringify({ confirmation }) });
      if (scopedClearMessage) {
        scopedClearMessage.className = 'message success';
        scopedClearMessage.textContent = `清空完成：${button.textContent}\n备份：${result.backup_path}\n删除归档：${result.archives_deleted || 0} 个`;
      }
      await loadDimensions();
      await loadTargets();
    } catch (error) {
      if (scopedClearMessage) {
        scopedClearMessage.className = 'message error';
        scopedClearMessage.textContent = `清空失败：${error.message}`;
      }
    }
  });
});


const passwordForm = document.querySelector('#password-form');
const passwordMessage = document.querySelector('#password-message');

if (passwordForm && passwordMessage) {
  passwordForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = passwordForm.querySelector('button');
    button.disabled = true;
    passwordMessage.className = 'message';
    passwordMessage.textContent = '正在修改密码...';
    try {
      const data = new FormData(passwordForm);
      await api('/api/admin/password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: data.get('current_password'),
          new_password: data.get('new_password'),
          confirm_password: data.get('confirm_password'),
        }),
      });
      passwordForm.reset();
      passwordMessage.className = 'message success';
      passwordMessage.textContent = '密码已修改，下次登录请使用新密码。';
    } catch (error) {
      passwordMessage.className = 'message error';
      passwordMessage.textContent = `修改失败：${error.message}`;
    } finally {
      button.disabled = false;
    }
  });
}

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
