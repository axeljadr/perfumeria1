function initBuscadorPerfumes(contenedor, opciones) {
  opciones = opciones || {};
  const modoSeleccion = typeof opciones.onSelect === 'function';
  const input = contenedor.querySelector('.pf-input');
  const dropdown = contenedor.querySelector('.pf-dropdown');
  let timer = null;

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
  const dinero = (n) => '$' + Number(n).toLocaleString('es-MX', {
    minimumFractionDigits: 2, maximumFractionDigits: 2
  });

  function chips(lista, perfume, titulo) {
    if (!lista.length) return '';
    const html = lista.map((p) => {
      const clase = `pf-opcion ${p.stock <= 0 ? 'agotado' : ''}`;
      const cuerpo = `<span class="ml">${esc(p.ml)} ml</span>
                      <span class="precio">${dinero(p.precio)}</span>`;
      return modoSeleccion
        ? `<button type="button" class="${clase}" data-perfume="${perfume.id}" data-pres="${p.id}">${cuerpo}</button>`
        : `<span class="${clase}">${cuerpo}</span>`;
    }).join('');
    return `<div class="pf-grupo"><span class="pf-grupo-titulo">${titulo}</span>${html}</div>`;
  }

  function fila(p) {
    const foto = p.foto
      ? `<img class="pf-foto" src="${esc(p.foto)}" alt="${esc(p.nombre)}" loading="lazy">`
      : '<div class="pf-foto vacia">Sin foto</div>';

    const precios = p.desde != null ? `
      <div class="pf-precio-linea">
        ${p.precio_original && p.precio_original > p.desde
          ? `<span class="pf-tachado">${dinero(p.precio_original)}</span>` : ''}
        <span class="pf-desde">Desde <strong>${dinero(p.desde)}</strong></span>
      </div>` : '';

    const info = `
      <div class="pf-info">
        <div class="pf-marca">${esc(p.marca)}</div>
        <div class="pf-nombre">${esc(p.nombre)}</div>
        ${precios}
        ${chips(p.decants, p, 'Decants')}
        ${chips(p.originales, p, 'Original')}
      </div>`;

    return modoSeleccion
      ? `<div class="pf-item">${foto}${info}</div>`
      : `<a class="pf-item" href="${esc(p.url)}">${foto}${info}</a>`;
  }

  function render(resultados) {
    dropdown._datos = resultados;
    dropdown.innerHTML = resultados.length
      ? resultados.map(fila).join('')
      : '<div class="pf-vacio">Sin resultados</div>';
    dropdown.classList.add('abierto');
  }

  async function buscar() {
    const q = input.value.trim();
    try {
      const resp = await fetch(`${opciones.url}?q=${encodeURIComponent(q)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      if (!resp.ok) throw new Error(resp.status);
      render((await resp.json()).resultados);
    } catch (err) {
      dropdown.innerHTML = '<div class="pf-vacio">No se pudo buscar. Revisa que estés con sesión iniciada.</div>';
      dropdown.classList.add('abierto');
      console.error('Buscador de perfumes:', err);
    }
  }

  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(buscar, 250);
  });
  input.addEventListener('focus', buscar);

  if (modoSeleccion) {
    dropdown.addEventListener('mousedown', (e) => {
      const btn = e.target.closest('.pf-opcion');
      if (!btn) return;
      e.preventDefault();
      const perfume = dropdown._datos.find((p) => p.id == btn.dataset.perfume);
      const pres = [...perfume.originales, ...perfume.decants]
        .find((x) => x.id == btn.dataset.pres);
      input.value = `${perfume.marca} ${perfume.nombre} · ${pres.ml} ml`;
      dropdown.classList.remove('abierto');
      opciones.onSelect(perfume, pres);
    });
  }

  document.addEventListener('click', (e) => {
    if (!contenedor.contains(e.target)) dropdown.classList.remove('abierto');
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') dropdown.classList.remove('abierto');
  });
}