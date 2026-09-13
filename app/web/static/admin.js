const root = document.querySelector('#admin-root');
if (root) {
  root.innerHTML = '<p>请选择左侧资料或目标管理。</p>';
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
    } catch (error) {
      resetMessage.className = 'message error';
      resetMessage.textContent = `清空失败：${error.message}`;
    } finally {
      button.disabled = false;
    }
  });
}
