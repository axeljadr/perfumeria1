function seleccionarPresentacion(btn) {
  // Quitar activo de todos
  document
    .querySelectorAll(".btn-presentacion")
    .forEach((b) => b.classList.remove("activo"));
  btn.classList.add("activo");

  // Actualizar precio y stock
  const precio = btn.dataset.precio;
  const stock = parseInt(btn.dataset.stock);

  document.getElementById("precio-display").textContent =
    `$${parseFloat(precio).toLocaleString("es-MX", { minimumFractionDigits: 2 })}`;
  document.getElementById("stock-display").textContent =
    stock > 0 ? "En stock" : "Disponible por pedido";
}
