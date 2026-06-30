// Search filter + single-event selection in the links panel.
// No frameworks, keeping the project simple.
(function () {
  const input = document.getElementById("event-search");
  const rows = document.querySelectorAll(".schedule-row[data-search]");
  const featured = document.querySelectorAll(".featured-card");

  function normalize(text) {
    return text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  if (input) {
    input.addEventListener("input", function () {
      const query = normalize(input.value.trim());

      // The links panel is no longer a list (it only shows the selected
      // event), so the search only needs to filter the left-hand schedule.
      rows.forEach(function (row) {
        const match = !query || normalize(row.dataset.search).includes(query);
        row.style.display = match ? "" : "none";
      });

      // While searching, featured cards don't help (they are not real
      // search results), so we hide them to avoid confusion.
      featured.forEach(function (card) {
        card.style.display = query ? "none" : "";
      });
    });
  }

  // --- Links panel: shows ONE event at a time (master-detail pattern) ---
  // Base behaviour without JS: :target in the CSS (see style.css).
  // With JS we intercept the click to avoid the jarring scroll jump that
  // changing location.hash directly causes, and to also highlight the
  // corresponding schedule row for the event being shown.
  const linksCol = document.querySelector(".links-col");
  const allLinkCards = document.querySelectorAll(".link-card");
  const allRows = document.querySelectorAll(".schedule-row[data-event-id]");

  function selectEvent(id, scrollIntoView) {
    allLinkCards.forEach(function (card) {
      card.classList.toggle("is-active", card.id === id);
    });
    allRows.forEach(function (row) {
      row.classList.toggle("is-selected", row.dataset.eventId === id);
    });
    if (scrollIntoView && id) {
      const card = document.getElementById(id);
      if (card) card.scrollIntoView({ behavior: "smooth", block: "nearest" });
      if (linksCol) linksCol.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  document.querySelectorAll('a[href^="#event-"]').forEach(function (btn) {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      const id = this.getAttribute("href").slice(1);
      history.pushState(null, "", "#" + id);
      selectEvent(id, true);
    });
  });

  document.querySelectorAll(".link-card-close").forEach(function (btn) {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      history.pushState(null, "", window.location.pathname + window.location.search);
      selectEvent(null, false);
    });
  });

  window.addEventListener("popstate", function () {
    selectEvent(window.location.hash.slice(1), false);
  });

  // Initial state: if the page is loaded with #event-N in the URL (shared
  // link), select that card without animating the scroll.
  selectEvent(window.location.hash.slice(1), false);
})();
