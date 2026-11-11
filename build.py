#!/usr/bin/env python3
"""Genera la web de Claudia Paredes Guinand a partir de los textos de contenido/*.json.

Uso:  python3 build.py            -> crea la web en la carpeta _site/
      python3 build.py OTRA_CARPETA

Solo usa la biblioteca estándar de Python (sin instalar nada). Netlify lo ejecuta
cada vez que se guarda un cambio desde el panel (/admin).
"""
import html
import json
import os
import re
import shutil
import struct
import sys
import unicodedata
from urllib.parse import quote

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(RAIZ, "_site")
ESTATICOS = ["styles.css", "site.js", "talleres.js", "img", "admin"]


# ------------------------------------------------------------------ utilidades

def cargar(nombre):
    with open(os.path.join(RAIZ, "contenido", nombre + ".json"), encoding="utf-8") as f:
        return json.load(f)


def esc(texto):
    return html.escape(str(texto or ""), quote=True)


def inline(texto):
    """Texto con formato sencillo: *cursiva*, **negrita**, [enlace](url) y saltos de línea."""
    s = str(texto or "").strip()
    guardados = []

    def guardar(fragmento):
        guardados.append(fragmento)
        return "\x00%d\x00" % (len(guardados) - 1)

    # Caracteres escapados con barra (el editor los añade a veces)
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!>~|])", lambda m: guardar(html.escape(m.group(1))), s)
    s = html.escape(s, quote=False)

    def enlace(m):
        url = m.group(2).strip()
        externo = re.match(r"https?://", url) is not None
        attrs = ' target="_blank" rel="noopener"' if externo else ""
        return guardar('<a href="%s"%s>%s</a>' % (url.replace('"', "&quot;"), attrs, enfasis(m.group(1))))

    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", enlace, s)
    s = enfasis(s)
    s = re.sub(r"[ \t]*\\?\n[ \t]*", "<br>", s)
    for i, fragmento in enumerate(guardados):
        s = s.replace("\x00%d\x00" % i, fragmento)
    return s


def enfasis(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<!\w)__(.+?)__(?!\w)", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s, flags=re.S)
    s = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", s, flags=re.S)
    return s


def parrafos(texto):
    """Divide un texto largo en párrafos (separados por una línea en blanco)."""
    return [inline(p) for p in re.split(r"\n[ \t]*\n", str(texto or "").strip()) if p.strip()]


def ruta_img(ruta):
    return str(ruta or "").lstrip("/")


