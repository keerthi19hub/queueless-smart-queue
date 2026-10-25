/**
 * QueueLess — Core Client Utilities
 * Handles sound chimes (Web Audio API), in-app toasts, browser notifications, and clipboard helpers.
 */

// Sound Synthesizer using Web Audio API
class QueueAudio {
  constructor() {
    this.ctx = null;
    this.enabled = true;
  }

  init() {
    if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  // Play standard gentle bell chime (for turn approaching or general status)
  playChime() {
    if (!this.enabled) return;
    try {
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const osc1 = this.ctx.createOscillator();
      const osc2 = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc1.type = 'sine';
      osc2.type = 'sine';

      // Pleasant chord (F5 and A5)
      osc1.frequency.setValueAtTime(698.46, now);
      osc2.frequency.setValueAtTime(880.00, now + 0.1);

      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(0.2, now + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 1.2);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(this.ctx.destination);

      osc1.start(now);
      osc1.stop(now + 0.6);
      osc2.start(now + 0.1);
      osc2.stop(now + 1.2);
    } catch (e) {
      console.warn("Audio chime prevented:", e);
    }
  }

  // Play urgent announcement chime (for "Your Turn / Called to Counter")
  playUrgentCall() {
    if (!this.enabled) return;
    try {
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6 arpeggio

      notes.forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const start = now + (idx * 0.15);

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(0.25, start + 0.04);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.8);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(start);
        osc.stop(start + 0.8);
      });
    } catch (e) {
      console.warn("Audio call alert prevented:", e);
    }
  }
}

const queueAudio = new QueueAudio();

// In-app Toast Notifications
function showToast(title, message, type = 'info', durationMs = 5000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = type === 'success' ? '✓' : (type === 'warning' ? '⚠' : (type === 'danger' ? '✖' : 'ℹ'));

  toast.innerHTML = `
    <div style="font-weight: 800; font-size: 1.1rem; line-height: 1;">${icon}</div>
    <div style="flex: 1;">
      <div style="font-weight: 700; font-size: 0.92rem; color: #1e293b; margin-bottom: 2px;">${title}</div>
      <div style="font-size: 0.85rem; color: #475569;">${message}</div>
    </div>
    <button onclick="this.parentElement.remove()" style="background: none; border: none; cursor: pointer; color: #94a3b8; font-size: 1.1rem; padding: 0 4px;">&times;</button>
  `;

  container.appendChild(toast);

  if (durationMs > 0) {
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, durationMs);
  }
}

// Browser Desktop Notifications
const NotificationManager = {
  isSupported() {
    return 'Notification' in window;
  },

  getPermission() {
    return this.isSupported() ? Notification.permission : 'unsupported';
  },

  async requestPermission() {
    if (!this.isSupported()) {
      showToast("Browser Notifications", "Your browser does not support desktop notifications.", "warning");
      return false;
    }
    const perm = await Notification.requestPermission();
    if (perm === 'granted') {
      showToast("Notifications Enabled", "You will receive desktop alerts when your turn approaches.", "success");
      return true;
    } else {
      showToast("Permission Denied", "Desktop alerts are blocked. You can still use in-app notifications.", "info");
      return false;
    }
  },

  send(title, body, tag = 'queue-alert') {
    if (this.isSupported() && Notification.permission === 'granted') {
      try {
        const notif = new Notification(title, {
          body: body,
          icon: '/static/favicon.svg',
          tag: tag,
          requireInteraction: true
        });
        notif.onclick = () => {
          window.focus();
          notif.close();
        };
      } catch (e) {
        console.warn("Notification error:", e);
      }
    }
  }
};

// Copy Text Helper
function copyToClipboard(text, successMsg = "Copied to clipboard!") {
  navigator.clipboard.writeText(text).then(() => {
    showToast("Success", successMsg, "success", 2500);
  }).catch(() => {
    // Fallback
    const input = document.createElement('input');
    input.value = text;
    document.body.appendChild(input);
    input.select();
    document.execCommand('copy');
    document.body.removeChild(input);
    showToast("Success", successMsg, "success", 2500);
  });
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
  // Mobile navigation menu toggle
  const mobileToggle = document.getElementById('mobile-menu-toggle');
  const navLinks = document.getElementById('nav-links');
  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', () => {
      navLinks.classList.toggle('show');
    });
  }

  // Initialize audio on first user interaction anywhere
  const enableAudioOnce = () => {
    queueAudio.init();
    document.removeEventListener('click', enableAudioOnce);
    document.removeEventListener('keydown', enableAudioOnce);
  };
  document.addEventListener('click', enableAudioOnce);
  document.addEventListener('keydown', enableAudioOnce);
});
