// Global Raspberry Pi Control Center Client-side JS

const RPi = {
  csrfToken: document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '',

  async fetchApi(url, options = {}) {
    const opts = { ...options };
    opts.headers = {
      'Accept': 'application/json',
      'X-CSRFToken': RPi.csrfToken,
      ...(opts.headers || {})
    };

    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }

    try {
      const res = await fetch(url, opts);
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.message || `Request failed with status ${res.status}`);
      }
      return json;
    } catch (err) {
      RPi.showToast(err.message, 'error');
      throw err;
    }
  },

  showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container-custom';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast-custom toast-${type}`;
    toast.innerHTML = `
      <span>${message}</span>
      <button style="background:none;border:none;color:var(--text-muted);cursor:pointer;margin-left:10px;" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 250);
    }, 4000);
  },

  confirmAction(title, message, onConfirm) {
    const modal = document.getElementById('global-confirm-modal');
    if (!modal) return;
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;

    const confirmBtn = document.getElementById('modal-confirm-btn');
    const newBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

    newBtn.onclick = () => {
      RPi.closeModal();
      onConfirm();
    };

    modal.classList.add('active');
  },

  closeModal() {
    const modal = document.getElementById('global-confirm-modal');
    if (modal) modal.classList.remove('active');
  },

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('rpi_theme', next);
    const icon = document.getElementById('theme-toggle-icon');
    if (icon) {
      icon.className = next === 'dark' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
    }
  },

  initTheme() {
    const saved = localStorage.getItem('rpi_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    const icon = document.getElementById('theme-toggle-icon');
    if (icon) {
      icon.className = saved === 'dark' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
    }
  },

  toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (sidebar) {
      const isOpen = sidebar.classList.toggle('open');
      if (backdrop) {
        backdrop.classList.toggle('active', isOpen);
      }
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  RPi.initTheme();

  // Close modals when clicking backdrop
  const modal = document.getElementById('global-confirm-modal');
  if (modal) {
    modal.onclick = (e) => {
      if (e.target === modal) RPi.closeModal();
    };
  }
});
