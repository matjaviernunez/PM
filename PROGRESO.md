# Polla Mundialista 2026 — Estado del Proyecto
**Última actualización:** 9 junio 2026  
**Deploy:** https://huzerpro.pythonanywhere.com  
**Repo:** https://github.com/matjaviernunez/PM

---

## Resumen ejecutivo

| Estado | Cantidad |
|--------|----------|
| ✅ Completado | 22 |
| 🔴 Crítico (antes 11 jun) | 3 |
| ⚪ Nice-to-have | 0 |

El torneo arranca el **11 de junio de 2026**. Quedan 3 tareas críticas de lógica de eliminatorias que deben estar listas antes de esa fecha.

---

## Stack técnico

- **Backend:** Python 3 + Flask + Flask-Login
- **DB:** SQLite con `sqlite3.Row` (sin ORM)
- **Deploy:** PythonAnywhere (free tier)
- **Frontend:** Mobile-first CSS vanilla + JS vanilla
- **Fuentes:** Bebas Neue + Oswald (Google Fonts)
- **Flags:** flagcdn.com (ISO 2-letter codes)
- **Flujo deploy:** `git push` → `git pull` en PythonAnywhere → Reload

---

## Blueprints / estructura

```
app.py
├── auth_bp        → /auth/          (login, register, perfil)
├── pred_bp        → /predicciones/  (lista partidos, guardar preds)
├── ranking_bp     → /ranking/       (tabla, stats, el más botado)
├── hub_bp         → /mundial/       (links, música, goleadores, tarjetas)
└── admin_bp       → /admin/         (panel completo)
```

---

## Tareas completadas ✅

### B1 — Fundamentos
- [x] Estructura de carpetas + `config.py`
- [x] Schema SQLite + script de inicialización (`init_db.py`)
- [x] `equipos.json` con los 48 equipos reales, grupos A–L e ISO codes

### B2 — Autenticación
- [x] Registro con perfil completo (edad, equipo favorito, jugador favorito, campeón favorito, ligas)
- [x] Login / Logout con Flask-Login + UserMixin
- [x] **Perfil editable** — el usuario puede modificar sus datos y unirse a nuevas ligas

### B3 — Predicciones
- [x] Vista por grupos (filtros A–L) con pills → **migrado a selects**
- [x] Vista por días (Todos / Sig. día / 2 días / 3 días) → **select**
- [x] Filtro por estado (Todos / Pendientes / Guardados)
- [x] Guardado y edición de predicciones en DB vía fetch/AJAX
- [x] **Countdown** al inicio del Mundial (11 jun 21:00 UTC) con Bebas Neue
- [x] **Banner de Zayu** (jaguar México) como header de la página
- [x] Fondo difuminado de Zayu en toda la pantalla (opacidad 4.5%)

### B4 — Scoring
- [x] Motor `calcular_puntos()` — resultado exacto (3 pts), solo ganador (1 pt)
- [x] Recálculo automático al cargar resultado (`recalcular_partido`)
- [x] Scraper de resultados ESPN (runner manual desde admin)
- [x] Tabla `puntajes_fase` por jugador y fase

### B6 — Hub informativo
- [x] Links a FIFA, Sofascore, ESPN, Flashscore, OneFootball, Google Noticias
- [x] **Sección de música** con links a YouTube/Spotify (La Copa de la Vida, Waka Waka, etc.)
- [x] Cuentas X/Twitter clave del torneo
- [x] Tabla de goleadores (cargada desde admin)
- [x] Tabla de tarjetas amarillas/rojas (cargada desde admin)
- [x] Fondo difuminado de Maple (alce Canadá) en toda la pantalla

### B7 — Ranking
- [x] Tabla de posiciones con medallas 🥇🥈🥉
- [x] Desglose de puntos por fase (barras de colores)
- [x] Filtro por liga → **migrado a select**
- [x] **Tarjeta "El Más Botado" 🥄** — último lugar con cuchara de palo
- [x] Visualización campeón favorito (barras + banderas)
- [x] Visualización marcadores más predichos
- [x] **Banner de Clutch** (águila USA) como header + fondo difuminado
- [x] Fuente Bebas Neue en puntos grandes y header

