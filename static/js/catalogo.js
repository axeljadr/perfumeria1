// Contar filtros activos
function contarFiltrosActivos() {
    const params = new URLSearchParams(window.location.search);
    let count = 0;
    for (let [key, value] of params) {
        if (key !== 'page' && value && value.trim() !== '') {
            count++;
        }
    }
    return count;
}
// Actualizar badge
function actualizarBadge() {
    const badge = document.getElementById('badgeFiltros');
    const count = contarFiltrosActivos();
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-block';
    } else {
        badge.textContent = '0';
        badge.style.display = 'none';
    }
}
// Toggle filtros
function toggleFiltros() {
    const wrapper = document.getElementById('filtrosWrapper');
    const btn = document.querySelector('.toggle-filtros-btn');
    const text = document.getElementById('toggle-text');
    const icon = document.getElementById('toggle-icon');
    
    wrapper.classList.toggle('abierto');
    
    if (wrapper.classList.contains('abierto')) {
        text.textContent = 'Ocultar filtros';
        icon.classList.add('rotado');
        btn.setAttribute('aria-expanded', 'true');
    } else {
        text.textContent = 'Mostrar filtros';
        icon.classList.remove('rotado');
        btn.setAttribute('aria-expanded', 'false');
    }
}
// Eliminar filtro específico
function eliminarFiltro(nombre) {
    const url = new URL(window.location.href);
    if (nombre === 'acorde') {
        url.searchParams.delete('acorde');
    } else {
        url.searchParams.delete(nombre);
    }
    window.location.href = url.toString();
}
// Abrir filtros automáticamente si hay filtros activos
document.addEventListener('DOMContentLoaded', function() {
    const tieneFiltros = contarFiltrosActivos() > 0;
    actualizarBadge();
    
    if (tieneFiltros) {
        const wrapper = document.getElementById('filtrosWrapper');
        const btn = document.querySelector('.toggle-filtros-btn');
        const text = document.getElementById('toggle-text');
        const icon = document.getElementById('toggle-icon');
        
        wrapper.classList.add('abierto');
        text.textContent = 'Ocultar filtros';
        icon.classList.add('rotado');
        btn.setAttribute('aria-expanded', 'true');
    }
});