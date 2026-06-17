// ═══════════════════════════════════════
//  Quest Log — Main JS
// ═══════════════════════════════════════

// ── Week Chart ──
new Chart(document.getElementById('weekChart'), {
  type: 'bar',
  data: {
    labels: weekData.map(d => d.date.slice(5)),
    datasets: [{
      label: 'XP',
      data: weekData.map(d => d.xp),
      backgroundColor: '#e94560',
      borderRadius: 4,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, grid: { color: '#2a2a4a' }, ticks: { color: '#8892b0' } },
      x: { grid: { display: false }, ticks: { color: '#8892b0' } }
    }
  }
});

// ── Tab Switching ──
function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  const target = document.getElementById('tab-' + tabId);
  if (target) target.classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  if (tabId === 'data') {
    setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
  }
}

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ── Flip Book Animation ──
const fab = document.getElementById('fabBook');
const tabs = ['tasks', 'achievements', 'data'];
let fabIndex = 0;
if (fab) {
  fab.addEventListener('click', function() {
    fabIndex = (fabIndex + 1) % tabs.length;
    this.style.transform = 'rotateY(180deg) scale(1.1)';
    setTimeout(() => {
      this.style.transform = '';
      switchTab(tabs[fabIndex]);
    }, 200);
  });
}

// ── Habit Card Click (Toggle / Record) ──
document.querySelectorAll('.task-card').forEach(card => {
  card.addEventListener('click', async function(e) {
    // Don't trigger if clicking modal or form elements
    if (e.target.closest('.modal-overlay')) return;

    const habitId = this.dataset.habit;
    const habitType = this.dataset.type;
    const isDone = this.classList.contains('done');

    try {
      if (habitType === 'yesno') {
        // Toggle yesno
        if (isDone) {
          await undoHabit(habitId);
        } else {
          await completeHabit(habitId);
        }
      } else if (habitType === 'number') {
        // Prompt for count
        const target = this.dataset.target || 10;
        const defaultVal = 5;
        const input = prompt(`🔢 ${this.querySelector('.task-name').textContent} — 今天做了多少？（目標 ${target}）`, defaultVal);
        if (input === null) return;
        const val = parseInt(input);
        if (isNaN(val) || val <= 0) { showToast('❌ 請輸入有效數字'); return; }
        await completeHabit(habitId, val);
      } else if (habitType === 'timer') {
        // Prompt for minutes
        const target = this.dataset.target || 30;
        const defaultMin = 5;
        const input = prompt(`⏱ ${this.querySelector('.task-name').textContent} — 今天做了幾分鐘？（目標 ${target}）`, defaultMin);
        if (input === null) return;
        const minutes = parseInt(input);
        if (isNaN(minutes) || minutes <= 0) { showToast('❌ 請輸入有效分鐘數'); return; }
        await completeHabit(habitId, minutes);
      }
    } catch(e) {
      console.error(e);
      showToast('❌ 操作失敗');
    }
  });
});

async function completeHabit(habitId, value) {
  const body = { habit_id: habitId };
  if (value !== undefined) body.value = value;

  const resp = await fetch('/api/complete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const data = await resp.json();

  if (data.success) {
    const card = document.querySelector(`[data-habit="${habitId}"]`);
    if (card) {
      card.classList.add('done');
      const target = data.target;
      // Update progress display
      if (data.total_value !== undefined) {
        const total = data.total_value;
        const pct = Math.min(100, (total / target * 100));
        const ring = card.querySelector('.progress-ring');
        if (ring) {
          ring.innerHTML = `${total}/${target}<div class="progress-bar-inner" style="width:${pct}%"></div>`;
        }
        card.dataset.progress = total;
      } else {
        const check = card.querySelector('.check');
        if (check) check.textContent = '✓';
      }
    }
    let msg = `✅ +${data.xp_earned} XP`;
    if (data.achievements && data.achievements.length) {
      msg += ' · ' + data.achievements.join(' · ');
    }
    showToast(msg);
    setTimeout(() => location.reload(), 800);
  } else if (data.error === 'already completed today') {
    showToast('⚠️ 今天已完成');
  } else {
    showToast('❌ ' + (data.error || 'Error'));
  }
}

async function undoHabit(habitId) {
  const resp = await fetch('/api/uncomplete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({habit_id: habitId})
  });
  const data = await resp.json();
  if (data.success) {
    const card = document.querySelector(`[data-habit="${habitId}"]`);
    if (card) {
      card.classList.remove('done');
      const check = card.querySelector('.check');
      if (check) check.textContent = '';
      const ring = card.querySelector('.progress-ring');
      if (ring) {
        const target = card.dataset.target || 30;
        ring.innerHTML = `0/${target}<div class="progress-bar-inner" style="width:0%"></div>`;
      }
    }
    showToast(`↩️ 已取消，退還 ${data.xp_refunded} XP`);
    setTimeout(() => location.reload(), 800);
  } else {
    showToast('❌ ' + (data.error || 'Error'));
  }
}

