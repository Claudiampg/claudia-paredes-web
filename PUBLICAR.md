# Cómo publicar la web y activar el panel

La web se genera a partir de los textos de la carpeta `contenido/`. Claudia los edita desde un panel en `tudominio.com/admin` y, cada vez que guarda, Netlify vuelve a generar la web y la publica en uno o dos minutos.

## Qué hay en esta carpeta

| Carpeta o fichero | Para qué sirve |
|---|---|
| `contenido/` | Todos los textos, listas y fotos de la web, en ficheros JSON. Es lo que edita el panel. |
| `img/` | Fotos y portadas. Lo que Claudia suba desde el panel se guarda aquí. |
| `admin/` | El panel de edición (Decap CMS). Sus formularios se definen en `admin/config.yml`. |
| `build.py` | Genera las páginas HTML a partir de `contenido/`. Solo usa Python, no hay que instalar nada. |
| `styles.css`, `site.js`, `talleres.js` | Diseño y comportamiento de la web. |
| `netlify.toml` | Le indica a Netlify cómo generar la web. |
| `_site/` | La web generada. No se edita a mano y no se sube a GitHub. |

**Ver la web en el ordenador:** ejecuta `python3 build.py` en esta carpeta y abre `_site/index.html`.

## Publicar por primera vez (una sola vez, unos 30 minutos)

Lo ideal es crear las cuentas a nombre de Claudia, con su correo, para que la web sea suya desde el principio.

### 1. GitHub: guardar el código

1. Crea una cuenta gratuita en https://github.com.
2. Crea un repositorio nuevo:
   - Botón **New repository**.
   - Nombre: `claudia-paredes-web`.
   - Visibilidad: **Private**.
3. Antes de subir nada, abre `admin/config.yml` y cambia la línea `repo:` por `Claudiampg/claudia-paredes-web` (ya hecho).
4. En la página del repositorio, pulsa **uploading an existing file** y arrastra todo el contenido de esta carpeta, excepto `_site`.
5. Pulsa **Commit changes**.

### 2. Netlify: publicar la web

1. Crea una cuenta gratuita en https://www.netlify.com, entrando con la cuenta de GitHub.
2. Pulsa **Add new project → Import an existing project → GitHub** y elige `claudia-paredes-web`.
3. No cambies nada en la configuración, porque se lee de `netlify.toml`. Pulsa **Deploy**.
4. En uno o dos minutos la web estará en una dirección del tipo `https://nombre.netlify.app`.
   - Puedes cambiar el nombre en **Project configuration → Change project name**.

### 3. Activar el acceso al panel

El panel guarda los cambios en GitHub, así que hay que autorizarlo una vez.

1. En GitHub, ve a **Settings → Developer settings → OAuth Apps → New OAuth App** y rellena:
   - **Application name:** Panel web Claudia
   - **Homepage URL:** la dirección de la web (`https://nombre.netlify.app` o el dominio propio)
   - **Authorization callback URL:** `https://api.netlify.com/auth/done`
2. Pulsa **Register application**, después **Generate a new client secret**, y copia el *Client ID* y el *Client secret*.
3. En Netlify, ve a **Project configuration → Access & security → OAuth → Install a provider**.
4. Elige **GitHub** y pega el *Client ID* y el *Client secret*.

Desde ese momento se entra al panel en `https://nombre.netlify.app/admin` con **Login with GitHub**.

- Si el repositorio está en la cuenta de otra persona, invita a Claudia en GitHub: **Settings → Collaborators → Add people**.

### 4. Recibir los formularios en el correo

Los tres formularios de la web (contacto, «Quiero asistir» y «Llévalo a tu espacio») se envían con Netlify Forms. El plan gratuito incluye 100 envíos al mes.

1. En Netlify, abre **Forms** y pulsa **Enable form detection**.
2. Vuelve a publicar: **Deploys → Trigger deploy → Deploy project**.
   - Después aparecerán los formularios `contacto`, `taller-asistir` y `taller-propuesta`.
3. En **Forms → Form notifications → Add notification → Email notification**, pon el correo de Claudia para recibir cada mensaje.
   - El asunto del correo indica el motivo y el nombre de quien escribe.

### 5. Dominio propio: claudiaparedesguinand.com (DonDominio)

Se mantienen los DNS de DonDominio y solo se añaden dos registros, así no se toca nada del correo.

1. En Netlify, ve a **Domain management → Add a domain**, escribe `claudiaparedesguinand.com` y confirma. Cuando ofrezca usar Netlify DNS, elige la opción de **configurar DNS externo**.
2. En DonDominio, entra en **Dominios → claudiaparedesguinand.com → Zona DNS** (Gestión DNS) y:
   - Borra los registros `A` y `CNAME` de `@` y `www` que haya por defecto (los de aparcamiento). **No borres** los `MX` ni los `TXT` del correo.
   - Añade un registro **A**: nombre `@` (o vacío), valor `75.2.60.5`.
   - Añade un registro **CNAME**: nombre `www`, valor `nombre-del-proyecto.netlify.app`.
3. Espera entre unos minutos y unas horas. Netlify comprobará el dominio y activará el HTTPS solo (**Domain management → HTTPS → Verify DNS configuration** si tarda).
4. Actualiza la *Homepage URL* de la OAuth App de GitHub a `https://claudiaparedesguinand.com`.

### 6. Antes de dárselo a Claudia

Desde el propio panel, con estos cambios ya no hace falta tocar código:

- **Ajustes generales:**
  - Pon el correo real.
  - Desactiva «dirección provisional».
- **Talleres:**
  - Pon los talleres y las fechas reales.
  - Desactiva «contenido de ejemplo».
- **Libros:**
  - Añade los enlaces de compra.
  - Revisa las sinopsis.

## Mantenimiento

- **Historial:** cada cambio del panel queda guardado en GitHub con fecha. Si algo se rompe, se puede volver a una versión anterior desde el historial del repositorio o desde **Deploys** en Netlify (**Publish deploy** sobre una versión anterior).
- **Si una publicación falla:** el registro está en **Deploys** de Netlify. La web anterior sigue en línea hasta que una nueva se genere bien.
- **Cambios de diseño:** `styles.css`. Para la estructura de las páginas, `build.py`.
- **Nuevos campos para el panel:** hay que añadirlos en `admin/config.yml`, en el JSON de `contenido/` y en `build.py`.
