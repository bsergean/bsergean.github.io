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