// ── Toast ──
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  if (msg.includes('XP') && !msg.includes('取消') && !msg.includes('退還') && !msg.includes('已完成')) {
    t.style.borderColor = 'var(--gold)';
    t.style.background = 'linear-gradient(135deg, #1a1a2e, #2a1a0e)';
    t.style.boxShadow = '0 0 30px rgba(240, 192, 64, 0.3)';
  } else {
    t.style.borderColor = 'var(--green)';
    t.style.background = 'var(--card2)';
    t.style.boxShadow = '0 4px 20px rgba(0,0,0,0.4)';
  }
  setTimeout(() => t.classList.remove('show'), 3500);
}

// ── Calendar ──
const datePicker = document.getElementById('datePicker');
const dayTasks = document.getElementById('dayTasks');
const daySummary = document.getElementById('daySummary');

async function loadDay(dateStr) {
  try {
    const resp = await fetch(`/api/day?date=${dateStr}`);
    const data = await resp.json();
    if (data.tasks && data.tasks.length > 0) {
      dayTasks.innerHTML = data.tasks.map(t =>
        `<span class="day-task-badge">${t.icon} ${t.name} <span class="day-xp">+${t.xp}XP</span></span>`
      ).join('');
      daySummary.textContent = `✅ ${data.count} 項 · ${data.total_xp} XP`;
    } else {
      dayTasks.innerHTML = '<span class="day-empty">📭 這天沒有記錄</span>';
      daySummary.textContent = '';
    }
  } catch(e) {
    dayTasks.innerHTML = '<span class="day-empty">❌ 載入失敗</span>';
    daySummary.textContent = '';
  }
}
if (datePicker) {
  loadDay(datePicker.value);
  datePicker.addEventListener('change', function() { loadDay(this.value); });
}

// ── Auto-Polling ──
const syncBadge = document.getElementById('syncBadge');
let lastKnownState = null;

async function pollState() {
  try {
    if (!syncBadge) return;
    syncBadge.className = 'sync-badge syncing';
    syncBadge.textContent = '⟳ 同步';
    const resp = await fetch('/api/state');
    const state = await resp.json();
    if (lastKnownState && (
      lastKnownState.total_xp !== state.total_xp ||
      lastKnownState.streak !== state.streak ||
      JSON.stringify(lastKnownState.done_today) !== JSON.stringify(state.done_today)
    )) {
      syncBadge.textContent = '🔄 已更新';
      syncBadge.className = 'sync-badge';
      setTimeout(() => location.reload(), 500);
      return;
    }
    lastKnownState = state;
    syncBadge.textContent = '● 即時';
    syncBadge.className = 'sync-badge';
  } catch(e) {
    if (syncBadge) {
      syncBadge.textContent = '⚠ 離線';
      syncBadge.className = 'sync-badge stale';
    }
  }
}
if (syncBadge) {
  fetch('/api/state').then(r => r.json()).then(s => { lastKnownState = s; });
  setInterval(pollState, 30000);
}

