/* ============ DATOS DE LOS TALLERES ============
   Las fechas se editan en el panel (Talleres → Próximas fechas) y llegan en window.TALLERES.
   Los talleres ya pasados desaparecen solos. */
const TALLERES = window.TALLERES || [];
const escHTML = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ============ FECHAS ============ */
const parseFecha = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
const hoy = (() => { const n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); })();
const proximos = TALLERES
  .map(t => ({ ...t, date: parseFecha(t.fecha) }))
  .filter(t => t.date >= hoy)
  .sort((a, b) => a.date - b.date);
const fechaLarga = d => d.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });

/* ============ CALENDARIO ============ */
(function () {
  const grid = document.getElementById('cal-grid');
  const list = document.getElementById('cal-list');
  if (!grid || !list) return;
  const label = document.getElementById('cal-month');
  const prev = document.getElementById('cal-prev');
  const next = document.getElementById('cal-next');

  const monthIndex = d => d.getFullYear() * 12 + d.getMonth();
  const minMonth = monthIndex(hoy);
  const maxMonth = proximos.length ? monthIndex(proximos[proximos.length - 1].date) : minMonth;
  let current = proximos.length ? monthIndex(proximos[0].date) : minMonth;

  function highlight(fecha) {
    list.querySelectorAll('.cal-item').forEach(el => el.classList.toggle('is-active', el.dataset.fecha === fecha));
    grid.querySelectorAll('.cal__day--event').forEach(el => el.classList.toggle('is-active', el.dataset.fecha === fecha));
  }

  function renderMonth() {
    const year = Math.floor(current / 12), month = current % 12;
    const name = new Date(year, month, 1).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' });
    label.textContent = name.charAt(0).toUpperCase() + name.slice(1);
    prev.disabled = current <= minMonth;
    next.disabled = current >= maxMonth;
    grid.innerHTML = '';

    const offset = (new Date(year, month, 1).getDay() + 6) % 7; // la semana empieza en lunes
    for (let i = 0; i < offset; i++) grid.appendChild(document.createElement('span'));

    const days = new Date(year, month + 1, 0).getDate();
    for (let d = 1; d <= days; d++) {
      const date = new Date(year, month, d);
      const event = proximos.find(t => t.date.getTime() === date.getTime());
      const cell = document.createElement(event ? 'button' : 'span');
      cell.textContent = d;
      cell.className = 'cal__day';
      if (date.getTime() === hoy.getTime()) cell.classList.add('is-today');
      if (date < hoy) cell.classList.add('is-past');
      if (event) {
        cell.type = 'button';
        cell.classList.add('cal__day--event');
        cell.dataset.fecha = event.fecha;
        cell.setAttribute('aria-label', d + ': ' + event.titulo);
        cell.addEventListener('click', () => highlight(event.fecha));
      }
      grid.appendChild(cell);
    }
  }

  function renderList() {
    if (!proximos.length) {
      list.innerHTML = '<li class="cal-empty">Pronto anunciaremos nuevas fechas.</li>';
      return;
    }
    proximos.forEach(t => {
      const li = document.createElement('li');
      li.className = 'cal-item';
      li.dataset.fecha = t.fecha;
      const day = t.date.toLocaleDateString('es-ES', { day: 'numeric' });
      const mon = t.date.toLocaleDateString('es-ES', { month: 'short' }).replace('.', '');
      li.innerHTML =
        '<time class="cal-item__date" datetime="' + t.fecha + '"><b>' + day + '</b>' + mon + '</time>' +
        '<div class="cal-item__body"><h3>' + escHTML(t.titulo) + '</h3><p>' + escHTML(t.modalidad) + '</p></div>' +
        '<a class="cal-item__cta" href="talleres.html?fecha=' + t.fecha + '#asistir">Apuntarme →</a>';
      li.addEventListener('mouseenter', () => {
        current = monthIndex(t.date);
        renderMonth();
        highlight(t.fecha);
      });
      list.appendChild(li);
    });
  }

  prev.addEventListener('click', () => { current--; renderMonth(); });
  next.addEventListener('click', () => { current++; renderMonth(); });
  renderList();
  renderMonth();
})();

/* ============ FORMULARIOS (solo en talleres.html) ============ */
(function () {
  const selectFecha = document.getElementById('a-fecha');
  if (!selectFecha) return;

  proximos.forEach(t => {
    const o = document.createElement('option');
    o.value = t.titulo + ' · ' + fechaLarga(t.date);
    o.dataset.fecha = t.fecha;
    o.textContent = fechaLarga(t.date) + ' · ' + t.titulo;
    selectFecha.insertBefore(o, selectFecha.lastElementChild);
  });

  // Viene de un «Apuntarme»: deja elegida esa fecha
  const elegirFecha = fecha => {
    const o = [...selectFecha.options].find(x => x.dataset.fecha === fecha);
    if (o) selectFecha.value = o.value;
  };
  const inicial = new URLSearchParams(location.search).get('fecha');
  if (inicial) elegirFecha(inicial);

  // En esta misma página, «Apuntarme» no recarga
  document.getElementById('cal-list').addEventListener('click', e => {
    const a = e.target.closest('.cal-item__cta');
    if (!a) return;
    e.preventDefault();
    elegirFecha(a.closest('.cal-item').dataset.fecha);
    document.getElementById('asistir').scrollIntoView();
    document.getElementById('a-nombre').focus({ preventScroll: true });
  });

  // «Llevarlo a mi espacio» desde una ficha: deja elegido ese taller
  document.querySelectorAll('[data-taller]').forEach(a => a.addEventListener('click', () => {
    document.getElementById('c-taller').value = a.dataset.taller;
  }));
})();
