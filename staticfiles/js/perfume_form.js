// ============================================================
// BUSCADOR CON CREACIÓN AUTOMÁTICA
// Uso: initBuscador(config)
// ============================================================

function initBuscador(config) {
    const {
        inputId,       // id del input de texto visible
        urlBuscar,     // endpoint GET ?q=
        urlCrear,      // endpoint POST nombre=
        hiddenId,      // id del hidden input (para ForeignKey)
        tagsId,        // id del contenedor de tags (para M2M)
        tipo,          // 'fk' | 'm2m'
        csrfToken
    } = config;

    const input      = document.getElementById(inputId);
    const dropdown   = document.createElement('ul');
    dropdown.className = 'buscador-dropdown';
    input.parentNode.appendChild(dropdown);

    let seleccionados = {}; // { id: nombre } para M2M

    // ── Inicializar tags ya seleccionados (modo editar) ──────
    if (tipo === 'm2m' && tagsId) {
        const tagsContainer = document.getElementById(tagsId);
        tagsContainer.querySelectorAll('[data-id]').forEach(tag => {
            seleccionados[tag.dataset.id] = tag.dataset.nombre;
        });
    }

    // ── Mostrar dropdown ─────────────────────────────────────
    function mostrarDropdown(items, query) {
        dropdown.innerHTML = '';
        if (items.length === 0 && query) {
            const li = document.createElement('li');
            li.className = 'buscador-crear';
            li.textContent = `Crear "${query}"`;
            li.addEventListener('click', () => crearItem(query));
            dropdown.appendChild(li);
        } else {
            items.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item.nombre;
                li.addEventListener('click', () => seleccionar(item));
                dropdown.appendChild(li);
            });
            if (query) {
                const li = document.createElement('li');
                li.className = 'buscador-crear';
                li.textContent = `Crear "${query}"`;
                li.addEventListener('click', () => crearItem(query));
                dropdown.appendChild(li);
            }
        }
        dropdown.style.display = dropdown.children.length ? 'block' : 'none';
    }

    // ── Buscar ───────────────────────────────────────────────
    let timer;
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const q = input.value.trim();
        if (!q) { dropdown.style.display = 'none'; return; }
        timer = setTimeout(() => {
            fetch(`${urlBuscar}?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(data => mostrarDropdown(data, q));
        }, 250);
    });

    // ── Enter para crear si no hay coincidencia exacta ───────
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const q = input.value.trim();
            if (!q) return;
            crearItem(q);
        }
    });

    // ── Seleccionar existente ────────────────────────────────
    function seleccionar(item) {
        if (tipo === 'fk') {
            document.getElementById(hiddenId).value = item.id;
            input.value = item.nombre;
        } else {
            agregarTag(item);
        }
        dropdown.style.display = 'none';
        input.value = tipo === 'm2m' ? '' : input.value;
    }

    // ── Crear nuevo ──────────────────────────────────────────
    function crearItem(nombre) {
        const formData = new FormData();
        formData.append('nombre', nombre);
        formData.append('csrfmiddlewaretoken', csrfToken);
        fetch(urlCrear, { method: 'POST', body: formData })
            .then(r => r.json())
            .then(item => {
                seleccionar(item);
                dropdown.style.display = 'none';
            });
    }

    // ── Tags para M2M ────────────────────────────────────────
    function agregarTag(item) {
        if (seleccionados[item.id]) return; // ya está
        seleccionados[item.id] = item.nombre;

        const tagsContainer = document.getElementById(tagsId);
        const tag = document.createElement('span');
        tag.className = 'tag-seleccionado';
        tag.dataset.id = item.id;
        tag.dataset.nombre = item.nombre;
        tag.innerHTML = `${item.nombre} <button type="button" data-id="${item.id}">×</button>`;
        tag.querySelector('button').addEventListener('click', () => {
            delete seleccionados[item.id];
            tag.remove();
            actualizarHiddens(tagsContainer.dataset.name);
        });
        tagsContainer.appendChild(tag);
        actualizarHiddens(tagsContainer.dataset.name);
    }

    function actualizarHiddens(fieldName) {
        // Elimina hiddens anteriores de este campo
        document.querySelectorAll(`input[data-field="${fieldName}"]`).forEach(el => el.remove());
        Object.keys(seleccionados).forEach(id => {
            const hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.name = fieldName;
            hidden.value = id;
            hidden.dataset.field = fieldName;
            document.querySelector('form').appendChild(hidden);
        });
    }

    // ── Cerrar dropdown al hacer click fuera ─────────────────
    document.addEventListener('click', e => {
        if (!input.parentNode.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}