// ── Live Clock ──
function updateClock() {
  const el = document.getElementById('liveClock');
  if (!el) return;
  const now = new Date();
  el.textContent =
    `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
}
updateClock();
setInterval(updateClock, 1000);

// ── Editable Title ──
const siteTitle = document.getElementById('siteTitle');
const titleBtn = document.getElementById('titleEditBtn');

if (siteTitle && titleBtn) {
  function enableTitleEdit() {
    siteTitle.contentEditable = 'true';
    siteTitle.classList.add('editable-hint');
    siteTitle.focus();
    const range = document.createRange();
    range.selectNodeContents(siteTitle);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    titleBtn.textContent = '💾';
  }

  async function saveTitle() {
    const newTitle = siteTitle.textContent.trim();
    if (newTitle) {
      try {
        await fetch('/api/save_config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({key: 'title', value: newTitle})
        });
      } catch(e) {}
    }
    siteTitle.contentEditable = 'false';
    siteTitle.classList.remove('editable-hint');
    titleBtn.textContent = '✏️';
  }

  titleBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    if (siteTitle.contentEditable === 'true') saveTitle();
    else enableTitleEdit();
  });
  siteTitle.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { e.preventDefault(); this.blur(); }
  });
  siteTitle.addEventListener('blur', saveTitle);
}

// ── Logout ──
const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
  logoutBtn.addEventListener('click', async function() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/login';
  });
}

// ═══════════════════════════════════════
//  Add / Edit Habit Modal
// ═══════════════════════════════════════

const modal = document.getElementById('habitModal');
const modalTitle = document.getElementById('modalTitle');
const modalName = document.getElementById('modalName');
const modalIcon = document.getElementById('modalIcon');
const modalTarget = document.getElementById('modalTarget');
const modalXp = document.getElementById('modalXp');
const modalScheduleValue = document.getElementById('modalScheduleValue');
const modalConfirm = document.getElementById('modalConfirm');
const modalCancel = document.getElementById('modalCancel');
const modalClose = document.getElementById('modalClose');
const addBtn = document.getElementById('addHabitBtn');

// Edit state
let editingHabitId = null;

// Type picker
document.querySelectorAll('#modalType .type-option').forEach(btn => {
  btn.addEventListener('click', function() {
    document.querySelectorAll('#modalType .type-option').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
  });
});

// Schedule picker
document.querySelectorAll('#modalSchedule .type-option').forEach(btn => {
  btn.addEventListener('click', function() {
    document.querySelectorAll('#modalSchedule .type-option').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('weeklyInput').style.display =
      this.dataset.value === 'weekly_x' ? 'block' : 'none';
  });
});

// Category picker → Group picker with dynamic fields
document.querySelectorAll('#modalGroup .type-option').forEach(btn => {
  btn.addEventListener('click', function() {
    document.querySelectorAll('#modalGroup .type-option').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    const g = this.dataset.value;
    document.getElementById('deadlineField').style.display = g === 'milestone' ? 'block' : 'none';
    document.getElementById('targetScopeField').style.display = g === 'target' ? 'block' : 'none';
  });
});

function openModal(habitData) {
  if (habitData) {
    // Edit mode
    editingHabitId = habitData.id;
    modalTitle.textContent = '✏️ 編輯習慣';
    modalName.value = habitData.name;
    modalIcon.value = habitData.icon;
    modalTarget.value = habitData.target_value;
    modalXp.value = habitData.base_xp;

    // Select type
    document.querySelectorAll('#modalType .type-option').forEach(b => {
      b.classList.toggle('active', b.dataset.value === habitData.type);
    });

    // Select schedule
    document.querySelectorAll('#modalSchedule .type-option').forEach(b => {
      b.classList.toggle('active', b.dataset.value === habitData.schedule_type);
    });
    document.getElementById('weeklyInput').style.display =
      habitData.schedule_type === 'weekly_x' ? 'block' : 'none';
    modalScheduleValue.value = habitData.schedule_value;

    // Select category → Group
    document.querySelectorAll('#modalGroup .type-option').forEach(b => {
      b.classList.toggle('active', b.dataset.value === (habitData.group || 'daily'));
    });
    document.getElementById('deadlineField').style.display = (habitData.group || 'daily') === 'milestone' ? 'block' : 'none';
    document.getElementById('targetScopeField').style.display = (habitData.group || 'daily') === 'target' ? 'block' : 'none';
    if (habitData.group === 'milestone' && habitData.deadline)
      document.getElementById('modalDeadline').value = habitData.deadline;
    if (habitData.group === 'target' && habitData.scope)
      document.querySelectorAll('#modalScope .type-option').forEach(b =>
        b.classList.toggle('active', b.dataset.value === habitData.scope));

    modalConfirm.textContent = '💾 更新';
  } else {
    // Add mode
    editingHabitId = null;
    modalTitle.textContent = '✚ 新增習慣';
    modalName.value = '';
    modalIcon.value = '📌';
    modalTarget.value = 30;
    modalXp.value = 10;
    modalScheduleValue.value = 3;
    document.querySelectorAll('#modalType .type-option').forEach((b,i) => b.classList.toggle('active', i===0));
    document.querySelectorAll('#modalSchedule .type-option').forEach((b,i) => b.classList.toggle('active', i===0));
    document.querySelectorAll('#modalGroup .type-option').forEach((b,i) => b.classList.toggle('active', i===0));
    document.getElementById('weeklyInput').style.display = 'none';
    modalConfirm.textContent = '✚ 新增';
  }
  modal.style.display = 'flex';
  setTimeout(() => modalName.focus(), 100);
}

function closeModal() {
  modal.style.display = 'none';
  editingHabitId = null;
}

// Add habit button
if (addBtn) {
  addBtn.addEventListener('click', () => openModal(null));
}

// Close buttons
if (modalClose) modalClose.addEventListener('click', closeModal);
if (modalCancel) modalCancel.addEventListener('click', closeModal);
modal.addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

// Save / Update
if (modalConfirm) {
  modalConfirm.addEventListener('click', async function() {
    const name = modalName.value.trim();
    if (!name) { showToast('❌ 請輸入習慣名稱'); return; }

    const type = document.querySelector('#modalType .type-option.active')?.dataset.value || 'yesno';
    const schedule = document.querySelector('#modalSchedule .type-option.active')?.dataset.value || 'daily';
    const group = document.querySelector('#modalGroup .type-option.active')?.dataset.value || 'daily';
    const scheduleVal = schedule === 'weekly_x' ? parseInt(modalScheduleValue.value) || 3 : 1;
    const target = parseInt(modalTarget.value) || 30;
    const xp = parseInt(modalXp.value) || 10;
    const icon = modalIcon.value.trim() || '📌';

    const body = {
      name, icon, type,
      schedule_type: schedule,
      schedule_value: scheduleVal,
      target_value: target,
      base_xp: xp,
      group: document.querySelector('#modalGroup .type-option.active')?.dataset.value || 'daily',
      deadline: document.getElementById('modalDeadline')?.value || null,
      scope: document.querySelector('#modalScope .type-option.active')?.dataset.value || null
    };

    try {
      let resp;
      if (editingHabitId) {
        resp = await fetch(`/api/habits/${editingHabitId}`, {
          method: 'PUT',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(body)
        });
      } else {
        resp = await fetch('/api/habits', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(body)
        });
      }
      const data = await resp.json();
      if (data.success) {
        showToast(editingHabitId ? '✅ 已更新習慣' : '✅ 已新增習慣');
        closeModal();
        setTimeout(() => location.reload(), 600);
      } else {
        showToast('❌ ' + (data.error || 'Error'));
      }
    } catch(e) {
      showToast('❌ 儲存失敗');
    }
  });
}

// ── Delete habit (via hover + confirm) ──
// Add delete button to each habit card on hover
document.querySelectorAll('.task-card').forEach(card => {
  const delBtn = document.createElement('button');
  delBtn.className = 'card-delete-btn';
  delBtn.textContent = '✕';
  delBtn.title = '刪除習慣';
  delBtn.addEventListener('click', async function(e) {
    e.stopPropagation();
    const habitId = card.dataset.habit;
    const name = card.querySelector('.task-name')?.textContent || '此習慣';
    if (!confirm(`確定刪除「${name}」？所有歷史記錄將保留但不再顯示。`)) return;
    try {
      const resp = await fetch(`/api/habits/${habitId}`, { method: 'DELETE' });
      const data = await resp.json();
      if (data.success) {
        showToast(`🗑️ 已刪除「${name}」`);
        setTimeout(() => location.reload(), 600);
      } else {
        showToast('❌ ' + (data.error || '刪除失敗'));
      }
    } catch(e) {
      showToast('❌ 刪除失敗');
    }
  });
  card.appendChild(delBtn);
});

// ── Edit habit button ──
document.querySelectorAll('.task-card').forEach(card => {
  const editBtn = document.createElement('button');
  editBtn.className = 'card-edit-btn';
  editBtn.textContent = '✏️';
  editBtn.title = '編輯習慣';
  editBtn.addEventListener('click', async function(e) {
    e.stopPropagation();
    const habitId = card.dataset.habit;
    try {
      const resp = await fetch(`/api/habits`);
      const data = await resp.json();
      const habit = data.habits.find(h => h.id == habitId);
      if (habit) openModal(habit);
    } catch(e) {
      showToast('❌ 載入失敗');
    }
  });
  card.appendChild(editBtn);
});