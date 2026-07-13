
(function () {
  'use strict';

  const input = document.getElementById('event-search');
  const rows = document.querySelectorAll('.schedule-row[data-search]');
  const featured = document.querySelectorAll('.featured-card');

  function normalize(text) {
    return text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }

  if (input) {
    input.addEventListener('input', function () {
      const query = normalize(input.value.trim());

      rows.forEach(function (row) {
        const match = !query || normalize(row.dataset.search).includes(query);
        row.style.display = match ? '' : 'none';
      });

      featured.forEach(function (card) {
        card.style.display = query ? 'none' : '';
      });
    });
  }

  const linksCol = document.querySelector('.links-col');
  const allLinkCards = document.querySelectorAll('.link-card');
  const allRows = document.querySelectorAll('.schedule-row[data-event-id]');

  function selectEvent(id, scrollIntoView) {
    allLinkCards.forEach(function (card) {
      card.classList.toggle('is-active', card.id === id);
    });
    allRows.forEach(function (row) {
      row.classList.toggle('is-selected', row.dataset.eventId === id);
    });
    if (scrollIntoView && id) {
      const card = document.getElementById(id);
      if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      if (linksCol) linksCol.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  document.querySelectorAll('a[href^="#event-"]').forEach(function (btn) {
    btn.addEventListener('click', function (event) {
      event.preventDefault();
      const id = this.getAttribute('href').slice(1);
      history.pushState(null, '', '#' + id);
      selectEvent(id, true);
    });
  });

  document.querySelectorAll('.link-card-close').forEach(function (btn) {
    btn.addEventListener('click', function (event) {
      event.preventDefault();
      history.pushState(null, '', window.location.pathname + window.location.search);
      selectEvent(null, false);
    });
  });

  window.addEventListener('popstate', function () {
    selectEvent(window.location.hash.slice(1), false);
  });

  selectEvent(window.location.hash.slice(1), false);
  const bellBtn = document.getElementById('live-bell-btn');
  const bellDropdown = document.getElementById('bell-dropdown');
  const bellList = document.getElementById('bell-dropdown-list');
  const bellEmpty = document.getElementById('bell-dropdown-empty');
  const bellCount = document.getElementById('live-bell-count');
  const bellCta = document.getElementById('bell-dropdown-cta');

  if (!bellBtn || !bellDropdown) return;

  function updateBadge(count) {
    if (count > 0) {
      bellCount.textContent = count;
      bellCount.style.display = 'flex';
      bellBtn.classList.add('live-bell--active');
      bellBtn.setAttribute('aria-label', count + ' event' + (count !== 1 ? 's' : '') + ' live now');
    } else {
      bellCount.style.display = 'none';
      bellBtn.classList.remove('live-bell--active');
      bellBtn.setAttribute('aria-label', 'No events live right now');
    }
  }

  function renderDropdownItems(events) {
    bellList.innerHTML = '';
    if (events && events.length > 0) {
      bellEmpty.hidden = true;
      events.forEach(function (ev) {
        const li = document.createElement('li');
        const href = '?view_mode=links#event-' + ev.id;
        li.innerHTML =
          '<a class="bell-dropdown-item" href="' + href + '">' +
          '<span class="bell-dropdown-item-icon" aria-hidden="true">' + (ev.sport_icon || '🔴') + '</span>' +
          '<span class="bell-dropdown-item-body">' +
          '<span class="bell-dropdown-item-comp">' + escHtml(ev.competition) + '</span>' +
          '<span class="bell-dropdown-item-title">' + escHtml(ev.title) + '</span>' +
          '</span>' +
          '<span class="bell-dropdown-item-live" aria-hidden="true"><span class="live-dot" style="width:6px;height:6px;flex-shrink:0"></span>LIVE</span>' +
          '</a>';
        bellList.appendChild(li);
      });
      bellCta.style.display = '';
    } else {
      bellEmpty.hidden = false;
      bellCta.style.display = 'none';
    }
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function openDropdown() {
    bellDropdown.hidden = false;
    bellBtn.setAttribute('aria-expanded', 'true');
    renderDropdownItems(window._liveBellEvents || []);
  }

  function closeDropdown() {
    bellDropdown.hidden = true;
    bellBtn.setAttribute('aria-expanded', 'false');
  }

  function toggleDropdown() {
    if (!bellDropdown.hidden) {
      closeDropdown();
    } else {
      openDropdown();
    }
  }

  bellBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    toggleDropdown();
  });

  // Close when clicking outside
  document.addEventListener('click', function (e) {
    if (!bellDropdown.hidden && !bellDropdown.contains(e.target) && e.target !== bellBtn) {
      closeDropdown();
    }
  });

  // Close on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !bellDropdown.hidden) {
      closeDropdown();
      bellBtn.focus();
    }
  });

  function fetchLiveStatus() {
    fetch('/api/live-status/')
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (!data) return;
        window._liveBellEvents = data.events || [];
        updateBadge(data.live_count || 0);
        if (!bellDropdown.hidden) {
          renderDropdownItems(window._liveBellEvents);
        }
      })
      .catch(function () { /* Silently ignore network errors */ });
  }

  var initialCount = parseInt(bellCount.textContent, 10) || 0;
  window._liveBellEvents = window._liveBellEvents || [];
  updateBadge(initialCount);
  setInterval(fetchLiveStatus, 60000);
  fetchLiveStatus();

  document.querySelectorAll('.reminder-bell-btn').forEach(function (btn) {
    btn.addEventListener('click', function (event) {
      event.preventDefault();
      var hasReminder = btn.classList.toggle('has-reminder');
      var scheduleRow = btn.closest('.schedule-row');
      var eventId = scheduleRow ? scheduleRow.dataset.eventId : null;
      if (!eventId) return;

      var url = hasReminder
        ? '/api/events/' + eventId + '/set-reminder/'
        : '/api/events/' + eventId + '/remove-reminder/';

      fetch(url, { method: 'POST' })
        .then(function (res) { if (res.ok) return res.json(); }) // parse response if needed
        .then(function (data) {
        })
        .catch(function () { /* ignore API errors silently */ });
    });
  });
  document.querySelectorAll('.reminder-bell-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      const title = btn.dataset.title || 'Sports event';
      const comp = btn.dataset.comp || '';
      const startIso = btn.dataset.start || '';
      const eventId = btn.dataset.eventId || '';
      const storageKey = 'reminder-' + eventId;

      // Toggle off if already set
      if (btn.classList.contains('is-set')) {
        btn.classList.remove('is-set');
        btn.title = 'Set reminder';
        btn.setAttribute('aria-label', 'Set reminder for ' + title);
        localStorage.removeItem(storageKey);
        return;
      }

      if (!('Notification' in window)) {
        alert('Your browser does not support notifications.');
        return;
      }

      Notification.requestPermission().then(function (perm) {
        if (perm !== 'granted') return;

        const startMs = startIso ? new Date(startIso).getTime() : 0;
        const delay = startMs - Date.now();

        if (delay < 0) {
          alert('This event has already started!');
          return;
        }

        btn.classList.add('is-set');
        btn.title = 'Reminder set — click to cancel';
        btn.setAttribute('aria-label', 'Cancel reminder for ' + title);

        const timeoutId = setTimeout(function () {
          new Notification('🔴 Starting now!', {
            body: (comp ? comp + ' · ' : '') + title,
            icon: '/static/favicon.ico',
            tag: 'event-' + eventId,
          });
          btn.classList.remove('is-set');
          localStorage.removeItem(storageKey);
        }, delay);
        localStorage.setItem(storageKey, JSON.stringify({
          title: title,
          comp: comp,
          start: startIso,
          timeoutId: timeoutId,
        }));
      });
    });
  });

})();
