# Agregador de retransmisiones deportivas

Te dice en qué plataforma puedes ver un evento deportivo (con
comentarios en español), si está en directo ahora mismo, cuándo es si todavía
no ha empezado, o si puedes verlo en diferido en caso de que ya haya
terminado. Si un evento pasado no tiene repetición disponible en ningún
sitio, simplemente no se muestra.

Proyecto Django pensado para ejecutarse primero en local. Más adelante (fase
2) se podrá envolver en una app de Android Studio que consuma los mismos
datos.

## Índice

1. [Reglas del proyecto](#reglas-del-proyecto)
2. [Arquitectura](#arquitectura)
3. [Instalación y ejecución en local](#instalación-y-ejecución-en-local)
4. [APIs utilizadas: cuáles puedes publicar y cuáles no](#apis-utilizadas-cuáles-puedes-publicar-y-cuáles-no)
5. [Aviso legal sobre DAZN / Movistar Plus+](#aviso-legal-sobre-dazn--movistar-plus)
6. [Subir el proyecto a GitHub](#subir-el-proyecto-a-github)
7. [Fase 2: app de Android](#fase-2-app-de-android)

## Reglas del proyecto

Implementadas en `schedule/models.py` (propiedades `Event.is_visible` y
`Event.spanish_broadcasts`):

1. Solo se listan eventos con **al menos una retransmisión en español**
   (España o Latinoamérica).
2. Si la retransmisión es en español de Latinoamérica, se muestra un
   pequeño icono junto al nombre de la plataforma (`Broadcast.language ==
   "es-LA"`).
3. Eventos **futuros o en directo** → siempre visibles, con su fecha/hora
   (sección "Próximos · calendario") o con la etiqueta "● DIRECTO".
4. Eventos **pasados** → solo visibles si existe diferido/repetición
   (`vod_available=True`) en alguna plataforma. Si no, se ocultan.

Deportes y competiciones incluidas de ejemplo: Fútbol (Champions League,
Europa League, Mundial 2026, LaLiga, Premier League, Serie A, Bundesliga,
Ligue 1), Baloncesto (NBA), Motor (F1, MotoGP), Tenis (Wimbledon) y Deportes
de invierno (esquí alpino/slalom, salto de esquí, esquí de fondo).

## Arquitectura

```
streamsync_repo/
├── manage.py
├── requirements.txt
├── .env.example          <- plantilla pública (SÍ se sube al repo)
├── .gitignore             <- aquí está excluido el .env real
├── streamsync/            <- configuración del proyecto (settings, urls)
├── templates/base.html    <- plantilla compartida (cabecera, fuentes, CSS)
├── static/css/style.css   <- toda la identidad visual
└── schedule/               <- la app principal
    ├── models.py           <- Sport, Competition, Platform, Event, Broadcast
    ├── views.py            <- vista única que agrupa directo/próximos/diferido
    ├── admin.py            <- para introducir/editar eventos a mano
    ├── templates/schedule/  <- home.html + partials (tarjeta de evento, icono LatAm)
    ├── services/            <- un adaptador por cada fuente de datos externa
    │   ├── adapters.py      <- interfaz común (BaseSourceAdapter)
    │   ├── jolpica_f1.py    <- REAL y funcional, F1, sin clave
    │   ├── api_football.py  <- esqueleto, fútbol, requiere clave privada
    │   ├── thesportsdb.py   <- esqueleto, NBA/MotoGP, clave pública de pruebas
    │   └── api_tennis.py    <- esqueleto, tenis, requiere clave privada
    └── management/commands/
        ├── seed_demo_data.py     <- datos de ejemplo (no necesita ninguna API)
        └── import_f1_calendar.py <- demuestra el adaptador de F1 funcionando de verdad
```

Cada fuente de datos (API de pago, API gratuita, o algo que tú añadas más
adelante) es un **adaptador** independiente con un único método
`fetch_events()`. Así puedes añadir o cambiar fuentes sin tocar las vistas
ni las plantillas: solo conectas el resultado del adaptador con
`Event.objects.update_or_create(...)`, tal como hace
`import_f1_calendar.py`.

## Instalación y ejecución en local

Necesitas Python 3.11+.

```bash
git clone <tu-repositorio>
cd streamsync

python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # y rellena las claves que quieras usar (opcional al principio)

python manage.py migrate
python manage.py seed_demo_data # crea deportes, plataformas y ~19 eventos de ejemplo

python manage.py runserver
```

Abre `http://127.0.0.1:8000/` y ya deberías ver la web funcionando con datos
de ejemplo, sin haber configurado ninguna API todavía.

Para entrar al panel de administración y añadir/editar eventos a mano:

```bash
python manage.py createsuperuser
```

y entra en `http://127.0.0.1:8000/admin/`.

Para probar que el sistema también funciona con una API real (no requiere
ninguna clave):

```bash
python manage.py import_f1_calendar
```

## APIs utilizadas: cuáles puedes publicar y cuáles no

DAZN y Movistar Plus+ no tienen una API pública, así que la programación se
reconstruye combinando varias APIs deportivas reales que sí son abiertas,
más lo que añadas a mano desde `/admin/`. Resumen:

| Fuente | Cubre | ¿Clave necesaria? | ¿Se puede publicar en GitHub? |
|---|---|---|---|
| **Jolpica F1** (sucesora de Ergast) | Calendario de F1 | No | ✅ Sí — no hay ninguna clave, es 100% abierta |
| **TheSportsDB** | NBA, MotoGP | Clave de pruebas pública: `3` | ✅ Sí, esa clave de pruebas es oficialmente pública y compartida. Si en el futuro pasas a una clave Patreon de pago (más peticiones, datos en directo), esa ya **no** se publica |
| **API-Football** | Champions, Europa League, Mundial, LaLiga, Premier, Serie A, Bundesliga, Ligue 1 | Clave personal (capa gratuita: 100 peticiones/día) | ❌ No — identifica tu cuenta y tu cuota. Solo en `.env` |
| **Proveedor de tenis** (a elegir, ej. api-tennis.com) | Wimbledon, ATP, WTA | Clave personal | ❌ No — solo en `.env` |
| Deportes de invierno (esquí alpino, salto, fondo) | — | — | No hay una API gratuita decente; se introducen a mano desde `/admin/` (adaptador `ManualSourceAdapter`) |

Regla general: **cualquier clave que identifique tu cuenta personal o tu
cuota de peticiones es privada** y va solo en tu `.env` real (que está en
`.gitignore` y nunca se sube). Las claves de pruebas que el propio proveedor
publica como compartidas (como el `3` de TheSportsDB) sí son seguras de
tener en el repositorio, aunque igualmente las dejamos en `.env` por
limpieza y para poder cambiarlas fácilmente.

## Aviso legal sobre DAZN / Movistar Plus+

Ninguna de las dos plataformas ofrece una API pública para consultar su
programación. La única forma de sacar esos datos directamente de sus webs
sería mediante *scraping* (leer su HTML), y eso:

- puede incumplir sus Términos de Servicio,
- se rompe cada vez que cambian el diseño de la web,
- no es algo que conviniera automatizar sin que tú decidas hacerlo y revises
  antes sus condiciones legales.

Por eso este proyecto **no** incluye un scraper de DAZN/Movistar+ listo
para usar. En su lugar:

- Usa las APIs deportivas reales de la tabla anterior para saber **qué**
  evento es y **cuándo** es.
- Tú añades manualmente, desde `/admin/`, **en qué plataforma** se puede
  ver (eso lo consultas tú mismo en sus webs/apps, como haces normalmente).
- Si en el futuro decides programar tú mismo un scraper bajo tu propia
  responsabilidad, el sitio donde encajaría en la arquitectura es
  `ManualSourceAdapter` en `schedule/services/adapters.py`.

## Subir el proyecto a GitHub

```bash
git init
git add .
git commit -m "Primera versión"
git branch -M main
git remote add origin <url-de-tu-repositorio>
git push -u origin main
```

Antes de subirlo, comprueba que `.env` (tu archivo real, con tus claves) NO
aparece en `git status`. Si aparece, revisa que `.gitignore` esté en la raíz
del proyecto.

## Fase 2: app de Android

Tal como se pidió, esta primera entrega es solo la web. Cuando llegue el
momento de la app en Android Studio, lo natural es:

1. Añadir una pequeña API REST de solo lectura encima de estos mismos
   modelos (con Django REST Framework), reutilizando toda la lógica de
   `Event.is_visible` que ya existe.
2. Consumir esa API desde la app Android con Retrofit + Kotlin, mostrando
   las mismas tres secciones (directo / próximos / diferido).

No es necesario decidir nada de esto ahora: los modelos y la lógica de
negocio ya están separados de las plantillas, así que añadir esa API más
adelante no debería requerir tocar lo que ya funciona.
