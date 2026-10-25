/**
 * QueueLess — Administrator Dashboard Interactivity
 * Handles live queue stats, counter operations (Call Next, Complete, Skip, Recall), and table filters.
 */

class AdminDashboard {
  constructor() {
    this.pollInterval = 4000;
    this.timer = null;
    this.activeFilter = 'ALL';
    this.searchTerm = '';
    this.tokensData = [];
  }

  start() {
    this.fetchData();
    this.timer = setInterval(() => this.fetchData(), this.pollInterval);
    this.setupListeners();
  }

  setupListeners() {
    // Search input
    const searchInput = document.getElementById('admin-token-search');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchTerm = e.target.value.toLowerCase().trim();
        this.renderTable();
      });
    }

    // Filter tabs
    const tabs = document.querySelectorAll('.filter-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        tabs.forEach(t => t.classList.remove('active'));
        e.target.classList.add('active');
        this.activeFilter = e.target.getAttribute('data-filter');
        this.renderTable();
      });
    });
  }

  async fetchData() {
    try {
      const res = await fetch('/api/admin/dashboard-data');
      if (res.status === 401) {
        window.location.href = '/admin/login';
        return;
      }
      const json = await res.json();
      if (json.success && json.data) {
        this.renderStats(json.data.stats);
        this.renderCounters(json.data.services);
        this.tokensData = json.data.recent_tokens || [];
        this.renderTable();
      }
    } catch (e) {
      console.warn("Admin poll error:", e);
    }
  }

  renderStats(stats) {
    if (!stats) return;
    const update = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = val;
    };
    update('stat-total', stats.total_tokens);
    update('stat-waiting', stats.waiting_tokens);
    update('stat-serving', stats.serving_tokens);
    update('stat-completed', stats.completed_tokens);
    update('stat-avg-time', `${stats.avg_service_mins}m`);
  }

  renderCounters(services) {
    if (!services) return;
    services.forEach(s => {
      const card = document.getElementById(`counter-card-${s.id}`);
      if (!card) return;

      const servingEl = card.querySelector('.serving-token-num');
      const visitorEl = card.querySelector('.serving-visitor');
      const waitCountEl = card.querySelector('.counter-waiting-count');
      const nextInLineEl = card.querySelector('.counter-next-inline');
      const btnCall = card.querySelector('.btn-call-next');
      const btnComplete = card.querySelector('.btn-complete');
      const btnSkip = card.querySelector('.btn-skip');
      const btnRecall = card.querySelector('.btn-recall');

      if (s.current_serving) {
        servingEl.innerText = s.current_serving.token_number;
        visitorEl.innerText = s.current_serving.visitor_name || 'Visitor';
        card.querySelector('.serving-display').className = 'serving-display active';
        if (btnComplete) {
          btnComplete.disabled = false;
          btnComplete.setAttribute('data-token-id', s.current_serving.id);
        }
        if (btnSkip) {
          btnSkip.disabled = false;
          btnSkip.setAttribute('data-token-id', s.current_serving.id);
        }
        if (btnRecall) {
          btnRecall.disabled = false;
          btnRecall.setAttribute('data-token-id', s.current_serving.id);
        }
      } else {
        servingEl.innerText = '—';
        visitorEl.innerText = 'No visitor currently serving';
        card.querySelector('.serving-display').className = 'serving-display';
        if (btnComplete) btnComplete.disabled = true;
        if (btnSkip) btnSkip.disabled = true;
        if (btnRecall) btnRecall.disabled = true;
      }

      if (waitCountEl) waitCountEl.innerText = `${s.waiting_count} waiting`;
      if (nextInLineEl) {
        nextInLineEl.innerText = s.next_in_line ? s.next_in_line.token_number : 'None';
      }
    });
  }

  renderTable() {
    const tbody = document.getElementById('admin-tokens-tbody');
    if (!tbody) return;

    let filtered = this.tokensData;
    if (this.activeFilter !== 'ALL') {
      filtered = filtered.filter(t => t.status === this.activeFilter);
    }

    if (this.searchTerm) {
      filtered = filtered.filter(t => 
        (t.token_number && t.token_number.toLowerCase().includes(this.searchTerm)) ||
        (t.visitor_name && t.visitor_name.toLowerCase().includes(this.searchTerm)) ||
        (t.reference_code && t.reference_code.toLowerCase().includes(this.searchTerm)) ||
        (t.service_name && t.service_name.toLowerCase().includes(this.searchTerm))
      );
    }

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #94a3b8; padding: 1.5rem;">No tokens found matching criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(t => {
      const created = new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return `
        <tr>
          <td><strong>${t.token_number}</strong></td>
          <td><span style="font-family: monospace; font-size: 0.85rem; color: #4f46e5;">${t.reference_code}</span></td>
          <td>${t.service_name || '—'}</td>
          <td>${t.visitor_name || 'Visitor'}${t.student_id ? ` <small style="color: #64748b;">(${t.student_id})</small>` : ''}</td>
          <td><span class="badge badge-${t.status.toLowerCase()}">${t.status}</span></td>
          <td style="color: #64748b; font-size: 0.85rem;">${created}</td>
          <td>
            <a href="/status/${t.reference_code}" target="_blank" class="btn btn-secondary btn-sm" title="View Ticket / Live Status">View</a>
          </td>
        </tr>
      `;
    }).join('');
  }

  async callNext(serviceId) {
    try {
      const res = await fetch('/api/admin/call-next', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service_id: serviceId })
      });
      const data = await res.json();
      if (data.success) {
        showToast("Token Called", data.message, "success");
        queueAudio.playChime();
        this.fetchData();
      } else if (data.queue_empty) {
        showToast("Queue Empty", "No visitors are waiting in queue for this service.", "info");
      } else {
        showToast("Error", data.error || "Failed to advance queue.", "danger");
      }
    } catch (e) {
      showToast("Error", "Network error.", "danger");
    }
  }

  async completeCurrent(tokenId) {
    if (!tokenId) return;
    try {
      const res = await fetch('/api/admin/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token_id: tokenId })
      });
      const data = await res.json();
      if (data.success) {
        showToast("Completed", data.message, "success");
        this.fetchData();
      } else {
        showToast("Error", data.error || "Failed to complete token.", "danger");
      }
    } catch (e) {
      showToast("Error", "Network error.", "danger");
    }
  }

  async skipCurrent(tokenId) {
    if (!tokenId) return;
    if (!confirm("Are you sure you want to skip this token? Visitor will be marked as absent.")) return;
    try {
      const res = await fetch('/api/admin/skip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token_id: tokenId })
      });
      const data = await res.json();
      if (data.success) {
        showToast("Skipped", data.message, "warning");
        this.fetchData();
      } else {
        showToast("Error", data.error || "Failed to skip token.", "danger");
      }
    } catch (e) {
      showToast("Error", "Network error.", "danger");
    }
  }

  async recallCurrent(tokenId) {
    if (!tokenId) return;
    try {
      const res = await fetch('/api/admin/recall', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token_id: tokenId })
      });
      const data = await res.json();
      if (data.success) {
        showToast("Recalled", data.message, "info");
        queueAudio.playChime();
        this.fetchData();
      } else {
        showToast("Error", data.error || "Failed to recall token.", "danger");
      }
    } catch (e) {
      showToast("Error", "Network error.", "danger");
    }
  }

  async resetQueue() {
    if (!confirm("Are you sure you want to reset all waiting queues? All active waiting visitors will be cleared.")) return;
    try {
      const res = await fetch('/api/admin/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.success) {
        showToast("Queue Reset", data.message, "warning");
        this.fetchData();
      } else {
        showToast("Error", data.error || "Failed to reset queue.", "danger");
      }
    } catch (e) {
      showToast("Error", "Network error.", "danger");
    }
  }
}
