function initVistaRapida(opciones) {
  const overlay = document.getElementById('vrOverlay');
  const cuerpo = document.getElementById('vrCuerpo');
  const cerrar = document.getElementById('vrCerrar');
  const cache = {};
  let ultimoFoco = null;

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
  const dinero = (n) => '$' + Number(n).toLocaleString('es-MX', {
    minimumFractionDigits: 2, maximumFractionDigits: 2
  });

  function nivel(n) {
    let h = '';
    for (let i = 1; i <= 5; i++) h += `<span class="vr-punto ${i <= n ? 'on' : ''}"></span>`;
    return h;
  }

  function tags(lista) {
  return lista.map((t) => {
    const estilo = [
      t.color ? `background-color:${esc(t.color)}` : '',
      t.color_texto ? `color:${esc(t.color_texto)}` : '',
      t.color_borde ? `--borde:${esc(t.color_borde)}` : ''
    ].filter(Boolean).join(';');
    return `<span class="vr-tag" style="${estilo}">${esc(t.nombre)}</span>`;
  }).join(''); 
 } 

  function pintar(p) {
    const pres = p.presentaciones;
    cuerpo.innerHTML = `
      <div class="vr-foto">
        ${p.foto ? `<img src="${esc(p.foto)}" alt="${esc(p.nombre)}">`
                 : '<div class="vr-sin-foto">Sin imagen</div>'}
      </div>
      <div class="vr-info">
        <span class="vr-marca">${esc(p.marca)}</span>
        <h2 class="vr-nombre" id="vrNombre">${esc(p.nombre)}</h2>
        <span class="vr-genero">${esc(p.genero)}${p.familia ? ' · ' + esc(p.familia) : ''}</span>

        ${pres.length ? `
          <div class="vr-precio" id="vrPrecio"></div>
          <div class="vr-estado" id="vrEstado"></div>
          <div class="vr-etiqueta">Tamaño</div>
          <div class="vr-chips" id="vrChips">
            ${pres.map((x, i) => `
              <button type="button" class="vr-chip ${i === 0 ? 'activo' : ''}" data-i="${i}">
                ${esc(x.ml)} ml
              </button>`).join('')}
          </div>` : '<div class="vr-estado">Sin presentaciones disponibles</div>'}

        <div class="vr-perfil">
          ${p.longevidad.nivel ? `<div><span>Longevidad</span><span class="vr-puntos">${nivel(p.longevidad.nivel)}</span></div>` : ''}
          ${p.estela.nivel ? `<div><span>Estela</span><span class="vr-puntos">${nivel(p.estela.nivel)}</span></div>` : ''}
          ${p.uso ? `<div><span>Uso</span><strong>${esc(p.uso)}</strong></div>` : ''}
        </div>

        ${p.acordes.length ? `<div class="vr-etiqueta">Acordes principales</div><div class="vr-tags-grid">${tags(p.acordes)}</div>` : ''}
        ${p.notas.length ? `<div class="vr-etiqueta">Notas</div><div class="vr-tags-grid">${tags(p.notas)}</div>` : ''}
        ${p.descripcion ? `<p class="vr-desc">${esc(p.descripcion)}</p>` : ''}

        <a class="vr-boton" href="${esc(p.url)}">Ver detalle completo</a>
      </div>`;

    if (!pres.length) return;
    const precio = document.getElementById('vrPrecio');
    const estado = document.getElementById('vrEstado');

    function seleccionar(i) {
      const x = pres[i];
      precio.textContent = dinero(x.precio);
      estado.textContent = `${x.tipo} · ${x.disponible ? 'Disponible' : 'Por pedido'}`;
      estado.classList.toggle('pedido', !x.disponible);
      cuerpo.querySelectorAll('.vr-chip').forEach((c) =>
        c.classList.toggle('activo', Number(c.dataset.i) === i));
    }
    cuerpo.querySelector('#vrChips').addEventListener('click', (e) => {
      const b = e.target.closest('.vr-chip');
      if (b) seleccionar(Number(b.dataset.i));
    });
    seleccionar(0);
  }

  async function abrir(id) {
    ultimoFoco = document.activeElement;
    cuerpo.innerHTML = '<div class="vr-cargando">Cargando…</div>';
    overlay.classList.add('abierto');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    cerrar.focus();

    try {
      if (!cache[id]) {
        const r = await fetch(opciones.urlBase.replace('__ID__', id));
        if (!r.ok) throw new Error(r.status);
        cache[id] = await r.json();
      }
      pintar(cache[id]);
    } catch (err) {
      cuerpo.innerHTML = '<div class="vr-cargando">No se pudo cargar el perfume.</div>';
      console.error('Vista rápida:', err);
    }
  }

  function cerrarModal() {
    overlay.classList.remove('abierto');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (ultimoFoco) ultimoFoco.focus();
  }

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-vista-rapida');
    if (btn) { e.preventDefault(); abrir(btn.dataset.id); }
  });
  cerrar.addEventListener('click', cerrarModal);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) cerrarModal(); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay.classList.contains('abierto')) cerrarModal();
  });
}