/* Comportamiento común a todas las páginas */

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

/* Formularios: se envían con Web3Forms (web3forms.com), que los reenvía al correo de Claudia.
   El correo no aparece en la web. */
function asuntoDe(form) {
  const motivo = form.querySelector('[name="motivo"]');
  const base = motivo ? motivo.value : form.dataset.asunto;
  return base + ' — ' + form.querySelector('[name="nombre"]').value.trim();
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
    const res = await fetch(form.action, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
      body: new FormData(form)
    });
    const datos = await res.json().catch(() => ({}));
    if (!res.ok || datos.success === false) throw new Error(res.status);
    form.reset();
    ok.hidden = false;
  } catch (_) {
    error.hidden = false;
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
