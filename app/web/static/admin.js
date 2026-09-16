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

function renderDimensions() {
  renderTable(
    document.querySelector('#operator-list'),
    ['运营', '编号'],
    state.operators.map((item) => [item.name, item.id])
  );
  renderTable(
    document.querySelector('#store-list'),
    ['店铺', '平台', '编号'],
    state.stores.map((item) => [item.name, item.platform, item.id])
  );
  renderTable(
    document.querySelector('#category-list'),
    ['类目', '负责运营', '编号'],
    state.categories.map((item) => [item.name, operatorName(item.operator_id), item.id])
  );
  renderTable(
    document.querySelector('#product-list'),
    ['商品 ID', '商品名称', '店铺', '类目', '运营'],
    state.products.map((item) => [
      item.product_id,
      item.name,
      storeName(item.store_id),
      categoryName(item.category_id),
      operatorName(item.operator_id),
    ])
  );

  fillSelect(document.querySelector('#category-operator'), state.operators, (item) => item.id, (item) => item.name, '请选择运营');
  fillSelect(document.querySelector('#product-operator'), state.operators, (item) => item.id, (item) => item.name, '请选择运营');
  fillSelect(document.querySelector('#product-store'), state.stores, (item) => item.id, (item) => item.name, '请选择店铺');
  fillSelect(document.querySelector('#product-category'), state.categories, (item) => item.id, (item) => `${item.name}（${operatorName(item.operator_id)}）`, '请选择类目');
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
