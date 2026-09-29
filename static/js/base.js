
const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');
const navOverlay = document.getElementById('navOverlay');
function openMenu() {
    navToggle.classList.add('active');
    navLinks.classList.add('open');
    navOverlay.classList.add('active');
    navToggle.setAttribute('aria-expanded', 'true');
    navToggle.setAttribute('aria-label', 'Cerrar menú');
    document.body.classList.add('menu-open');
}
function closeMenu() {
    navToggle.classList.remove('active');
    navLinks.classList.remove('open');
    navOverlay.classList.remove('active');
    navToggle.setAttribute('aria-expanded', 'false');
    navToggle.setAttribute('aria-label', 'Abrir menú');
    document.body.classList.remove('menu-open');
}
function toggleMenu() {
    if (navLinks.classList.contains('open')) {
        closeMenu();
    } else {
        openMenu();
    }
}
navToggle.addEventListener('click', toggleMenu);
navOverlay.addEventListener('click', closeMenu);
document.querySelectorAll('.nav-links a').forEach(function (link) {
    link.addEventListener('click', closeMenu);
});
document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
        closeMenu();
    }
});
window.addEventListener('resize', function () {
    if (window.innerWidth > 992) {
        closeMenu();
    }
});