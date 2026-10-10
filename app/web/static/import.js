const form = document.querySelector('#import-form');
const resultBox = document.querySelector('#result');
const storeSelect = document.querySelector('#store-select');
const logList = document.querySelector('#log-list');

const TYPE_LABELS = { store: '店铺数据', product: '商品数据', ad: '推广数据' };

function setResult(text, kind = 'success') {
  if (!resultBox) return;
  resultBox.className = `message ${kind}`;
  resultBox.textContent = text;
}

async function loadStores() {
  if (!storeSelect) return;
  const response = await fetch('/api/admin/stores');
  if (!response.ok) throw new Error('请先登录管理员账号');
  const body = await response.json();
  storeSelect.textContent = '';
  if (!body.items.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = '请先到管理后台新增店铺';
    storeSelect.append(option);
    return;
  }
  body.items.forEach((store) => {
    const option = document.createElement('option');
    option.value = String(store.id);
    option.textContent = `${store.name}（${store.platform}）`;
    storeSelect.append(option);
  });
}

function renderLogs(items) {
  if (!logList) return;
  logList.textContent = '';
  if (!items.length) {
    const p = document.createElement('p');
    p.className = 'empty';
    p.textContent = '暂无导入记录';
    logList.append(p);
    return;
  }
  const table = document.createElement('table');
  const head = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['时间', '类型', '文件', '数据日期', '新增', '更新', '跳过', '未匹配', '操作'].forEach((label) => {
    const th = document.createElement('th');
    th.textContent = label;
    headRow.append(th);
  });
  head.append(headRow);
  const body = document.createElement('tbody');
  items.forEach((item) => {
    const tr = document.createElement('tr');
    const values = [
      (item.created_at || '').replace('T', ' ').slice(0, 19),
      TYPE_LABELS[item.file_type] || item.file_type,
      item.file_name,
      item.data_date,
      item.inserted_rows,
      item.updated_rows,
      item.skipped_rows,
      item.unmatched_rows,
    ];
    values.forEach((value) => {
      const td = document.createElement('td');
      td.textContent = String(value === null || value === undefined ? '' : value);
      tr.append(td);
    });
    const actionCell = document.createElement('td');
    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.textContent = '删除记录和文件';
    deleteButton.addEventListener('click', async () => {
      if (!window.confirm(`确定删除导入记录“${item.file_name}”及其归档文件吗？`)) return;
      try {
        const response = await fetch(`/api/import/logs/${item.id}`, { method: 'DELETE' });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || '删除失败');
        await loadLogs();
      } catch (error) {
        setResult(`删除失败：${error.message}`, 'error');
      }
    });
    actionCell.append(deleteButton);
    tr.append(actionCell);
    body.append(tr);
  });
  table.append(head, body);
  logList.append(table);
}

async function loadLogs() {
  const response = await fetch('/api/import/logs');
  if (!response.ok) return;
  renderLogs((await response.json()).items);
}

if (form) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button');
    button.disabled = true;
    setResult('正在上传并解析，请稍候...');
    try {
      const response = await fetch('/api/import/upload', { method: 'POST', body: new FormData(form) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || body.error || '导入失败');
      const stats = body.stats || {};
      setResult([
        `导入完成：${body.file_name}`,
        `识别表头行：第 ${body.header_row} 行，读取 ${body.rows} 行`,
        `新增 ${stats['新增'] || 0}，更新 ${stats['更新'] || 0}，跳过 ${stats['跳过'] || 0}，未匹配 ${stats['未匹配'] || 0}`,
        (stats['未匹配'] || 0) > 0 ? '存在未匹配商品，请到管理后台补建商品后重新导入。' : '',
      ].filter(Boolean).join('\n'));
      await loadLogs();
    } catch (error) {
      setResult(`导入失败：${error.message}`, 'error');
    } finally {
      button.disabled = false;
    }
  });
}

loadStores().catch((error) => setResult(error.message, 'error'));
loadLogs().catch(() => {});
