/* ═══ Quest Log v1.01 — Frontend JS ═══ */

// ── Toast ──
function showToast(msg, duration = 2000) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}

// ── API Helper ──
async function api(url, method = 'POST', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  return res.json();
}

// ── Binary Toggle ──
async function toggleBinary(habitId) {
  const item = document.querySelector(`.habit-item[data-id="${habitId}"]`);
  const isDone = item?.classList.contains('completed');

  if (isDone) {
    const data = await api('/api/binary/uncomplete', 'POST', { habit_id: habitId });
    if (data.success) {
      item.classList.remove('completed');
      const btn = item.querySelector('.check-btn');
      btn.classList.remove('checked'); btn.textContent = '';
      item.querySelector('.habit-name')?.classList.remove('line-through');
      const timeEl = item.querySelector('.habit-time');
      if (timeEl) timeEl.remove();
      showToast(`↩ 撤销 -${data.xp_refunded} XP`);
      updateXpDisplay(data.total_xp, data.level);
    } else { showToast(data.error || '操作失败'); }
  } else {
    const data = await api('/api/binary/complete', 'POST', { habit_id: habitId });
    if (data.success) {
      item.classList.add('completed');
      const btn = item.querySelector('.check-btn');
      btn.classList.add('checked'); btn.textContent = '✓';
      item.querySelector('.habit-name')?.classList.add('line-through');
      const xpEl = item.querySelector('.habit-xp');
      if (xpEl && !item.querySelector('.habit-time')) {
        const timeSpan = document.createElement('span');
        timeSpan.className = 'habit-time';
        timeSpan.textContent = data.completed_at;
        xpEl.before(timeSpan);
      }
      showToast(`✅ +${data.xp_earned} XP`);
      updateXpDisplay(data.total_xp, data.level);
      const list = item.parentElement;
      list.appendChild(item);
      if (data.achievements?.length) {
        for (const a of data.achievements) {
          setTimeout(() => showToast(`🏆 解锁: ${a.name} +${a.xp_reward} XP`, 3000), 500);
        }
      }
    } else { showToast(data.error || '操作失败'); }
  }
}

// ── SOP Step Complete ──
async function completeSopStep(habitId, stepOrder) {
  const data = await api('/api/sop/complete_step', 'POST', { habit_id: habitId, step_order: stepOrder });
  if (data.success) {
    const card = document.querySelector(`.sop-card[data-id="${habitId}"]`);
    const step = card?.querySelector(`.sop-step[data-step="${stepOrder}"]`);
    if (step) {
      step.classList.add('step-done');
      const btn = step.querySelector('.step-check');
      btn.classList.add('checked'); btn.textContent = '✓'; btn.disabled = true;
    }
    const nextStep = card?.querySelector(`.sop-step[data-step="${stepOrder + 1}"]`);
    if (nextStep) {
      nextStep.classList.remove('step-locked');
      const nextBtn = nextStep.querySelector('.step-check');
      if (nextBtn) { nextBtn.disabled = false; nextBtn.textContent = `${stepOrder + 1}`; }
    }
    const fill = card?.querySelector('.sop-fill');
    const progress = card?.querySelector('.sop-progress');
    if (fill && data.total_steps) fill.style.width = `${(data.completed_steps / data.total_steps * 100)}%`;
    if (progress) progress.textContent = `${data.completed_steps}/${data.total_steps}`;
    showToast(`✅ +${data.xp_earned} XP`);
    updateXpDisplay(data.total_xp, data.level);
    if (data.all_done) {
      setTimeout(() => {
        if (!card.querySelector('.sop-complete-badge')) {
          const badge = document.createElement('div');
          badge.className = 'sop-complete-badge';
          badge.textContent = '🎉 SOP 完成！';
          card.appendChild(badge);
        }
        showToast('🎉 SOP 全部完成！', 3000);
      }, 300);
    }
  } else { showToast(data.error || '操作失败'); }
}

// ── Update XP display ──
function updateXpDisplay(totalXp, level) {
  const statValues = document.querySelectorAll('.stat-value');
  if (statValues.length >= 2) {
    statValues[0].textContent = `Lv.${level}`;
    statValues[1].textContent = `${totalXp} XP`;
  }
}

// ── Date Navigation ──
function goToDate(dateStr) {
  if (dateStr) window.location.href = `/day/${dateStr}`;
}

// ═══ CRUD: Add / Edit / Delete ═══

let editingId = null;

function openAddModal(taskType, frequency) {
  editingId = null;
  document.getElementById('modalTitle').textContent = '添加习惯';
  document.getElementById('modalName').value = '';
  document.getElementById('modalIcon').value = '';
  document.getElementById('modalXp').value = '10';

  // Set type
  document.querySelectorAll('#modalType .type-option').forEach(b => {
    b.classList.toggle('active', b.dataset.value === taskType);
  });

  // Set frequency
  document.querySelectorAll('#modalFreq .type-option').forEach(b => {
    b.classList.toggle('active', b.dataset.value === frequency);
  });

  // Show/hide SOP steps
  toggleSopSteps(taskType === 'sop');
  document.getElementById('sopStepsList').innerHTML = '';

  document.getElementById('habitModal').style.display = 'flex';
}

