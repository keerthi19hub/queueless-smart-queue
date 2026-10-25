/**
 * QueueLess — Public TV / Kiosk Display Script
 * Live multi-counter board with audio announcements and visual pulse for waiting halls.
 */

class PublicDisplay {
  constructor() {
    this.pollInterval = 3500;
    this.timer = null;
    this.lastAnnouncementTime = null;
    this.audioEnabled = true;
  }

  start() {
    this.updateClock();
    setInterval(() => this.updateClock(), 1000);
    this.fetchData();
    this.timer = setInterval(() => this.fetchData(), this.pollInterval);
  }

  updateClock() {
    const el = document.getElementById('display-clock');
    if (el) {
      const now = new Date();
      el.innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
  }

  async fetchData() {
    try {
      const res = await fetch('/api/display');
      const json = await res.json();
      if (json.success && json.data) {
        this.render(json.data);
      }
    } catch (e) {
      console.warn("Display fetch error:", e);
    }
  }

  render(data) {
    const counters = data.counters || [];
    const grid = document.getElementById('display-counters-grid');
    if (!grid) return;

    grid.innerHTML = counters.map(c => {
      const isServing = c.now_serving && c.now_serving !== '—';
      return `
        <div class="display-counter-card ${isServing ? 'is-active' : ''}">
          <div class="display-counter-header">
            <span class="display-counter-name">${c.counter_number}</span>
            <span class="display-service-name">${c.service_name}</span>
          </div>
          <div class="display-counter-body">
            <div class="display-now-serving-label">NOW SERVING</div>
            <div class="display-serving-token">${c.now_serving}</div>
            ${c.visitor_name ? `<div class="display-visitor-name">${c.visitor_name}</div>` : ''}
          </div>
          <div class="display-counter-footer">
            <div class="display-waiting-count">${c.waiting_count} waiting</div>
            <div class="display-upcoming">
              <span>Next:</span> ${c.upcoming.length > 0 ? c.upcoming.join(', ') : 'None'}
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Announcement banner check
    if (data.latest_announcement && data.latest_announcement_time !== this.lastAnnouncementTime) {
      this.lastAnnouncementTime = data.latest_announcement_time;
      const ticker = document.getElementById('display-ticker-text');
      if (ticker) {
        ticker.innerText = `🔔 ${data.latest_announcement}`;
      }
      if (this.audioEnabled) {
        queueAudio.playUrgentCall();
      }
    }
  }
}
