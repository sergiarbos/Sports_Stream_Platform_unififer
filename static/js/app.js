// StreamSync — filtro de búsqueda en cliente.
// Filtra a la vez las filas de la agenda (izquierda) y las tarjetas
// del panel de enlaces (derecha) por equipo/piloto/competición.
// No depende de ningún framework para mantener el proyecto sencillo.
(function () {
  const input = document.getElementById("event-search");
  if (!input) return;

  const rows = document.querySelectorAll(".schedule-row[data-search]");
  const cards = document.querySelectorAll(".link-card[data-search]");
  const featured = document.querySelectorAll(".featured-card");

  function normalize(text) {
    return text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  input.addEventListener("input", function () {
    const query = normalize(input.value.trim());

    rows.forEach(function (row) {
      const match = !query || normalize(row.dataset.search).includes(query);
      row.style.display = match ? "" : "none";
    });

    cards.forEach(function (card) {
      const match = !query || normalize(card.dataset.search).includes(query);
      card.style.display = match ? "" : "none";
    });

    // Mientras se busca, los destacados no aportan (no son resultado de
    // búsqueda real), así que los ocultamos para no confundir.
    featured.forEach(function (card) {
      card.style.display = query ? "none" : "";
    });
  });
})();
