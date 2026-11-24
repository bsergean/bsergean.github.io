'use strict';
const header = document.querySelector('.header');
const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('#navigation');
header.classList.add('js-menu');
toggle.hidden = false;
function closeMenu() {
  toggle.setAttribute('aria-expanded', 'false');
  nav.classList.remove('open');
}
toggle.addEventListener('click', () => {
  const open = toggle.getAttribute('aria-expanded') !== 'true';
  toggle.setAttribute('aria-expanded', String(open));
  nav.classList.toggle('open', open);
});
nav.addEventListener('click', (event) => { if (event.target.closest('a')) closeMenu(); });
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
    closeMenu();
    toggle.focus();
  }
});
const filters = document.querySelector('.filters');
if (filters) {
  const events = [...document.querySelectorAll('.event')];
  const today = new Intl.DateTimeFormat('en-CA', {timeZone:'America/Los_Angeles',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  function filterEvents(category) {
    let count = 0;
    events.forEach((event) => {
      const show = event.dataset.end >= today && (category === 'all' || event.dataset.category === category);
      event.hidden = !show;
      if (show) count++;
    });
    document.querySelector('.empty').hidden = count > 0;
    document.querySelector('#event-status').textContent = `${count} rendez-vous à venir · Sélection des annonces de novembre 2026`;
  }
  filters.hidden = false;
  filters.addEventListener('click', (event) => {
    const button = event.target.closest('[data-filter]');
    if (!button) return;
    filters.querySelectorAll('button').forEach((item) => {
      const active = item === button;
      item.classList.toggle('active', active);
      item.setAttribute('aria-pressed', String(active));
    });
    filterEvents(button.dataset.filter);
  });
  filterEvents('all');
}

// Native dialog keeps gallery navigation keyboard accessible; links still work without JS.
const photoLinks = [...document.querySelectorAll('a[data-photo]')];
if (photoLinks.length) {
  const viewer = document.createElement('dialog');
  viewer.className = 'photo-viewer';
  viewer.setAttribute('aria-label', 'Visionneuse de photos');
  viewer.innerHTML = '<div class="viewer-toolbar"><p>Photos CathoSV</p><button type="button" data-close>Fermer</button></div><img class="viewer-image" alt=""><p class="viewer-caption" aria-live="polite"></p><div class="viewer-controls"><button type="button" data-previous>Précédente</button><a target="_blank" rel="noopener noreferrer" data-original>Ouvrir l’original</a><button type="button" data-next>Suivante</button></div>';
  document.body.append(viewer);
  let collection = [];
  let selected = 0;
  let opener;
  const image = viewer.querySelector('.viewer-image');
  function showPhoto(index) {
    selected = (index + collection.length) % collection.length;
    const link = collection[selected];
    image.src = link.href;
    image.alt = link.dataset.caption;
    viewer.querySelector('[data-original]').href = link.href;
    viewer.querySelector('.viewer-caption').textContent = `${link.dataset.caption} · ${selected + 1} / ${collection.length}`;
    viewer.querySelector('[data-previous]').disabled = collection.length < 2;
    viewer.querySelector('[data-next]').disabled = collection.length < 2;
  }
  photoLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = link;
      collection = [...link.closest('.photo-grid').querySelectorAll('[data-photo]')];
      showPhoto(collection.indexOf(link));
      viewer.showModal();
      viewer.querySelector('[data-close]').focus();
    });
  });
  viewer.querySelector('[data-close]').addEventListener('click', () => viewer.close());
  viewer.querySelector('[data-previous]').addEventListener('click', () => showPhoto(selected - 1));
  viewer.querySelector('[data-next]').addEventListener('click', () => showPhoto(selected + 1));
  viewer.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft') { event.preventDefault(); showPhoto(selected - 1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); showPhoto(selected + 1); }
  });
  viewer.addEventListener('click', (event) => {
    const bounds = viewer.getBoundingClientRect();
    if (event.target === viewer && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) viewer.close();
  });
  viewer.addEventListener('close', () => {
    image.removeAttribute('src');
    if (opener) opener.focus({ preventScroll: true });
  });
}

const albumPicker = document.querySelector('#album-picker');
function revealAlbum() {
  const album = document.getElementById(location.hash.slice(1));
  if (album?.matches('details.album')) {
    album.open = true;
    album.scrollIntoView({ block: 'start' });
    if (albumPicker) albumPicker.value = album.id;
  }
}
if (albumPicker) {
  albumPicker.addEventListener('change', () => {
    if (albumPicker.value) {
      location.hash = albumPicker.value;
      revealAlbum();
    }
  });
  window.addEventListener('hashchange', revealAlbum);
  revealAlbum();
}

// The original menu groups work with native details controls, with or without JS.
const navigationGroups = [...document.querySelectorAll('#navigation .nav-group')];
navigationGroups.forEach((group) => {
  group.addEventListener('toggle', () => {
    if (group.open) navigationGroups.forEach((other) => { if (other !== group) other.open = false; });
  });
});
document.addEventListener('click', (event) => {
  if (!nav.contains(event.target) && !toggle.contains(event.target)) navigationGroups.forEach((group) => { group.open = false; });
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') navigationGroups.forEach((group) => { group.open = false; });
});

// Source links and shared URLs may point inside a collapsed homepage story.
if (document.querySelector('.front-page')) {
  function revealFrontTarget() {
    if (!location.hash) return;
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    let expanded = false;
    for (let node = target; node; node = node.parentElement) {
      if (node.matches('details') && !node.open) { node.open = true; expanded = true; }
    }
    if (expanded) requestAnimationFrame(() => target.scrollIntoView({block:'start'}));
  }
  window.addEventListener('hashchange', revealFrontTarget);
  revealFrontTarget();
}