### B8 — Panel Admin
- [x] Lista de partidos pendientes y completados
- [x] Partidos **colapsables** (click para expandir → inputs + guardar)
- [x] Filtros de partidos: grupo + días → **selects** + estado → pills
- [x] Abrir/cerrar partidos individualmente
- [x] Cargar resultado → recálculo automático de puntos
- [x] Ver predicciones por partido
- [x] Ver predicciones completas por usuario + borrar individual
- [x] Filtro de usuarios por liga y nombre
- [x] **Gestión de ligas por usuario** — botón 🏆 Ligas abre panel con checkboxes
- [x] Gestión de goleadores (agregar, editar, borrar)
- [x] Gestión de tarjetas amarillas/rojas
- [x] Crear ligas nuevas
- [x] Eliminar usuarios
- [x] Scrape manual de resultados ESPN

### B9 — Diseño polish
- [x] **Bebas Neue + Oswald** aplicado a headers, números grandes, countdown
- [x] **Stripes diagonales** estilo camiseta en ranking cards (opción B — full card)
- [x] **Mascotas del Mundial 2026:**
  - Maple 🦌 (alce, Canadá, rojo) → login + registro + fondo hub
  - Zayu 🐆 (jaguar, México, verde) → header + fondo predicciones
  - Clutch 🦅 (águila, USA, azul) → header + fondo ranking
- [x] Imágenes en formato JPG (convertidas de AVIF para compatibilidad)
- [x] Fondo difuminado con mascota por pestaña (opacity 4.5%, fixed)

### B10 — Deploy
- [x] Deploy en PythonAnywhere (huzerpro.pythonanywhere.com)
- [x] Flujo estable: `git push` + `git pull` + Reload

---

## Tareas pendientes críticas 🔴

> ⚠️ **Deadline: antes del 11 de junio de 2026** (inicio del torneo)

### Task #10 — Lógica de mejores terceros
**Qué es:** En la fase de grupos del Mundial 2026 (48 equipos, 12 grupos de 4), los 8 mejores terceros de cada grupo avanzan a octavos. El sistema necesita identificar automáticamente cuáles terceros clasifican según puntos, diferencia de goles y goles a favor.

**Por qué es crítica:** Sin esto, la generación de cruces de eliminatorias (#12) no puede funcionar correctamente.

**Archivos a modificar:**
- `game/scoring.py` — agregar función `mejores_terceros()`
- `db.py` o una nueva tabla para guardar clasificados

---

### Task #12 — Eliminatorias: generación de cruces reales
**Qué es:** Una vez cerrada la fase de grupos, generar automáticamente los 32 partidos de eliminatorias (octavos, cuartos, semis, final) con los cruces reales del fixture FIFA 2026.

**Por qué es crítica:** Sin cruces generados, los usuarios no pueden predecir eliminatorias.

**Archivos a modificar:**
- `game/eliminatorias.py` (nuevo)
- `admin/routes.py` — ruta para disparar la generación
- Schema DB — tabla `partidos` ya existe, solo agregar fase y referencia a clasificado

---

### Task #13 — Formulario eliminatorias con penales condicionales
**Qué es:** El formulario de predicción de eliminatorias necesita campos adicionales:
- ¿Empate al 90'? → mostrar campo de prórroga
- ¿Empate en prórroga? → mostrar campo de ganador por penales

**Por qué es crítica:** Los usuarios necesitan poder predecir eliminatorias desde el día 1.

**Archivos a modificar:**
- `templates/predicciones/index.html`
- `predicciones/routes.py`
- `static/js/predicciones.js`

---

## Notas técnicas importantes

### Deploy en PythonAnywhere
```bash
# Cada vez que hay cambios:
cd ~/PM && git pull
# Luego: Web tab → Reload
```

### Agregar imágenes nuevas
Los archivos estáticos (imágenes, audio) NO se suben con `git push` automáticamente si no se hace `git add` explícito:
```bash
git add static/img/*.jpg static/audio/*.mp3
git commit -m "Add static assets"
git push
```

### Variables CSS principales
```css
--azul-oscuro: #0a1628
--azul-medio:  #132340
--rojo:        #c0392b
--dorado:      #f39c12
--verde:       #27ae60
```

### Convención de nombres ISO (banderas)
Se usa `flagcdn.com/w80/{iso}.png` donde `iso` es el código de 2 letras en minúscula del país (ej: `mx`, `br`, `us`).
