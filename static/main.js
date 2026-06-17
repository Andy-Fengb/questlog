/* ═══ Quest Log v2 — Frontend JS ═══ */

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
    // Uncomplete
    const data = await api('/api/binary/uncomplete', 'POST', { habit_id: habitId });
    if (data.success) {
      item.classList.remove('completed');
      const btn = item.querySelector('.check-btn');
      btn.classList.remove('checked');
      btn.textContent = '';
      item.querySelector('.habit-name')?.classList.remove('line-through');
      const timeEl = item.querySelector('.habit-time');
      if (timeEl) timeEl.remove();
      showToast(`↩ 撤销 -${data.xp_refunded} XP`);
      updateXpDisplay(data.total_xp, data.level);
    } else {
      showToast(data.error || '操作失败');
    }
  } else {
    // Complete
    const data = await api('/api/binary/complete', 'POST', { habit_id: habitId });
    if (data.success) {
      item.classList.add('completed');
      const btn = item.querySelector('.check-btn');
      btn.classList.add('checked');
      btn.textContent = '✓';
      item.querySelector('.habit-name')?.classList.add('line-through');

      // Add completion time
      const xpEl = item.querySelector('.habit-xp');
      if (xpEl && !item.querySelector('.habit-time')) {
        const timeSpan = document.createElement('span');
        timeSpan.className = 'habit-time';
        timeSpan.textContent = data.completed_at;
        xpEl.before(timeSpan);
      }

      showToast(`✅ +${data.xp_earned} XP`);
      updateXpDisplay(data.total_xp, data.level);

      // Move to bottom
      const list = item.parentElement;
      list.appendChild(item);

      // Check achievements
      if (data.achievements?.length) {
        for (const a of data.achievements) {
          setTimeout(() => showToast(`🏆 解锁成就: ${a.name} +${a.xp_reward} XP`, 3000), 500);
        }
      }
    } else {
      showToast(data.error || '操作失败');
    }
  }
}

// ── SOP Step Complete ──
async function completeSopStep(habitId, stepOrder) {
  const data = await api('/api/sop/complete_step', 'POST', {
    habit_id: habitId,
    step_order: stepOrder,
  });

  if (data.success) {
    // Update step UI
    const card = document.querySelector(`.sop-card[data-id="${habitId}"]`);
    const step = card?.querySelector(`.sop-step[data-step="${stepOrder}"]`);
    if (step) {
      step.classList.add('step-done');
      const btn = step.querySelector('.step-check');
      btn.classList.add('checked');
      btn.textContent = '✓';
      btn.disabled = true;

      // Add time
      if (!step.querySelector('.step-time')) {
        const timeSpan = document.createElement('span');
        timeSpan.className = 'step-time';
        timeSpan.textContent = '✓';
        step.appendChild(timeSpan);
      }
    }

    // Unlock next step
    const nextStep = card?.querySelector(`.sop-step[data-step="${stepOrder + 1}"]`);
    if (nextStep) {
      nextStep.classList.remove('step-locked');
      const nextBtn = nextStep.querySelector('.step-check');
      if (nextBtn) {
        nextBtn.disabled = false;
        nextBtn.textContent = `${stepOrder + 1}`;
      }
    }

    // Update progress bar
    const fill = card?.querySelector('.sop-fill');
    const progress = card?.querySelector('.sop-progress');
    if (fill && data.total_steps) {
      fill.style.width = `${(data.completed_steps / data.total_steps * 100)}%`;
    }
    if (progress) {
      progress.textContent = `${data.completed_steps}/${data.total_steps}`;
    }

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
  } else {
    showToast(data.error || '操作失败');
  }
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
  if (dateStr) {
    window.location.href = `/day/${dateStr}`;
  }
}

// ── Logout ──
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
  await fetch('/api/logout', { method: 'POST' });
  window.location.href = '/login';
});

// ── Binary habit row click (toggle) ──
document.querySelectorAll('.habit-item[data-type="binary"]').forEach(item => {
  item.addEventListener('click', (e) => {
    // Don't double-trigger if they clicked the button directly
    if (e.target.closest('.check-btn')) return;
    const id = item.dataset.id;
    if (id) toggleBinary(parseInt(id));
  });
});