function openEditModal(habitId) {
  const habit = ALL_HABITS.find(h => h.id === habitId);
  if (!habit) return;

  editingId = habitId;
  document.getElementById('modalTitle').textContent = '编辑习惯';
  document.getElementById('modalName').value = habit.name;
  document.getElementById('modalIcon').value = habit.icon;
  document.getElementById('modalXp').value = habit.base_xp;

  // Set type
  document.querySelectorAll('#modalType .type-option').forEach(b => {
    b.classList.toggle('active', b.dataset.value === habit.task_type);
  });

  // Set frequency
  document.querySelectorAll('#modalFreq .type-option').forEach(b => {
    b.classList.toggle('active', b.dataset.value === habit.frequency);
  });

  // SOP steps
  toggleSopSteps(habit.task_type === 'sop');
  const stepsList = document.getElementById('sopStepsList');
  stepsList.innerHTML = '';
  if (habit.steps) {
    habit.steps.forEach(s => addSopStep(s.label, s.xp, s.description));
  }

  document.getElementById('habitModal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('habitModal').style.display = 'none';
  editingId = null;
}

function toggleSopSteps(show) {
  document.getElementById('sopStepsField').style.display = show ? 'block' : 'none';
}

function pickType(btn) {
  btn.parentElement.querySelectorAll('.type-option').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  toggleSopSteps(btn.dataset.value === 'sop');
}

function pickFreq(btn) {
  btn.parentElement.querySelectorAll('.type-option').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

function addSopStep(label = '', xp = 10, desc = '') {
  const list = document.getElementById('sopStepsList');
  const div = document.createElement('div');
  div.className = 'sop-step-input';
  div.innerHTML = `
    <input type="text" class="step-label-input" placeholder="步骤名称" value="${label}">
    <input type="number" class="step-xp-input" placeholder="XP" value="${xp}" min="1">
    <button class="remove-step-btn" onclick="this.parentElement.remove()">✕</button>
  `;
  list.appendChild(div);
}

async function saveHabit() {
  const name = document.getElementById('modalName').value.trim();
  if (!name) { showToast('请输入名称'); return; }

  const icon = document.getElementById('modalIcon').value || '📋';
  const taskType = document.querySelector('#modalType .type-option.active')?.dataset.value || 'binary';
  const frequency = document.querySelector('#modalFreq .type-option.active')?.dataset.value || 'daily';
  const baseXp = parseInt(document.getElementById('modalXp').value) || 10;

  const body = { name, icon, task_type: taskType, frequency, base_xp: baseXp };

  // Collect SOP steps
  if (taskType === 'sop') {
    const stepInputs = document.querySelectorAll('#sopStepsList .sop-step-input');
    body.steps = [];
    stepInputs.forEach((div, i) => {
      const label = div.querySelector('.step-label-input').value.trim();
      const xp = parseInt(div.querySelector('.step-xp-input').value) || 10;
      if (label) body.steps.push({ step_order: i + 1, label, xp, description: '' });
    });
    if (body.steps.length === 0) { showToast('SOP 至少需要一个步骤'); return; }
  }

  let data;
  if (editingId) {
    data = await api(`/api/habits/${editingId}`, 'PUT', body);
  } else {
    data = await api('/api/habits', 'POST', body);
  }

  if (data.success) {
    closeModal();
    showToast(editingId ? '✅ 已更新' : '✅ 已添加');
    setTimeout(() => location.reload(), 300);
  } else {
    showToast(data.error || '操作失败');
  }
}

async function deleteHabit(habitId, name) {
  if (!confirm(`确定删除「${name}」？\n历史记录会保留，但该习惯将不再显示。`)) return;

  const data = await api(`/api/habits/${habitId}`, 'DELETE');
  if (data.success) {
    showToast('🗑️ 已删除');
    // Remove from UI
    const el = document.querySelector(`[data-id="${habitId}"]`);
    if (el) el.remove();
    setTimeout(() => location.reload(), 500);
  } else {
    showToast(data.error || '删除失败');
  }
}

// ── Logout ──
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
  await fetch('/api/logout', { method: 'POST' });
  window.location.href = '/login';
});

// ── Binary habit row click ──
document.querySelectorAll('.habit-item[data-type="binary"]').forEach(item => {
  item.addEventListener('click', (e) => {
    if (e.target.closest('.check-btn') || e.target.closest('.habit-actions')) return;
    const id = item.dataset.id;
    if (id) toggleBinary(parseInt(id));
  });
});

// ── Close modal on overlay click ──
document.getElementById('habitModal')?.addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});
