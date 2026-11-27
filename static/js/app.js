(function () {
  "use strict";

  const input = document.getElementById("event-search");
  const suggestions = document.getElementById("search-suggestions");
  const rowEls = Array.from(
    document.querySelectorAll(
      ".schedule-row[data-search], .result-row[data-search]",
    ),
  );
  const featured = document.querySelectorAll(".featured-card");
  const competitionHeaders = Array.from(
    document.querySelectorAll(".competition-subheader"),
  );
  let searchMatchSet = null;
  let activeSuggestionIndex = -1;
  let favoritesOnly = false;
  let favorites = new Set();
  try {
    favorites = new Set(
      JSON.parse(localStorage.getItem("sports-favorites") || "[]"),
    );
  } catch (error) {
    favorites = new Set();
  }

  function syncCompetitionHeaders() {
    competitionHeaders.forEach((header) => {
      let node = header.nextElementSibling;
      let hasVisibleRow = false;
      while (
        node &&
        !node.classList.contains("competition-subheader") &&
        !node.classList.contains("section-header") &&
        !node.classList.contains("dgrouphead")
      ) {
        if (
          (node.classList.contains("schedule-row") ||
            node.classList.contains("result-row")) &&
          node.style.display !== "none"
        ) {
          hasVisibleRow = true;
          break;
        }
        node = node.nextElementSibling;
      }
      header.style.display = hasVisibleRow ? "" : "none";
    });
  }

  function normalize(text) {
    return text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  let fuse = null;
  if (typeof Fuse !== "undefined" && rowEls.length) {
    const fuseData = rowEls.map((el, i) => ({
      i,
      text: normalize(el.dataset.search || ""),
    }));
    fuse = new Fuse(fuseData, {
      keys: ["text"],
      threshold: 0.35,
      minMatchCharLength: 2,
      ignoreLocation: true,
    });
  }

  function matchingRowIndexes(query) {
    if (fuse) {
      return new Set(fuse.search(query).map((result) => result.item.i));
    }
    const norm = normalize(query);
    return new Set(
      rowEls
        .map((el, i) =>
          normalize(el.dataset.search || "").includes(norm) ? i : -1,
        )
        .filter((i) => i >= 0),
    );
  }

  function hideSuggestions() {
    if (!suggestions) return;
    suggestions.hidden = true;
    suggestions.innerHTML = "";
    activeSuggestionIndex = -1;
    if (input) input.setAttribute("aria-expanded", "false");
  }

  function jumpToRow(row) {
    hideSuggestions();
    const link = row.querySelector('a[href^="#event-"], a.result-open');
    if (link) {
      link.click();
      return;
    }
    row.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function renderSuggestions(query, matches) {
    if (!suggestions || !query) return;
    suggestions.innerHTML = "";
    activeSuggestionIndex = -1;

    if (!matches.length) {
      const empty = document.createElement("div");
      empty.className = "search-suggestion-empty";
      empty.textContent = "Sin eventos para esa búsqueda";
      suggestions.appendChild(empty);
    } else {
      const groups = [
        ["proximos", "Próximos partidos"],
        ["resultados", "Últimos resultados"],
      ];
      groups.forEach(([key, label]) => {
        const items = matches
          .filter((row) => row.dataset.group === key)
          .slice(0, 5);
        if (!items.length) return;
        const heading = document.createElement("div");
        heading.className = "search-suggestion-group";
        heading.textContent = label;
        suggestions.appendChild(heading);
        items.forEach((row) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "search-suggestion";
          button.setAttribute("role", "option");
          button.textContent = (row.dataset.search || "Evento")
            .replace(/\s+/g, " ")
            .trim();
          button.addEventListener("click", () => jumpToRow(row));
          suggestions.appendChild(button);
        });
      });
    }

    suggestions.hidden = false;
    if (input) input.setAttribute("aria-expanded", "true");
  }

  function matchesFavorites(row) {
    if (!favoritesOnly || !favorites.size) return true;
    const keys = (row.dataset.favoriteKeys || "").split(" ").filter(Boolean);
    return keys.some((key) => favorites.has(key));
  }

  function applyVisibility() {
    rowEls.forEach((row, i) => {
      const visible =
        (!searchMatchSet || searchMatchSet.has(i)) && matchesFavorites(row);
      row.style.display = visible ? "" : "none";
    });
    featured.forEach((card) => {
      card.style.display = searchMatchSet || favoritesOnly ? "none" : "";
    });
    syncCompetitionHeaders();
  }

  function saveFavorites() {
    try {
      localStorage.setItem(
        "sports-favorites",
        JSON.stringify(Array.from(favorites)),
      );
    } catch (error) {
      return;
    }
  }

  function makeStar(key) {
    const star = document.createElement("button");
    star.type = "button";
    star.className = "fav-star";
    star.dataset.favoriteKey = key;
    star.setAttribute("aria-label", "Seguir equipo o competición");
    star.textContent = favorites.has(key) ? "★" : "☆";
    star.classList.toggle("is-favorite", favorites.has(key));
    star.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (favorites.has(key)) favorites.delete(key);
      else favorites.add(key);
      saveFavorites();
      syncFavoriteStars();
      applyVisibility();
    });
    return star;
  }

  function syncFavoriteStars() {
    document
      .querySelectorAll(".fav-star[data-favorite-key]")
      .forEach((star) => {
        const active = favorites.has(star.dataset.favoriteKey);
        star.textContent = active ? "★" : "☆";
        star.classList.toggle("is-favorite", active);
      });
    const count = document.getElementById("favorites-count");
    const pill = document.getElementById("favorites-filter");
    if (count) count.textContent = String(favorites.size);
    if (pill) {
      pill.classList.toggle("is-empty", favorites.size === 0);
      pill.disabled = favorites.size === 0 && !favoritesOnly;
    }
  }

  function injectFavoriteStars() {
    document
      .querySelectorAll(
        ".competition-tab[data-favorite-key], .competition-subheader[data-favorite-key]",
      )
      .forEach((target) => {
        const key = target.dataset.favoriteKey;
        if (!key) return;
        if (target.classList.contains("competition-tab")) {
          if (target.nextElementSibling?.classList.contains("fav-star")) return;
          target.insertAdjacentElement("afterend", makeStar(key));
          return;
        }
        if (target.querySelector(".fav-star")) return;
        target.appendChild(makeStar(key));
      });

    document.querySelectorAll(".result-team[title]").forEach((team) => {
      if (team.querySelector(".fav-star")) return;
      const key = normalize(team.getAttribute("title")).replace(/\s+/g, "-");
      team.appendChild(makeStar(key));
    });

    document
      .querySelectorAll(".schedule-row[data-favorite-keys]")
      .forEach((row) => {
        const actions = row.querySelector(".schedule-row-actions");
        if (!actions || row.querySelector(".fav-star")) return;
        const key = (row.dataset.favoriteKeys || "").split(" ")[0];
        if (key) actions.prepend(makeStar(key));
      });
  }

  const favoritesFilter = document.getElementById("favorites-filter");
  if (favoritesFilter) {
    favoritesFilter.addEventListener("click", () => {
      if (!favorites.size) return;
      favoritesOnly = !favoritesOnly;
      favoritesFilter.setAttribute("aria-pressed", String(favoritesOnly));
      applyVisibility();
    });
  }

  injectFavoriteStars();
  syncFavoriteStars();

  if (input) {
    input.addEventListener("input", function () {
      const query = input.value.trim();
      if (!query) {
        searchMatchSet = null;
        hideSuggestions();
        applyVisibility();
        return;
      }
      searchMatchSet = matchingRowIndexes(query);
      renderSuggestions(
        query,
        Array.from(searchMatchSet)
          .map((i) => rowEls[i])
          .filter(Boolean),
      );
      applyVisibility();
    });

    input.addEventListener("keydown", function (event) {
      if (!suggestions || suggestions.hidden) return;
      const options = Array.from(
        suggestions.querySelectorAll(".search-suggestion"),
      );
      if (!options.length) return;

      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        activeSuggestionIndex =
          event.key === "ArrowDown"
            ? (activeSuggestionIndex + 1) % options.length
            : (activeSuggestionIndex - 1 + options.length) % options.length;
        options.forEach((option, i) =>
          option.classList.toggle("is-active", i === activeSuggestionIndex),
        );
        options[activeSuggestionIndex].scrollIntoView({ block: "nearest" });
      } else if (event.key === "Enter" && activeSuggestionIndex >= 0) {
        event.preventDefault();
        options[activeSuggestionIndex].click();
      } else if (event.key === "Escape") {
        event.stopPropagation();
        hideSuggestions();
      }
    });

    input.addEventListener("blur", () => {
      window.setTimeout(hideSuggestions, 150);
    });
  }

  const toast = document.getElementById("app-toast");
  let toastTimer = null;

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.hidden = true;
    }, 2400);
  }

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const helper = document.createElement("textarea");
    helper.value = text;
    helper.setAttribute("readonly", "");
    helper.style.position = "fixed";
    helper.style.opacity = "0";
    document.body.appendChild(helper);
    helper.select();
    document.execCommand("copy");
    helper.remove();
  }

  document.querySelectorAll(".link-card-copy").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const href = button.dataset.copyHref;
      if (!href) return;
      try {
        await copyText(new URL(href, window.location.origin).href);
        showToast("Enlace copiado al portapapeles");
      } catch (error) {
        showToast("No se pudo copiar el enlace");
      }
    });
  });

  const reportBtn = document.getElementById("report-error-btn");
  if (reportBtn) {
    reportBtn.addEventListener("click", () =>
      showToast(
        "Cuéntanos el error y lo revisaremos en la próxima actualización",
      ),
    );
  }

  const tzSelect = document.getElementById("tz-select");
  const tzLabel = document.getElementById("tz-label");
  let selectedTimeZone = "Europe/Madrid";
  try {
    selectedTimeZone =
      localStorage.getItem("sports-timezone") || selectedTimeZone;
  } catch (error) {
    selectedTimeZone = "Europe/Madrid";
  }

  function updateLocalTimes() {
    document.querySelectorAll(".js-time[data-iso]").forEach((node) => {
      const value = new Date(node.dataset.iso);
      if (Number.isNaN(value.getTime())) return;
      node.textContent = new Intl.DateTimeFormat("es-ES", {
        day: "numeric",
        month: "long",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: selectedTimeZone,
      }).format(value);
    });
    if (tzLabel && tzSelect) {
      const option = tzSelect.options[tzSelect.selectedIndex];
      tzLabel.textContent = option
        ? option.text.toUpperCase()
        : selectedTimeZone;
      tzLabel.title = "Las horas se muestran en " + selectedTimeZone;
    }
  }

  if (tzSelect) {
    if (
      Array.from(tzSelect.options).some((o) => o.value === selectedTimeZone)
    ) {
      tzSelect.value = selectedTimeZone;
    } else {
      selectedTimeZone = tzSelect.value;
    }
    tzSelect.addEventListener("change", () => {
      selectedTimeZone = tzSelect.value;
      try {
        localStorage.setItem("sports-timezone", selectedTimeZone);
      } catch (error) {
        return;
      }
      updateLocalTimes();
    });
    updateLocalTimes();
  }

  const loadingSkeleton = document.getElementById("loading-skeleton");

  function flashSkeleton(duration) {
    if (!loadingSkeleton) return;
    loadingSkeleton.hidden = false;
    window.setTimeout(() => {
      loadingSkeleton.hidden = true;
    }, duration);
  }

  document
    .querySelectorAll(
      ".mode-tab, .sport-tab:not(#favorites-filter), .platform-tab, .competition-tab",
    )
    .forEach((link) => {
      link.addEventListener("click", (event) => {
        if (event.defaultPrevented || event.metaKey || event.ctrlKey) return;
        if (loadingSkeleton) loadingSkeleton.hidden = false;
      });
    });

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

  document.querySelectorAll(".schedule-row[data-event-id]").forEach((row) => {
    row.addEventListener("click", (e) => {
      if (e.target.closest("button, a")) return;
      const link = row.querySelector('a[href^="#event-"]');
      if (link) link.click();
    });
  });

  document.querySelectorAll(".result-row").forEach((row) => {
    row.addEventListener("click", (e) => {
      if (e.target.closest("a")) return;
      const link = row.querySelector("a.result-open");
      if (link) link.click();
    });
  });

  document.querySelectorAll("[data-event-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.eventTarget;
      history.pushState(null, "", "#" + id);
      selectEvent(id, true);
    });
  });

  const datePills = Array.from(document.querySelectorAll(".date-pill"));
  const dateStrip = document.querySelector(".date-nav-pills");

  function setActiveDate(iso) {
    datePills.forEach((pill) => {
      const active = pill.dataset.dateIso === iso;
      pill.classList.toggle("is-active", active);
      if (active) pill.setAttribute("aria-current", "date");
      else pill.removeAttribute("aria-current");
    });
  }

  function centerActiveDate(behavior = "auto") {
    const active = datePills.find((pill) =>
      pill.classList.contains("is-active"),
    );
    if (!active || !dateStrip) return;
    const stripBox = dateStrip.getBoundingClientRect();
    const pillBox = active.getBoundingClientRect();
    const left =
      dateStrip.scrollLeft +
      (pillBox.left - stripBox.left) -
      (stripBox.width - pillBox.width) / 2;
    dateStrip.scrollTo({ left: Math.max(0, left), behavior });
  }

  function syncDateUrl(iso) {
    const url = new URL(window.location.href);
    url.searchParams.set("date", iso);
    history.pushState(null, "", url);
  }

  datePills.forEach((pill) => {
    pill.addEventListener("click", () => {
      flashSkeleton(280);
      setActiveDate(pill.dataset.dateIso);
      syncDateUrl(pill.dataset.dateIso);
      centerActiveDate("smooth");
      const target = document.getElementById(pill.dataset.dateTarget);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  document.querySelectorAll(".date-nav-arrow").forEach((arrow) => {
    arrow.addEventListener("click", () => {
      if (!datePills.length) return;
      flashSkeleton(280);
      const step = Number(arrow.dataset.dateStep || 0);
      const activeIndex = datePills.findIndex((pill) =>
        pill.classList.contains("is-active"),
      );
      const visibleIndex = datePills.findIndex((pill) => {
        const target = document.getElementById(pill.dataset.dateTarget);
        if (!target) return false;
        const top = target.getBoundingClientRect().top;
        return top >= -8 && top <= 120;
      });
      const currentIndex = activeIndex >= 0 ? activeIndex : visibleIndex;
      const base =
        currentIndex < 0 ? (step > 0 ? 0 : datePills.length - 1) : currentIndex;
      const nextIndex = Math.min(
        datePills.length - 1,
        Math.max(0, base + step),
      );
      setActiveDate(datePills[nextIndex].dataset.dateIso);
      syncDateUrl(datePills[nextIndex].dataset.dateIso);
      centerActiveDate("smooth");
      const target = document.getElementById(
        datePills[nextIndex].dataset.dateTarget,
      );
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  requestAnimationFrame(() => centerActiveDate());
  window.addEventListener("resize", () => centerActiveDate());

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

  // On load: restore the shared link, or select the first row by default
  let initialId = window.location.hash.slice(1);
  const hashEl = initialId ? document.getElementById(initialId) : null;
  if (!hashEl || !hashEl.classList.contains("link-card")) {
    initialId = allRows.length ? allRows[0].dataset.eventId : null;
  }
  selectEvent(initialId, false);

  /* ──────────────────────────────────────────────────────────────────────────
   * 3. LIVE BELL DROPDOWN + AJAX POLLING
   * ────────────────────────────────────────────────────────────────────────── */
  const bellBtn = document.getElementById("live-bell-btn");
  const bellDropdown = document.getElementById("bell-dropdown");
  const bellList = document.getElementById("bell-dropdown-list");
  const bellEmpty = document.getElementById("bell-dropdown-empty");
  const bellCount = document.getElementById("live-bell-count");
  const bellCta = document.getElementById("bell-dropdown-cta");
  const bellReminderList = document.getElementById("bell-reminders-list");
  const bellReminderEmpty = document.getElementById("bell-reminders-empty");
  const bellReminderCount = document.getElementById("bell-reminders-count");
  const bellNotifyBtn = document.getElementById("bell-notify-btn");
  const bellExportBtn = document.getElementById("bell-export-btn");

  if (bellBtn && bellDropdown) {
    function updateBadge(count) {
      if (count > 0) {
        bellCount.textContent = count;
        bellCount.style.display = "flex";
        bellBtn.classList.add("live-bell--active");
        bellBtn.setAttribute(
          "aria-label",
          count + " evento(s) en directo ahora",
        );
      } else {
        bellCount.style.display = "none";
        bellBtn.classList.remove("live-bell--active");
        bellBtn.setAttribute("aria-label", "No hay eventos en directo ahora");
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

    function renderReminders(reminders) {
      if (!bellReminderList) return;
      const upcoming = (reminders || [])
        .filter((reminder) => Number(reminder.fireAt) > Date.now())
        .sort((a, b) => Number(a.fireAt) - Number(b.fireAt));
      bellReminderList.innerHTML = "";
      if (bellReminderCount)
        bellReminderCount.textContent = String(upcoming.length);
      if (bellReminderEmpty) bellReminderEmpty.hidden = upcoming.length > 0;

      upcoming.forEach((reminder) => {
        const li = document.createElement("li");
        li.className = "bell-reminder-item";
        const when = new Intl.DateTimeFormat(
          document.documentElement.lang || "es",
          {
            dateStyle: "medium",
            timeStyle: "short",
            timeZone: selectedTimeZone,
          },
        ).format(new Date(Number(reminder.fireAt)));
        li.innerHTML =
          '<span class="bell-reminder-body">' +
          '<span class="bell-reminder-title">' +
          escHtml(reminder.title || "Evento deportivo") +
          "</span>" +
          '<span class="bell-reminder-when">' +
          escHtml(when) +
          "</span>" +
          "</span>" +
          '<button type="button" class="bell-reminder-cancel" data-reminder-id="' +
          escHtml(String(reminder.id)) +
          '" aria-label="Quitar aviso de ' +
          escHtml(reminder.title || "evento") +
          '">✕</button>';
        bellReminderList.appendChild(li);
      });
    }

    function refreshReminders() {
      renderReminders(window._savedReminders || []);
      if (typeof window.getReminders === "function") window.getReminders();
    }

    function updateNotifyButton() {
      if (!bellNotifyBtn) return;
      if (!("Notification" in window)) {
        bellNotifyBtn.textContent = "Notificaciones no disponibles";
        bellNotifyBtn.disabled = true;
      } else if (Notification.permission === "granted") {
        bellNotifyBtn.textContent = "Notificaciones activas";
        bellNotifyBtn.disabled = true;
      } else if (Notification.permission === "denied") {
        bellNotifyBtn.textContent = "Notificaciones bloqueadas";
        bellNotifyBtn.disabled = true;
      } else {
        bellNotifyBtn.textContent = "Activar notificaciones";
        bellNotifyBtn.disabled = false;
      }
    }

    function icsEscape(value) {
      return String(value || "")
        .replace(/\\/g, "\\\\")
        .replace(/;/g, "\\;")
        .replace(/,/g, "\\,")
        .replace(/\r?\n/g, "\\n");
    }

    function icsDate(timestamp) {
      return new Date(timestamp)
        .toISOString()
        .replace(/[-:]/g, "")
        .replace(/\.\d{3}/, "");
    }

    function exportRemindersIcs() {
      const reminders = (window._savedReminders || []).filter(
        (reminder) => Number(reminder.fireAt) > Date.now(),
      );
      if (!reminders.length) {
        if (bellExportBtn) {
          const label = bellExportBtn.textContent;
          bellExportBtn.textContent = "Sin avisos que exportar";
          setTimeout(() => {
            bellExportBtn.textContent = label;
          }, 1800);
        }
        return;
      }

      const lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Sports Stream Platform//Avisos//ES",
        "CALSCALE:GREGORIAN",
      ];
      const stamp = icsDate(Date.now());
      reminders.forEach((reminder) => {
        const start = icsDate(Number(reminder.fireAt));
        lines.push(
          "BEGIN:VEVENT",
          "UID:reminder-" + reminder.id + "@sports-stream",
          "DTSTAMP:" + stamp,
          "DTSTART:" + start,
          "DTEND:" + icsDate(Number(reminder.fireAt) + 3600000),
          "SUMMARY:" + icsEscape(reminder.title || "Evento deportivo"),
          "DESCRIPTION:" + icsEscape(reminder.comp || "Aviso de evento"),
        );
        if (reminder.url)
          lines.push(
            "URL:" +
              icsEscape(new URL(reminder.url, window.location.href).href),
          );
        lines.push("END:VEVENT");
      });
      lines.push("END:VCALENDAR");

      const blob = new Blob([lines.join("\r\n")], {
        type: "text/calendar;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "avisos-deportivos.ics";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    function openDropdown() {
      bellDropdown.hidden = false;
      bellBtn.setAttribute("aria-expanded", "true");
      renderDropdownItems(window._liveBellEvents || []);
      renderReminders(window._savedReminders || []);
      refreshReminders();
      updateNotifyButton();
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

    document.addEventListener("remindersUpdated", (e) => {
      renderReminders((e.detail && e.detail.reminders) || []);
    });

    if (bellReminderList) {
      bellReminderList.addEventListener("click", (e) => {
        const button = e.target.closest(".bell-reminder-cancel");
        if (!button) return;
        if (typeof window.cancelReminder === "function")
          window.cancelReminder(button.dataset.reminderId);
        refreshReminders();
      });
    }

    if (bellNotifyBtn) {
      bellNotifyBtn.addEventListener("click", () => {
        if (!("Notification" in window)) return;
        Notification.requestPermission().then(updateNotifyButton);
      });
    }

    if (bellExportBtn)
      bellExportBtn.addEventListener("click", exportRemindersIcs);

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
    updateNotifyButton();
    refreshReminders();
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
      const title = btn.dataset.title || "Evento deportivo";
      const comp = btn.dataset.comp || "";
      const startIso = btn.dataset.start || "";

      if (btn.classList.contains("is-set")) {
        // Cancel reminder
        btn.classList.remove("is-set");
        btn.title = "Añadir recordatorio";
        btn.setAttribute("aria-label", "Añadir recordatorio para " + title);
        if (typeof window.cancelReminder === "function")
          window.cancelReminder(id);
      } else {
        // Schedule reminder via Service Worker
        btn.classList.add("is-set");
        btn.title = "Recordatorio activado — pulsa para cancelar";
        btn.setAttribute("aria-label", "Cancelar recordatorio para " + title);

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
   *    Enter    → activate "VER ENLACES" on focused schedule row
   * ────────────────────────────────────────────────────────────────────────── */
  document.addEventListener("keydown", function (e) {
    const tag = (document.activeElement || {}).tagName || "";
    const inInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

    // Ctrl/Cmd + K → focus search
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (input) {
        input.focus();
        input.select();
      }
      return;
    }

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
      if (inInput && input && input.value) {
        input.value = "";
        input.dispatchEvent(new Event("input"));
        input.blur();
      } else if (bellDropdown && !bellDropdown.hidden) {
        bellDropdown.hidden = true;
        if (bellBtn) {
          bellBtn.setAttribute("aria-expanded", "false");
          bellBtn.focus();
        }
      } else if (document.querySelector(".link-card.is-active")) {
        history.pushState(
          null,
          "",
          window.location.pathname + window.location.search,
        );
        selectEvent(null, false);
      } else if (inInput && input) {
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

    // Enter → activate "VER ENLACES" on selected row (when not in input)
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