def medidas(ruta):
    """Ancho y alto de una imagen JPG, PNG, GIF o WebP (None si no se puede leer)."""
    try:
        with open(os.path.join(RAIZ, ruta_img(ruta)), "rb") as f:
            d = f.read()
    except OSError:
        return None
    try:
        if d[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", d[16:24])
        if d[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", d[6:10])
        if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
            tipo = d[12:16]
            if tipo == b"VP8X":
                return 1 + int.from_bytes(d[24:27], "little"), 1 + int.from_bytes(d[27:30], "little")
            if tipo == b"VP8 ":
                w, h = struct.unpack("<HH", d[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if tipo == b"VP8L":
                b = d[21:25]
                return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        if d[:2] == b"\xff\xd8":
            i = 2
            while i < len(d) - 9:
                if d[i] != 0xFF:
                    i += 1
                    continue
                marca = d[i + 1]
                if marca == 0xFF:
                    i += 1
                    continue
                if marca in (0xD8, 0x01) or 0xD0 <= marca <= 0xD7:
                    i += 2
                    continue
                largo = struct.unpack(">H", d[i + 2:i + 4])[0]
                if 0xC0 <= marca <= 0xCF and marca not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">HH", d[i + 5:i + 9])
                    return w, h
                i += 2 + largo
    except (struct.error, IndexError):
        pass
    return None


def img(ruta, alt, extra=""):
    m = medidas(ruta)
    dim = ' width="%d" height="%d"' % m if m else ""
    return '<img src="%s" alt="%s"%s%s>' % (esc(ruta_img(ruta)), esc(alt), dim, extra)


def slug(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "imagen"


def externo(url, contenido, clase=""):
    c = ' class="%s"' % clase if clase else ""
    return '<a href="%s" target="_blank" rel="noopener"%s>%s</a>' % (esc(url), c, contenido)


# ------------------------------------------------------------------ datos

AJUSTES = cargar("ajustes")
INICIO = cargar("inicio")
LIBROS = cargar("libros").get("libros", [])
OBRA = cargar("obra")
TALLERES = cargar("talleres")
PRENSA = cargar("prensa")
SOBRE = cargar("sobre")
CONTACTO = cargar("contacto")

NOMBRE = AJUSTES.get("nombre", "")
CORREO = AJUSTES.get("correo", "")
DESTACADO = next((l for l in LIBROS if l.get("destacado")), LIBROS[0] if LIBROS else None)
ANTERIORES = [l for l in LIBROS if l is not DESTACADO]
AVISO_TALLERES = bool(TALLERES.get("contenido_de_ejemplo"))


def mailto(asunto=""):
    return "mailto:%s%s" % (CORREO, "?subject=" + quote(asunto) if asunto else "")


def contacto_url(motivo):
    return "contacto.html?motivo=" + quote(motivo)


# ------------------------------------------------------------------ piezas comunes

MENU = [("sobre.html", "Sobre"), ("talleres.html", "Talleres"), ("obra.html", "Obra"),
        ("prensa.html", "Prensa"), ("contacto.html", "Contacto")]


def pagina(archivo, seo_titulo, seo_descripcion, cuerpo, scripts=("site.js",),
           imagen=None, con_talleres=False):
    inicio = archivo == "index.html"
    menu = "\n".join(
        '    <a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == archivo else "", t) for h, t in MENU)
    datos = ""
    if con_talleres:
        lista = [{"fecha": str(f.get("fecha", ""))[:10], "titulo": f.get("taller", ""), "modalidad": f.get("lugar", "")}
                 for f in TALLERES.get("fechas", []) if f.get("fecha")]
        datos = "<script>window.TALLERES = %s;</script>\n" % json.dumps(lista, ensure_ascii=False).replace("</", "<\\/")
    js = "".join('<script src="%s"></script>\n' % s for s in scripts)
    return """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{imagen}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="styles.css">
</head>
<body data-correo="{correo}">

<header class="nav">
  <a href="{marca_href}" class="nav__brand">{marca}</a>
  <button class="nav__toggle" aria-label="Abrir menú" aria-expanded="false">☰</button>
  <nav class="nav__links">
{menu}
  </nav>
</header>

<main>
{cuerpo}
</main>

<footer class="footer">
  <p>© <span id="year"></span> {nombre}</p>
</footer>

{datos}{js}</body>
</html>
""".format(titulo=esc(seo_titulo), desc=esc(seo_descripcion),
           imagen=esc(ruta_img(imagen or AJUSTES.get("imagen_compartir"))), correo=esc(CORREO),
           marca_href="#inicio" if inicio else "index.html", marca=esc(AJUSTES.get("nombre_corto", NOMBRE)),
           menu=menu, cuerpo=cuerpo.strip("\n"), nombre=esc(NOMBRE), datos=datos, js=js)


def aviso(texto):
    return '<p class="sample-note">%s</p>' % texto


def calendario():
    return """    <div class="cal-layout">
      <div class="cal" aria-label="Calendario de talleres">
        <div class="cal__head">
          <button type="button" class="cal__nav" id="cal-prev" aria-label="Mes anterior">←</button>
          <p class="cal__month" id="cal-month" aria-live="polite"></p>
          <button type="button" class="cal__nav" id="cal-next" aria-label="Mes siguiente">→</button>
        </div>
        <div class="cal__weekdays" aria-hidden="true"><span>L</span><span>M</span><span>X</span><span>J</span><span>V</span><span>S</span><span>D</span></div>
        <div class="cal__grid" id="cal-grid"></div>
      </div>
      <ul class="cal-list" id="cal-list"></ul>
    </div>"""


def lista_prensa(items):
    filas = []
    for it in items:
        fecha = (esc(it.get("fecha")) + " →") if it.get("fecha") else "→"
        filas.append("""      <li>
        {a}
          <span class="press__media">{medio}</span>
          <span class="press__title">{titulo}</span>
          <span class="press__date">{fecha}</span>
        </a>
      </li>""".format(a='<a href="%s" target="_blank" rel="noopener">' % esc(it.get("enlace")),
                      medio=esc(it.get("medio")), titulo=inline(it.get("titulo")), fecha=fecha))
    return '    <ul class="press__list">\n%s\n    </ul>' % "\n".join(filas)


def alt_portada(libro):
    return "Portada de «%s», de %s (%s)" % (libro.get("titulo", ""), NOMBRE,
                                           libro.get("editorial_corta") or libro.get("editorial", ""))


def boton_compra(libro, clase):
    if libro.get("enlace_compra"):
        return externo(libro["enlace_compra"], esc(libro.get("texto_compra") or "Comprar"), clase)
    return '<a href="%s" class="%s">Dónde conseguirlo</a>' % (esc(contacto_url("Libros")), clase)


def novela_destacada(en_inicio):
    l = DESTACADO
    if not l:
        return ""
    titulo = inline(l.get("titulo_destacado") or l.get("titulo"))
    h = "h3" if en_inicio else "h2"
    if en_inicio:
        textos = '<p class="featured__syn">%s</p>' % inline(l.get("resumen") or l.get("sinopsis"))
        campos = [("Editorial", l.get("editorial")), ("Género", l.get("genero")), ("ISBN", l.get("isbn"))]
        segundo = '<a href="obra.html#%s" class="btn btn--outline-light">Ver ficha completa</a>' % esc(l.get("ancla"))
    else:
        ps = parrafos(l.get("sinopsis"))
        textos = "\n        ".join('<p class="featured__syn%s">%s</p>' % (" featured__syn--second" if i else "", p)
                                   for i, p in enumerate(ps))
        campos = [("Editorial", l.get("editorial")), ("Año", l.get("anio")), ("ISBN", l.get("isbn"))]
        segundo = '<a href="prensa.html#kit" class="btn btn--outline-light">Kit de prensa</a>'
    meta = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (k, esc(v)) for k, v in campos if v)
    sub = '<p class="featured__sub">%s</p>' % inline(l["subtitulo"]) if l.get("subtitulo") else ""
    badge = '<p class="featured__badge">%s</p>' % esc(l["etiqueta"]) if l.get("etiqueta") else ""
    return """<div class="featured__inner">
      <div class="featured__cover">
        {img}
      </div>
      <div class="featured__text">
        {badge}
        <{h}>{titulo}</{h}>
        {sub}
        {textos}
        <dl class="featured__meta">{meta}</dl>
        <div class="featured__cta">
          {compra}
          {segundo}
        </div>
      </div>
    </div>""".format(img=img(l.get("portada"), alt_portada(l)), badge=badge, h=h, titulo=titulo, sub=sub,
                     textos=textos, meta=meta, compra=boton_compra(l, "btn btn--light"), segundo=segundo)


def eyebrow_libro(l):
    return " · ".join(esc(x) for x in (l.get("editorial_corta") or l.get("editorial"), l.get("ciudad"), l.get("anio")) if x)


# ------------------------------------------------------------------ páginas

def pagina_inicio():
    i = INICIO
    novedad = '\n      <p class="hero__new"><span>Novedad</span> %s</p>' % inline(i["novedad"]) if i.get("novedad") else ""
    anteriores = "\n".join("""        <article class="prev-book">
          <div class="cover cover--img">
            {img}
          </div>
          <div class="prev-book__info">
            <p class="eyebrow">{eyebrow}</p>
            <h4>{titulo}</h4>
            <p>{resumen}</p>
            <a href="obra.html#{ancla}" class="prev-book__link">Ver ficha →</a>
          </div>
        </article>""".format(img=img(l.get("portada"), alt_portada(l), ' loading="lazy"'), eyebrow=eyebrow_libro(l),
                             titulo=esc(l.get("titulo")), resumen=inline(l.get("resumen") or l.get("sinopsis")),
                             ancla=esc(l.get("ancla"))) for l in ANTERIORES)
    cuerpo = """  <!-- PRESENTACIÓN -->
  <section id="inicio" class="hero">
    <div class="hero__text">
      <p class="eyebrow">{antetitulo}</p>
      <h1>{titulo}</h1>
      <p class="hero__lead">{presentacion}</p>
      <p class="hero__more"><a href="sobre.html">Conoce su historia →</a></p>{novedad}
      <div class="hero__cta">
        <a href="#talleres" class="btn">Próximos talleres</a>
        <a href="#novela" class="btn btn--ghost">Descubrir la novela</a>
      </div>
    </div>
    <div class="hero__photo">
      {foto}
    </div>
  </section>

  <!-- PRÓXIMOS TALLERES -->
  <section id="talleres" class="section upcoming">
    <h2 class="section__title"><span>01</span> Próximos talleres</h2>
    {aviso}
{calendario}
    <div class="upcoming__cta">
      <a href="talleres.html" class="btn">Ver todos los talleres</a>
    </div>
  </section>

  <!-- OBRA -->
  <section id="obra" class="obra">
    <div class="obra__head">
      <h2 class="section__title"><span>02</span> Obra</h2>
    </div>

    <div id="novela" class="featured">
    {destacada}
    </div>

    <div class="section obra__prev">
      <h3 class="obra__subtitle">Obras anteriores</h3>
      <div class="prev-grid">
{anteriores}
      </div>
      <div class="obra__cta"><a href="obra.html" class="btn">Ver toda la obra</a></div>
    </div>
  </section>

  <!-- PRENSA -->
  <section id="prensa" class="section press">
    <h2 class="section__title"><span>03</span> Prensa</h2>
{prensa}
    <div class="obra__cta"><a href="prensa.html" class="btn">Ver toda la prensa</a></div>
  </section>

  <!-- CONTACTO -->
  <section id="contacto" class="section contact">
    <h2 class="section__title"><span>04</span> Contacto</h2>
    <p class="contact__lead">{contacto}</p>
    <a href="contacto.html" class="btn">Escríbenos</a>
    <div class="contact__social">
      {instagram}
    </div>
  </section>""".format(
        antetitulo=esc(i.get("antetitulo")), titulo=inline(i.get("titulo")), presentacion=inline(i.get("presentacion")),
        novedad=novedad, foto=img(i.get("foto"), i.get("foto_alt")),
        aviso=aviso("Fechas de ejemplo, pendientes de confirmar") if AVISO_TALLERES else "",
        calendario=calendario(), destacada=novela_destacada(True), anteriores=anteriores,
        prensa=lista_prensa(i.get("prensa", [])), contacto=inline(i.get("contacto_texto")),
        instagram=externo(AJUSTES.get("instagram_url"), "Instagram · " + esc(AJUSTES.get("instagram_usuario"))))
    return pagina("index.html", i.get("seo_titulo"), i.get("seo_descripcion"), cuerpo,
                  scripts=("talleres.js", "site.js"), con_talleres=True)


def campo(pre, id_, etiqueta, control):
    return '        <label for="%s-%s">%s</label>\n        %s' % (pre, id_, etiqueta, control)


def formulario(id_, nombre_netlify, asunto, clase, titulo_tag, titulo, entrada, campos, boton, boton_clase, sent_extra):
    """Formulario que llega por Netlify Forms; si no está disponible, abre el correo."""
    lead = '\n        <p class="join-form__lead">%s</p>' % inline(entrada) if entrada else ""
    return """      <form id="{id}" name="{nombre}" class="{clase}" data-asunto="{asunto}" method="POST" data-netlify="true" netlify-honeypot="bot-field">
        <input type="hidden" name="form-name" value="{nombre}">
        <input type="hidden" name="subject" value="{asunto}">
        <p class="visually-hidden" aria-hidden="true"><label>No rellenar <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>
        <{tt}>{titulo}</{tt}>{lead}
{campos}
        <button type="submit" class="{boton_clase}">{boton}</button>
        <p class="join-form__hint">Te responderemos lo antes posible.</p>
        <p class="join-form__sent join-form__sent--ok" role="status" hidden>¡Gracias! Hemos recibido tu mensaje y te responderemos pronto.</p>
        <p class="join-form__sent join-form__sent--error" role="status" hidden>No se ha podido enviar desde la web, así que se ha abierto tu correo con el mensaje ya escrito. Si no se abre, escribe a <a href="{mailto}">{correo}</a>{extra}.</p>
      </form>""".format(id=id_, nombre=nombre_netlify, clase=clase, asunto=esc(asunto), tt=titulo_tag, titulo=titulo,
                        lead=lead, campos="\n".join(campos), boton_clase=boton_clase, boton=boton,
                        mailto=esc(mailto()), correo=esc(CORREO), extra=sent_extra)


def pagina_talleres():
    t = TALLERES
    tarjetas = "\n".join("""      <article class="tcard">
        <h3>{titulo}</h3>
        <p>{desc}</p>
        {meta}
        <div class="tcard__links">
          <a href="#fechas">Ver fechas →</a>
          <a href="#contratar" data-taller="{titulo}">Llevarlo a mi espacio →</a>
        </div>
      </article>""".format(titulo=esc(c.get("titulo")), desc=inline(c.get("descripcion")),
                           meta='<p class="tcard__meta">%s</p>' % esc(c["modalidad"]) if c.get("modalidad") else "")
                         for c in t.get("catalogo", []))
    pasos = "\n".join("""        <li>
          <h3>{titulo}</h3>
          <p>{texto}</p>
        </li>""".format(titulo=esc(p.get("titulo")), texto=inline(p.get("texto"))) for p in t.get("metodologia", []))
    opciones_taller = "".join('<option value="{0}">{0}</option>'.format(esc(c.get("titulo"))) for c in t.get("catalogo", []))
    asistir = formulario(
        "asistir", "taller-asistir", "Quiero asistir a un taller", "join-form", "h3", "Quiero asistir",
        t.get("asistir_texto"),
        [campo("a", "nombre", "Nombre", '<input id="a-nombre" name="nombre" type="text" autocomplete="name" required>'),
         campo("a", "email", "Correo electrónico", '<input id="a-email" name="email" type="email" autocomplete="email" required>'),
         campo("a", "fecha", "Fecha", '<select id="a-fecha" name="fecha" required>\n          <option value="">Elige una fecha</option>\n          <option value="Avísame de nuevas fechas">Avísame de nuevas fechas</option>\n        </select>'),
         campo("a", "mensaje", "Mensaje (opcional)", '<textarea id="a-mensaje" name="mensaje" rows="3"></textarea>')],
        "Enviar solicitud", "btn", "")
    contratar = formulario(
        "contratar", "taller-propuesta", "Quiero llevar un taller a mi espacio", "join-form join-form--dark", "h3",
        "Llévalo a tu espacio", t.get("contratar_texto"),
        [campo("c", "nombre", "Nombre", '<input id="c-nombre" name="nombre" type="text" autocomplete="name" required>'),
         campo("c", "espacio", "Librería o entidad", '<input id="c-espacio" name="espacio" type="text" autocomplete="organization" required>'),
         campo("c", "ciudad", "Ciudad", '<input id="c-ciudad" name="ciudad" type="text" autocomplete="address-level2" required>'),
         campo("c", "email", "Correo electrónico", '<input id="c-email" name="email" type="email" autocomplete="email" required>'),
         campo("c", "taller", "Taller de interés", '<select id="c-taller" name="taller">\n          <option value="Aún no lo sé">Aún no lo sé</option>' + opciones_taller + '\n        </select>'),
         campo("c", "mensaje", "Fechas, tamaño del grupo u otros detalles (opcional)", '<textarea id="c-mensaje" name="mensaje" rows="3"></textarea>')],
        "Pedir propuesta", "btn btn--light", "")
    cuerpo = """  <!-- CABECERA -->
  <section class="page-hero">
    <p class="eyebrow">{antetitulo}</p>
    <h1>{titulo}</h1>
    <p class="page-hero__lead">{entrada}</p>
    <div class="page-hero__cta">
      <a href="#asistir" class="btn">Quiero asistir</a>
      <a href="#contratar" class="btn btn--ghost">Llevarlo a mi librería</a>
    </div>
    {aviso}
  </section>

  <!-- FECHAS -->
  <section id="fechas" class="section upcoming">
    <h2 class="section__title">Próximas fechas</h2>
{calendario}
  </section>

  <!-- TODOS LOS TALLERES -->
  <section id="catalogo" class="section catalog">
    <h2 class="section__title">Todos los talleres</h2>
    <div class="catalog__grid">
{tarjetas}
    </div>
  </section>

  <!-- METODOLOGÍA -->
  <section id="metodologia" class="method">
    <div class="method__inner">
      <h2 class="section__title">Metodología</h2>
      <p class="method__lead">{metodo}</p>
      <ol class="method__steps">
{pasos}
      </ol>
    </div>
  </section>

  <!-- PARTICIPAR -->
  <section id="participar" class="section join">
    <h2 class="section__title">Participa</h2>
    <div class="join__grid">

{asistir}

{contratar}

    </div>
  </section>""".format(
        antetitulo=esc(t.get("antetitulo")), titulo=inline(t.get("titulo")), entrada=inline(t.get("entrada")),
        aviso=aviso("Contenido de ejemplo: talleres, fechas y metodología pendientes de confirmar") if AVISO_TALLERES else "",
        calendario=calendario(), tarjetas=tarjetas, metodo=inline(t.get("metodologia_entrada")), pasos=pasos,
        asistir=asistir, contratar=contratar)
    return pagina("talleres.html", t.get("seo_titulo"), t.get("seo_descripcion"), cuerpo,
                  scripts=("talleres.js", "site.js"), con_talleres=True)


def pagina_obra():
    o = OBRA
    estante = "\n".join('      <li><a href="#%s"><span>%s</span><em>%s</em></a></li>' % (
        esc(l.get("ancla")), esc(l.get("anio")), esc(l.get("titulo"))) for l in LIBROS)
    libros = []
    for n, l in enumerate(ANTERIORES):
        sinopsis = "\n        ".join("<p>%s</p>" % p for p in parrafos(l.get("sinopsis")))
        nota = '\n        <p class="book__note">%s</p>' % inline(l["nota"]) if l.get("nota") else ""
        temas = ('\n        <div class="tags">%s</div>' % "".join("<span>%s</span>" % esc(x) for x in l["temas"])) if l.get("temas") else ""
        sub = '\n        <p class="book__subtitle">%s</p>' % inline(l["subtitulo"]) if l.get("subtitulo") else ""
        libros.append("""    <article id="{ancla}" class="book{rev}">
      <div class="book__cover cover cover--img">
        {img}
      </div>
      <div class="book__info">
        <p class="eyebrow">{eyebrow}</p>
        <h3>{titulo}</h3>{sub}
        {sinopsis}{nota}{temas}
        {compra}
      </div>
    </article>""".format(ancla=esc(l.get("ancla")), rev=" book--reverse" if n % 2 else "",
                         img=img(l.get("portada"), alt_portada(l), ' loading="lazy"'), eyebrow=eyebrow_libro(l),
                         titulo=esc(l.get("titulo")), sub=sub, sinopsis=sinopsis, nota=nota, temas=temas,
                         compra=boton_compra(l, "btn btn--ghost")))
    otros = "\n".join("""      <div>
        <dt>{0}</dt>
        <dd>{1}</dd>
      </div>""".format(esc(x.get("tipo")), inline(x.get("detalle"))) for x in o.get("otros", []))
    cita = ""
    if o.get("cita"):
        cita = """
  <!-- CITA -->
  <section class="quote">
    <blockquote>
      {0}
      <cite>{1}</cite>
    </blockquote>
  </section>
""".format(inline(o["cita"]), inline(o.get("cita_fuente")))
    seccion_anteriores = """
  <!-- OBRAS ANTERIORES -->
  <section class="section works">
    <h2 class="section__title">Obras anteriores</h2>

{0}
  </section>
""".format("\n\n".join(libros)) if libros else ""
    seccion_otros = """
  <!-- OTROS TEXTOS -->
  <section class="section also">
    <h2 class="section__title">{0}</h2>
    <dl class="also__list">
{1}
    </dl>
  </section>
""".format(esc(o.get("otros_titulo")), otros) if o.get("otros") else ""
    cuerpo = """  <!-- CABECERA -->
  <section class="page-hero page-hero--obra">
    <p class="eyebrow">{antetitulo}</p>
    <h1>{titulo}</h1>
    <ol class="shelf">
{estante}
    </ol>
  </section>

  <!-- NOVELA -->
  <section id="{ancla}" class="featured">
    {destacada}
  </section>
{cita}{anteriores}{otros}
  <!-- INVITAR -->
  <section class="invite">
    <h2>{invitacion}</h2>
    <a href="{invitar}" class="btn btn--light">Escríbenos</a>
  </section>""".format(
        antetitulo=esc(o.get("antetitulo")), titulo=inline(o.get("titulo")), estante=estante,
        ancla=esc(DESTACADO.get("ancla") if DESTACADO else "novela"), destacada=novela_destacada(False),
        cita=cita, anteriores=seccion_anteriores, otros=seccion_otros, invitacion=inline(o.get("invitacion")),
        invitar=esc(contacto_url("Presentación o club de lectura")))
    return pagina("obra.html", o.get("seo_titulo"), o.get("seo_descripcion"), cuerpo,
                  imagen=DESTACADO.get("portada") if DESTACADO else None)


def pagina_prensa():
    p = PRENSA
    criticas = "\n".join("""      <article class="critic{main}">
        <p class="critic__media">{medio}</p>
        <p class="critic__meta">{detalle}</p>
        <h3>{titulo}</h3>
        <p>{texto}</p>
        {enlace}
      </article>""".format(main=" critic--main" if c.get("principal") else "", medio=esc(c.get("medio")),
                           detalle=esc(c.get("detalle")), titulo=inline(c.get("titulo")), texto=inline(c.get("texto")),
                           enlace=externo(c["enlace"], esc(c.get("texto_enlace") or "Leer →")) if c.get("enlace") else "")
                         for c in p.get("criticas", []))
    opiniones = []
    for o in p.get("opiniones", []):
        cita = "\n        <blockquote>%s</blockquote>" % inline(o["texto"]) if o.get("texto") else ""
        sobre = " " + inline(o["sobre"]) if o.get("sobre") else ""
        enlace = " · " + externo(o["enlace"], "Leer →") if o.get("enlace") else ""
        opiniones.append("""      <figure class="blurb">{cita}
        <figcaption><b>{autor}</b>{sobre}{enlace}</figcaption>
      </figure>""".format(cita=cita, autor=esc(o.get("autor")), sobre=sobre, enlace=enlace))
    destacada = ""
    if p.get("cita_destacada"):
        destacada = """    <figure class="blurb-main">
      <blockquote>{0}</blockquote>
      <figcaption>{1}</figcaption>
    </figure>
""".format(inline(p["cita_destacada"]), inline(p.get("cita_destacada_autor")))

    def bio(id_, texto):
        ps = parrafos(texto)
        if len(ps) == 1:
            return '<p id="%s">%s</p>' % (id_, ps[0])
        return '<div id="%s">\n          %s\n        </div>' % (id_, "\n          ".join("<p>%s</p>" % x for x in ps))

    descargas = []
    for d in p.get("descargas", []):
        ruta = ruta_img(d.get("imagen"))
        ext = os.path.splitext(ruta)[1].lower() or ".jpg"
        m = medidas(ruta)
        meta = ext[1:].upper().replace("JPEG", "JPG") + (" · %d × %d" % m if m else "") + " ↓"
        descargas.append("""      <li>
        <a href="{ruta}" download="{nombre_archivo}">
          {img}
          <span class="downloads__name">{nombre}</span>
          <span class="downloads__meta">{meta}</span>
        </a>
      </li>""".format(ruta=esc(ruta), nombre_archivo=esc(slug(NOMBRE) + "-" + slug(d.get("nombre", "")) + ext),
                      img=img(ruta, "", ' loading="lazy"'), nombre=esc(d.get("nombre")), meta=meta))
    cuerpo = """  <!-- CABECERA -->
  <section class="page-hero">
    <p class="eyebrow">{antetitulo}</p>
    <h1>{titulo}</h1>
    <p class="page-hero__lead">{entrada}</p>
    <div class="page-hero__cta">
      <a href="#kit" class="btn">Kit de prensa</a>
      <a href="{entrevista}" class="btn btn--ghost">Solicitar entrevista</a>
    </div>
    <ul class="press-jump">
      <li><a href="#critica">Crítica</a></li>
      <li><a href="#opiniones">Lo que dicen</a></li>
      <li><a href="#entrevistas">Entrevistas</a></li>
      <li><a href="#apariciones">Opinión y apariciones</a></li>
      <li><a href="#kit">Kit de prensa</a></li>
    </ul>
  </section>

  <!-- CRÍTICA -->
  <section id="critica" class="section critics">
    <h2 class="section__title">Crítica</h2>
    <div class="critics__grid">
{criticas}
    </div>
  </section>

  <!-- LO QUE DICEN -->
  <section id="opiniones" class="section blurbs">
    <h2 class="section__title">Lo que dicen de sus libros</h2>
{destacada}    <div class="blurbs__grid">
{opiniones}
    </div>
  </section>

  <!-- ENTREVISTAS -->
  <section id="entrevistas" class="section press">
    <h2 class="section__title">Entrevistas</h2>
{entrevistas}
  </section>

  <!-- OPINIÓN Y APARICIONES -->
  <section id="apariciones" class="section press">
    <h2 class="section__title">Opinión y apariciones</h2>
{apariciones}
  </section>

  <!-- KIT DE PRENSA -->
  <section id="kit" class="section kit">
    <h2 class="section__title">Kit de prensa</h2>

    <h3 class="kit__subtitle">Biografía</h3>
    <div class="bios">
      <article class="bio-card">
        <div class="bio-card__head">
          <h4>Versión corta</h4>
          <button type="button" class="copy-btn" data-copy="bio-corta">Copiar</button>
        </div>
        {bio_corta}
      </article>
      <article class="bio-card">
        <div class="bio-card__head">
          <h4>Versión larga</h4>
          <button type="button" class="copy-btn" data-copy="bio-larga">Copiar</button>
        </div>
        {bio_larga}
      </article>
    </div>

    <h3 class="kit__subtitle">Imágenes para descargar</h3>
    <ul class="downloads">
{descargas}
    </ul>
  </section>

  <!-- CONTACTO DE PRENSA -->
  <section class="invite">
    <h2>{invitacion}</h2>
    <a href="{contacto}" class="btn btn--light">Escríbenos</a>
  </section>""".format(
        antetitulo=esc(p.get("antetitulo")), titulo=inline(p.get("titulo")), entrada=inline(p.get("entrada")),
        entrevista=esc(mailto("Solicitud de entrevista")), criticas=criticas, destacada=destacada,
        opiniones="\n".join(opiniones), entrevistas=lista_prensa(p.get("entrevistas", [])),
        apariciones=lista_prensa(p.get("apariciones", [])), bio_corta=bio("bio-corta", p.get("bio_corta")),
        bio_larga=bio("bio-larga", p.get("bio_larga")), descargas="\n".join(descargas),
        invitacion=inline(p.get("invitacion")), contacto=esc(contacto_url("Prensa")))
    return pagina("prensa.html", p.get("seo_titulo"), p.get("seo_descripcion"), cuerpo)


def pagina_sobre():
    s = SOBRE
    historia = parrafos(s.get("historia"))
    historia_html = "\n        ".join('<p%s>%s</p>' % (' class="dropcap"' if n == 0 else "", x) for n, x in enumerate(historia))
    datos = "\n".join('        <li><span>%s</span>%s</li>' % (esc(d.get("etiqueta")), inline(d.get("valor"))) for d in s.get("datos", []))
    recorrido = s.get("recorrido", [])
    hitos = "\n".join('      <li%s><span class="timeline__when">%s</span><p>%s</p></li>' % (
        ' class="timeline__now"' if n == len(recorrido) - 1 else "", esc(r.get("cuando")), inline(r.get("texto")))
        for n, r in enumerate(recorrido))
    temas = "".join("<span>%s</span>" % esc(t) for t in s.get("temas", []))
    formacion = "\n".join("        <li>%s</li>" % inline(f) for f in s.get("formacion", []))
    cita = ""
    if s.get("cita"):
        cita = """
  <!-- CITA -->
  <section class="quote">
    <blockquote>
      {0}
      <cite>{1}</cite>
    </blockquote>
  </section>
""".format(inline(s["cita"]), inline(s.get("cita_fuente")))
    cuerpo = """  <!-- CABECERA -->
  <section class="page-hero about-hero">
    <div>
      <p class="eyebrow">{antetitulo}</p>
      <h1>{titulo}</h1>
      <p class="page-hero__lead">{entrada}</p>
    </div>
    <div class="hero__photo">
      {foto}
    </div>
  </section>

  <!-- SU HISTORIA -->
  <section id="historia" class="section story">
    <h2 class="section__title">Su historia</h2>
    <div class="about__grid">
      <div class="about__body">
        {historia}
      </div>
      <ul class="facts">
{datos}
      </ul>
    </div>
  </section>
{cita}
  <!-- RECORRIDO -->
  <section id="recorrido" class="section journey">
    <h2 class="section__title">Recorrido</h2>
    <ol class="timeline">
{hitos}
    </ol>
  </section>

  <!-- SU ESCRITURA -->
  <section id="escritura" class="section writing">
    <h2 class="section__title">Su escritura</h2>
    <div class="writing__grid">
      <div>
        <p class="writing__lead">{frase}</p>
        <p>{texto}</p>
      </div>
      <div>
        <h3 class="writing__label">Temas que recorren su obra</h3>
        <div class="tags tags--large">{temas}</div>
      </div>
    </div>
    <div class="writing__edu">
      <h3 class="writing__label">Formación y docencia</h3>
      <ul>
{formacion}
      </ul>
    </div>
  </section>

  <!-- SIGUE -->
  <section class="next-links">
    <a href="obra.html"><span>Leer</span>Su obra →</a>
    <a href="talleres.html"><span>Escribir</span>Sus talleres →</a>
    <a href="prensa.html"><span>Conocer más</span>Prensa →</a>
  </section>""".format(
        antetitulo=esc(s.get("antetitulo")), titulo=inline(s.get("titulo")), entrada=inline(s.get("entrada")),
        foto=img(s.get("foto"), s.get("foto_alt")), historia=historia_html, datos=datos, cita=cita, hitos=hitos,
        frase=inline(s.get("escritura_frase")), texto=inline(s.get("escritura_texto")), temas=temas, formacion=formacion)
    return pagina("sobre.html", s.get("seo_titulo"), s.get("seo_descripcion"), cuerpo, imagen=s.get("foto"))


def pagina_contacto():
    c = CONTACTO
    motivos = c.get("motivos", [])
    tarjetas = []
    for m in motivos:
        extra = '\n        <a href="%s" class="reason__alt">%s</a>' % (esc(m["enlace"]), esc(m.get("enlace_texto") or "Ver más")) if m.get("enlace") else ""
        tarjetas.append("""      <article class="reason">
        <h2>{titulo}</h2>
        <p>{texto}</p>
        <a href="#formulario" data-motivo="{motivo}">Escribir →</a>{extra}
      </article>""".format(titulo=esc(m.get("titulo")), texto=inline(m.get("texto")),
                           motivo=esc(m.get("motivo") or m.get("titulo")), extra=extra))
    opciones = "\n".join("          <option>%s</option>" % esc(m.get("motivo") or m.get("titulo")) for m in motivos)
    form = formulario(
        "formulario", "contacto", "Contacto desde la web", "join-form", "h2", "Envía un mensaje", "",
        [campo("f", "nombre", "Nombre", '<input id="f-nombre" name="nombre" type="text" autocomplete="name" required>'),
         campo("f", "email", "Correo electrónico", '<input id="f-email" name="email" type="email" autocomplete="email" required>'),
         campo("f", "motivo", "Motivo", '<select id="f-motivo" name="motivo" required>\n          <option value="">Elige un motivo</option>\n%s\n          <option>Otro</option>\n        </select>' % opciones),
         campo("f", "mensaje", "Mensaje", '<textarea id="f-mensaje" name="mensaje" rows="5" required></textarea>')],
        "Enviar mensaje", "btn", "")
    editoriales = "\n".join("            <li>%s <span>%s</span></li>" % (
        externo(e["enlace"], esc(e.get("nombre"))) if e.get("enlace") else esc(e.get("nombre")), esc(e.get("libro")))
        for e in c.get("editoriales", []))
    nota_correo = '\n          <p class="sample-note">Dirección provisional, pendiente de confirmar</p>' if AJUSTES.get("correo_provisional") else ""
    cuerpo = """  <!-- CABECERA -->
  <section class="page-hero">
    <p class="eyebrow">{antetitulo}</p>
    <h1>{titulo}</h1>
    <p class="page-hero__lead">{entrada}</p>
  </section>

  <!-- MOTIVOS -->
  <section class="section reasons" aria-label="Motivos de contacto">
    <div class="reasons__grid">
{tarjetas}
    </div>
  </section>

  <!-- FORMULARIO Y DATOS -->
  <section class="section contact-main">
    <div class="contact-main__grid">
{form}

      <aside class="contact-side">
        <h2 class="visually-hidden">Otras formas de contacto</h2>
        <div class="contact-side__block">
          <h3>Correo</h3>{nota}
          <a class="contact-side__mail" href="{mailto}">{correo}</a>
        </div>
        <div class="contact-side__block">
          <h3>Redes</h3>
          {instagram}
        </div>
        <div class="contact-side__block">
          <h3>Editoriales</h3>
          <ul>
{editoriales}
          </ul>
        </div>
      </aside>
    </div>
  </section>""".format(
        antetitulo=esc(c.get("antetitulo")), titulo=inline(c.get("titulo")), entrada=inline(c.get("entrada")),
        tarjetas="\n".join(tarjetas), form=form, nota=nota_correo, mailto=esc(mailto()), correo=esc(CORREO),
        instagram=externo(AJUSTES.get("instagram_url"), "Instagram · " + esc(AJUSTES.get("instagram_usuario"))),
        editoriales=editoriales)
    return pagina("contacto.html", c.get("seo_titulo"), c.get("seo_descripcion"), cuerpo)


# ------------------------------------------------------------------ generar

def main():
    os.makedirs(SALIDA, exist_ok=True)
    for nombre in os.listdir(SALIDA):  # vacía la carpeta sin borrarla
        ruta = os.path.join(SALIDA, nombre)
        shutil.rmtree(ruta) if os.path.isdir(ruta) and not os.path.islink(ruta) else os.remove(ruta)
    for nombre in ESTATICOS:
        origen = os.path.join(RAIZ, nombre)
        if os.path.isdir(origen):
            shutil.copytree(origen, os.path.join(SALIDA, nombre))
        elif os.path.exists(origen):
            shutil.copy2(origen, SALIDA)
    paginas = {
        "index.html": pagina_inicio, "talleres.html": pagina_talleres, "obra.html": pagina_obra,
        "prensa.html": pagina_prensa, "sobre.html": pagina_sobre, "contacto.html": pagina_contacto,
    }
    for archivo, generar in paginas.items():
        with open(os.path.join(SALIDA, archivo), "w", encoding="utf-8") as f:
            f.write(generar())
    print("Web generada en %s (%d páginas)" % (SALIDA, len(paginas)))


if __name__ == "__main__":
    main()
