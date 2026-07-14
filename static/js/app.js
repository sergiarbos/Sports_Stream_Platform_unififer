(function () {
  "use strict";

  const input = document.getElementById("event-search");
  const rowEls = Array.from(
    document.querySelectorAll(".schedule-row[data-search]"),
  );
  const featured = document.querySelectorAll(".featured-card");

  let fuse = null;
  if (typeof Fuse !== "undefined" && rowEls.length) {
    const fuseData = rowEls.map((el, i) => ({
      i,
      text: el.dataset.search || "",
    }));
    fuse = new Fuse(fuseData, {
      keys: ["text"],
      threshold: 0.35, // 0 = exact, 1 = match anything
      minMatchCharLength: 2,
    });
  }

  function normalize(text) {
    return text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  if (input) {
    input.addEventListener("input", function () {
      const query = input.value.trim();

      if (!query) {
        rowEls.forEach((row) => (row.style.display = ""));
        featured.forEach((card) => (card.style.display = ""));
        return;
      }

      featured.forEach((card) => (card.style.display = "none"));

      let matchSet;
      if (fuse) {
        // Fuzzy search — tolerates typos
        const results = fuse.search(query);
        matchSet = new Set(results.map((r) => r.item.i));
      } else {
        // Fallback: normalized exact substring
        const norm = normalize(query);
        matchSet = new Set(
          rowEls
            .map((el, i) =>
              normalize(el.dataset.search).includes(norm) ? i : -1,
            )
            .filter((i) => i >= 0),
        );
      }

      rowEls.forEach((row, i) => {
        row.style.display = matchSet.has(i) ? "" : "none";
      });
    });
  }

  /* ──────────────────────────────────────────────────────────────────────────
   * 1b. LANGUAGE SELECTOR DROPDOWN
   * ────────────────────────────────────────────────────────────────────────── */
  const langBtn = document.getElementById("lang-btn");
  const langDropdown = document.getElementById("lang-dropdown");

  if (langBtn && langDropdown) {
    langBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = !langDropdown.hidden;
      langDropdown.hidden = open;
      langBtn.setAttribute("aria-expanded", String(!open));
    });

    document.addEventListener("click", (e) => {
      if (
        !langDropdown.hidden &&
        !langDropdown.contains(e.target) &&
        e.target !== langBtn
      ) {
        langDropdown.hidden = true;
        langBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ──────────────────────────────────────────────────────────────────────────
   * 2. LINKS PANEL — master-detail (one event at a time)
   * ────────────────────────────────────────────────────────────────────────── */
  const linksCol = document.querySelector(".links-col");
  const allLinkCards = document.querySelectorAll(".link-card");
  const allRows = document.querySelectorAll(".schedule-row[data-event-id]");

  function selectEvent(id, scrollIntoView) {
    allLinkCards.forEach((card) =>
      card.classList.toggle("is-active", card.id === id),
    );
    allRows.forEach((row) =>
      row.classList.toggle("is-selected", row.dataset.eventId === id),
    );
    if (scrollIntoView && id) {
      const card = document.getElementById(id);
      if (card) card.scrollIntoView({ behavior: "smooth", block: "nearest" });
      if (linksCol)
        linksCol.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  document.querySelectorAll('a[href^="#event-"]').forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const id = this.getAttribute("href").slice(1);
      history.pushState(null, "", "#" + id);
      selectEvent(id, true);
    });
  });

  document.querySelectorAll(".link-card-close").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      history.pushState(
        null,
        "",
        window.location.pathname + window.location.search,
      );
      selectEvent(null, false);
    });
  });

  window.addEventListener("popstate", () =>
    selectEvent(window.location.hash.slice(1), false),
  );

  // On load: restore from URL hash (shared links)
  selectEvent(window.location.hash.slice(1), false);

  /* ──────────────────────────────────────────────────────────────────────────
   * 3. LIVE BELL DROPDOWN + AJAX POLLING
   * ────────────────────────────────────────────────────────────────────────── */
  const bellBtn = document.getElementById("live-bell-btn");
  const bellDropdown = document.getElementById("bell-dropdown");
  const bellList = document.getElementById("bell-dropdown-list");
  const bellEmpty = document.getElementById("bell-dropdown-empty");
  const bellCount = document.getElementById("live-bell-count");
  const bellCta = document.getElementById("bell-dropdown-cta");

  if (bellBtn && bellDropdown) {
    function updateBadge(count) {
      if (count > 0) {
        bellCount.textContent = count;
        bellCount.style.display = "flex";
        bellBtn.classList.add("live-bell--active");
        bellBtn.setAttribute(
          "aria-label",
          count + " event" + (count !== 1 ? "s" : "") + " live now",
        );
      } else {
        bellCount.style.display = "none";
        bellBtn.classList.remove("live-bell--active");
        bellBtn.setAttribute("aria-label", "No events live right now");
      }
    }

    function escHtml(str) {
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function renderDropdownItems(events) {
      bellList.innerHTML = "";
      if (events && events.length > 0) {
        bellEmpty.hidden = true;
        events.forEach((ev) => {
          const li = document.createElement("li");
          const href = "?view_mode=links#event-" + ev.id;
          li.innerHTML =
            '<a class="bell-dropdown-item" href="' +
            href +
            '">' +
            '<span class="bell-dropdown-item-icon" aria-hidden="true">' +
            (ev.sport_icon || "🔴") +
            "</span>" +
            '<span class="bell-dropdown-item-body">' +
            '<span class="bell-dropdown-item-comp">' +
            escHtml(ev.competition) +
            "</span>" +
            '<span class="bell-dropdown-item-title">' +
            escHtml(ev.title) +
            "</span>" +
            "</span>" +
            '<span class="bell-dropdown-item-live" aria-hidden="true">' +
            '<span class="live-dot" style="width:6px;height:6px;flex-shrink:0"></span>LIVE' +
            "</span>" +
            "</a>";
          bellList.appendChild(li);
        });
        if (bellCta) bellCta.style.display = "";
      } else {
        bellEmpty.hidden = false;
        if (bellCta) bellCta.style.display = "none";
      }
    }

    function openDropdown() {
      bellDropdown.hidden = false;
      bellBtn.setAttribute("aria-expanded", "true");
      renderDropdownItems(window._liveBellEvents || []);
    }

    function closeDropdown() {
      bellDropdown.hidden = true;
      bellBtn.setAttribute("aria-expanded", "false");
    }

    bellBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      bellDropdown.hidden ? openDropdown() : closeDropdown();
    });

    document.addEventListener("click", (e) => {
      if (
        !bellDropdown.hidden &&
        !bellDropdown.contains(e.target) &&
        e.target !== bellBtn
      ) {
        closeDropdown();
      }
    });

    function fetchLiveStatus() {
      fetch("/api/live-status/")
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (!data) return;
          window._liveBellEvents = data.events || [];
          updateBadge(data.live_count || 0);
          if (!bellDropdown.hidden) renderDropdownItems(window._liveBellEvents);
        })
        .catch(() => {});
    }

    const initialCount = parseInt(bellCount.textContent, 10) || 0;
    window._liveBellEvents = window._liveBellEvents || [];
    updateBadge(initialCount);
    setInterval(fetchLiveStatus, 60000);
    fetchLiveStatus();
  }

  /* ──────────────────────────────────────────────────────────────────────────
   * 4. REMINDER BELLS (Service Worker integration)
   *    sw-register.js exposes window.scheduleReminder / window.cancelReminder.
   *    Falls back silently if SW is not supported.
   * ────────────────────────────────────────────────────────────────────────── */
  document.querySelectorAll(".reminder-bell-btn").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();

      const id = btn.dataset.eventId || "";
      const title = btn.dataset.title || "Sports event";
      const comp = btn.dataset.comp || "";
      const startIso = btn.dataset.start || "";

      if (btn.classList.contains("is-set")) {
        // Cancel reminder
        btn.classList.remove("is-set");
        btn.title = "Set reminder";
        btn.setAttribute("aria-label", "Set reminder for " + title);
        if (typeof window.cancelReminder === "function")
          window.cancelReminder(id);
      } else {
        // Schedule reminder via Service Worker
        btn.classList.add("is-set");
        btn.title = "Reminder set — click to cancel";
        btn.setAttribute("aria-label", "Cancel reminder for " + title);

        if (typeof window.scheduleReminder === "function") {
          window.scheduleReminder({
            id,
            title,
            comp,
            startIso,
            url: "?view_mode=links#event-" + id,
          });
        }
      }
    });
  });

  /* ──────────────────────────────────────────────────────────────────────────
   * 5. KEYBOARD SHORTCUTS (A11y)
   *    /        → focus search input
   *    Escape   → close bell dropdown OR deselect active link card
   *    ↑ / ↓    → navigate between visible schedule rows
   *    Enter    → activate "Get links" on focused schedule row
   * ────────────────────────────────────────────────────────────────────────── */
  document.addEventListener("keydown", function (e) {
    const tag = (document.activeElement || {}).tagName || "";
    const inInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

    // "/" → focus search (only when not already typing)
    if (e.key === "/" && !inInput) {
      e.preventDefault();
      if (input) {
        input.focus();
        input.select();
      }
    }

    // Escape → close dropdown or deselect event
    if (e.key === "Escape") {
      if (bellDropdown && !bellDropdown.hidden) {
        // Close bell dropdown
        bellDropdown.hidden = true;
        if (bellBtn) {
          bellBtn.setAttribute("aria-expanded", "false");
          bellBtn.focus();
        }
      } else if (document.querySelector(".link-card.is-active")) {
        // Deselect active link card
        history.pushState(
          null,
          "",
          window.location.pathname + window.location.search,
        );
        selectEvent(null, false);
      } else if (inInput && input) {
        // Clear search & blur
        input.value = "";
        input.dispatchEvent(new Event("input"));
        input.blur();
      }
    }

    // ↑ / ↓ → navigate visible schedule rows
    if ((e.key === "ArrowUp" || e.key === "ArrowDown") && !inInput) {
      const visibleRows = Array.from(
        document.querySelectorAll(".schedule-row[data-event-id]"),
      ).filter((r) => r.style.display !== "none");

      if (!visibleRows.length) return;

      const current = document.querySelector(".schedule-row.is-selected");
      let idx = visibleRows.indexOf(current);

      if (e.key === "ArrowDown") {
        idx = idx < visibleRows.length - 1 ? idx + 1 : 0;
      } else {
        idx = idx > 0 ? idx - 1 : visibleRows.length - 1;
      }

      const target = visibleRows[idx];
      if (target) {
        const id = target.dataset.eventId;
        history.pushState(null, "", "#" + id);
        selectEvent(id, true);
        e.preventDefault();
      }
    }

    // Enter → activate "Get links" on selected row (when not in input)
    if (e.key === "Enter" && !inInput) {
      const selected = document.querySelector(".schedule-row.is-selected");
      if (selected) {
        const btn = selected.querySelector('a[href^="#event-"]');
        if (btn) btn.click();
        e.preventDefault();
      }
    }
  });
})();
