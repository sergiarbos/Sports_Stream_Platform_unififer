// Filtro de búsqueda + selección de un único evento en el panel de enlaces.
// Sin frameworks, para mantener el proyecto sencillo.
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

      // El panel de enlaces ya no es una lista (solo muestra el evento
      // seleccionado), así que la búsqueda solo necesita filtrar la
      // agenda de la izquierda.
      rows.forEach(function (row) {
        const match = !query || normalize(row.dataset.search).includes(query);
        row.style.display = match ? "" : "none";
      });

      // Mientras se busca, los destacados no aportan (no son resultado de
      // búsqueda real), así que los ocultamos para no confundir.
      featured.forEach(function (card) {
        card.style.display = query ? "none" : "";
      });
    });
  }

  // --- Panel de enlaces: muestra UN evento a la vez (patrón maestro-detalle) ---
  // Base de funcionamiento sin JS: :target en el CSS (ver style.css).
  // Con JS interceptamos el click para evitar el salto de scroll feo que
  // provoca cambiar location.hash directamente, y para resaltar también
  // la fila de la agenda que corresponde al evento mostrado.
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

  document.querySelectorAll(".get-links-btn").forEach(function (btn) {
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

  // Estado inicial: si se llega con #event-N en la URL (enlace
  // compartido), seleccionamos esa tarjeta sin animar el scroll.
  selectEvent(window.location.hash.slice(1), false);
})();
