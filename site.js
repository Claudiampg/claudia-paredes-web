/* Comportamiento común a todas las páginas */

/* El correo de contacto se edita en el panel (Ajustes generales) y llega en <body data-correo> */
const CORREO_CONTACTO = document.body.dataset.correo || '';

document.getElementById('year').textContent = new Date().getFullYear();

const navToggle = document.querySelector('.nav__toggle'), navLinks = document.querySelector('.nav__links');
navToggle.addEventListener('click', () => {
  const abierto = navLinks.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', abierto);
});
navLinks.addEventListener('click', e => { if (e.target.tagName === 'A') navLinks.classList.remove('open'); });

const revealObserver = new IntersectionObserver(
  entradas => entradas.forEach(e => e.isIntersecting && e.target.classList.add('in')),
  { threshold: .05 }
);
document.querySelectorAll('.section').forEach(s => { s.classList.add('reveal'); revealObserver.observe(s); });

/* Botones «Copiar» del kit de prensa */
document.querySelectorAll('[data-copy]').forEach(btn => btn.addEventListener('click', async () => {
  const texto = document.getElementById(btn.dataset.copy).innerText.trim();
  let copiado = false;
  try {
    await navigator.clipboard.writeText(texto);
    copiado = true;
  } catch (_) {
    const area = document.createElement('textarea');
    area.value = texto;
    document.body.appendChild(area);
    area.select();
    copiado = document.execCommand('copy');
    area.remove();
  }
  btn.textContent = copiado ? 'Copiado ✓' : 'No se pudo';
  setTimeout(() => { btn.textContent = 'Copiar'; }, 2000);
}));

/* Formularios: se envían con Netlify Forms. Si no se puede (por ejemplo, al abrir
   la web en local), se abre el correo de la persona con el mensaje ya escrito. */
function asuntoDe(form) {
  const motivo = form.querySelector('[name="motivo"]');
  const base = motivo ? motivo.value : form.dataset.asunto;
  return base + ' — ' + form.querySelector('[name="nombre"]').value.trim();
}

function construirMailto(form) {
  const lineas = [...form.querySelectorAll('input, select, textarea')]
    .map(c => ({ c, label: c.id && form.querySelector('label[for="' + c.id + '"]') }))
    .filter(({ c, label }) => label && c.value.trim())
    .map(({ c, label }) => label.textContent + ': ' + c.value.trim());
  return 'mailto:' + CORREO_CONTACTO +
    '?subject=' + encodeURIComponent(asuntoDe(form)) +
    '&body=' + encodeURIComponent(lineas.join('\n'));
}

document.querySelectorAll('.join-form').forEach(form => form.addEventListener('submit', async e => {
  e.preventDefault();
  const ok = form.querySelector('.join-form__sent--ok');
  const error = form.querySelector('.join-form__sent--error');
  const boton = form.querySelector('[type="submit"]');
  ok.hidden = error.hidden = true;
  const asunto = form.querySelector('[name="subject"]');
  if (asunto) asunto.value = asuntoDe(form);
  boton.disabled = true;
  try {
    const res = await fetch('/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(new FormData(form)).toString()
    });
    if (!res.ok) throw new Error(res.status);
    form.reset();
    ok.hidden = false;
  } catch (_) {
    error.hidden = false;
    location.href = construirMailto(form);
  } finally {
    boton.disabled = false;
  }
}));

/* Contacto: deja elegido el motivo, desde otra página (?motivo=) o desde una tarjeta */
const selectMotivo = document.getElementById('f-motivo');
if (selectMotivo) {
  const motivoInicial = new URLSearchParams(location.search).get('motivo');
  if (motivoInicial && [...selectMotivo.options].some(o => o.value === motivoInicial)) selectMotivo.value = motivoInicial;
  document.querySelectorAll('[data-motivo]').forEach(a => a.addEventListener('click', () => {
    selectMotivo.value = a.dataset.motivo;
    setTimeout(() => document.getElementById('f-nombre').focus({ preventScroll: true }), 50); // tras el salto al formulario
  }));
}
