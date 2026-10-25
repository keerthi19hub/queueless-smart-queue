/**
 * QueueLess — Visitor Live Status Tracker
 * Handles smart polling, stepper transitions, audio alerts, and event logs.
 */

class QueueTracker {
  constructor(refCode) {
    this.refCode = refCode;
    this.pollInterval = 3000; // 3 seconds
    this.timer = null;
    this.lastStatus = null;
    this.lastPeopleAhead = null;
    this.hasNotifiedApproaching = false;
    this.hasNotifiedServing = false;
    this.soundEnabled = true;
  }

  start() {
    if (!this.refCode) return;
    this.fetchStatus();
    this.timer = setInterval(() => this.fetchStatus(), this.pollInterval);
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  async fetchStatus() {
    try {
      const res = await fetch(`/api/token/status/${encodeURIComponent(this.refCode)}`);
      if (!res.ok) {
        if (res.status === 404) {
          this.stop();
          showToast("Not Found", "Token could not be located.", "danger");
        }
        return;
      }
      const data = await res.json();
      if (data.success && data.data) {
        this.render(data.data);
      }
    } catch (e) {
      console.warn("Status fetch failed:", e);
    }
  }

  render(token) {
    const status = token.status;
    const rawStatus = token.raw_status;
    const peopleAhead = token.people_ahead;
    const currentServing = token.current_serving || '—';
    const estWait = token.estimated_wait_mins;

    // Update Text Elements
    const elServing = document.getElementById('val-current-serving');
    const elAhead = document.getElementById('val-people-ahead');
    const elWait = document.getElementById('val-est-wait');
    const elStatusBadge = document.getElementById('val-status-badge');
    const elCounter = document.getElementById('val-counter-num');

    if (elServing) elServing.innerText = currentServing;
    if (elAhead) elAhead.innerText = rawStatus === 'WAITING' ? peopleAhead : 0;
    if (elWait) elWait.innerText = rawStatus === 'WAITING' ? `${estWait} mins` : (rawStatus === 'SERVING' ? 'Now' : '0 mins');
    if (elCounter) elCounter.innerText = token.counter_number;

    // Update Status Badge
    if (elStatusBadge) {
      elStatusBadge.className = `badge badge-${status.toLowerCase()}`;
      elStatusBadge.innerText = status;
    }

    // Stepper updates
    this.updateStepper(status, rawStatus);

    // Urgent Calling Banner
    const urgentBanner = document.getElementById('serving-alert-banner');
    if (urgentBanner) {
      if (rawStatus === 'SERVING') {
        urgentBanner.style.display = 'block';
        urgentBanner.innerHTML = `
          <h3>🔔 IT'S YOUR TURN!</h3>
          <p>Please proceed immediately to <strong>${token.counter_number} (${token.service_name})</strong>.</p>
        `;
      } else if (status === 'APPROACHING') {
        urgentBanner.style.display = 'block';
        urgentBanner.className = 'urgent-banner';
        urgentBanner.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
        urgentBanner.innerHTML = `
          <h3>⚡ GET READY!</h3>
          <p>Your turn is approaching! Only <strong>${peopleAhead}</strong> ${peopleAhead === 1 ? 'person' : 'people'} ahead of you.</p>
        `;
      } else {
        urgentBanner.style.display = 'none';
      }
    }

    // Trigger Notification Events
    this.handleNotifications(token);

    // Update Event Log
    this.renderEvents(token.events);

    // Cache state
    this.lastStatus = status;
    this.lastPeopleAhead = peopleAhead;

    // Stop polling if completed, cancelled, or skipped
    if (['COMPLETED', 'SKIPPED', 'CANCELLED'].includes(rawStatus)) {
      this.stop();
      const cancelBtn = document.getElementById('btn-cancel-token');
      if (cancelBtn) cancelBtn.style.display = 'none';
    }
  }

  updateStepper(status, rawStatus) {
    const steps = ['step-created', 'step-waiting', 'step-approaching', 'step-serving', 'step-completed'];
    steps.forEach(s => {
      const el = document.getElementById(s);
      if (el) el.className = 'step-item';
    });

    const setStepState = (id, state) => {
      const el = document.getElementById(id);
      if (el) el.classList.add(state);
    };

    setStepState('step-created', 'completed');

    if (rawStatus === 'WAITING') {
      if (status === 'APPROACHING') {
        setStepState('step-waiting', 'completed');
        setStepState('step-approaching', 'active');
      } else {
        setStepState('step-waiting', 'active');
      }
    } else if (rawStatus === 'SERVING') {
      setStepState('step-waiting', 'completed');
      setStepState('step-approaching', 'completed');
      setStepState('step-serving', 'active');
    } else if (rawStatus === 'COMPLETED') {
      setStepState('step-waiting', 'completed');
      setStepState('step-approaching', 'completed');
      setStepState('step-serving', 'completed');
      setStepState('step-completed', 'completed');
    }
  }

  handleNotifications(token) {
    const rawStatus = token.raw_status;
    const status = token.status;

    // Event 1: Serving Called
    if (rawStatus === 'SERVING' && (!this.hasNotifiedServing || this.lastStatus !== 'SERVING')) {
      this.hasNotifiedServing = true;
      if (this.soundEnabled) queueAudio.playUrgentCall();
      
      showToast(
        "🚨 YOUR TURN CALLED!",
        `Token ${token.token_number}: Please proceed to ${token.counter_number}.`,
        "success",
        10000
      );
      
      NotificationManager.send(
        `🚨 YOUR TURN: Token ${token.token_number}`,
        `Please proceed immediately to ${token.counter_number} (${token.service_name}).`
      );

      if ('vibrate' in navigator) {
        navigator.vibrate([300, 150, 300, 150, 400]);
      }
    }

    // Event 2: Turn Approaching
    if (status === 'APPROACHING' && !this.hasNotifiedApproaching && rawStatus === 'WAITING') {
      this.hasNotifiedApproaching = true;
      if (this.soundEnabled) queueAudio.playChime();

      showToast(
        "⚡ Turn Approaching",
        `Only ${token.people_ahead} ahead of you for ${token.service_name}. Please stay nearby!`,
        "warning",
        7000
      );

      NotificationManager.send(
        `⚡ Turn Approaching: Token ${token.token_number}`,
        `You have ${token.people_ahead} in front of you. Please head towards ${token.counter_number}.`
      );
    }
  }

  renderEvents(events) {
    const container = document.getElementById('history-list');
    if (!container || !events) return;

    if (events.length === 0) {
      container.innerHTML = `<li style="color: #94a3b8; font-size: 0.85rem;">No updates recorded yet.</li>`;
      return;
    }

    container.innerHTML = events.map(e => {
      const date = new Date(e.created_at);
      const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return `
        <li class="history-item">
          <span class="history-time">${timeStr}</span>
          <span>${e.message}</span>
        </li>
      `;
    }).join('');
  }

  async cancelToken() {
    if (!confirm("Are you sure you want to leave the queue and cancel this token? This action cannot be undone.")) {
      return;
    }

    try {
      const res = await fetch('/api/token/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reference_code: this.refCode })
      });
      const data = await res.json();
      if (data.success) {
        showToast("Cancelled", "Your token was cancelled.", "info");
        this.fetchStatus();
      } else {
        showToast("Error", data.error || "Could not cancel token.", "danger");
      }
    } catch (e) {
      showToast("Error", "Network connection error.", "danger");
    }
  }
}
