# Estado del Arte — Polla Mundialista 2026
**Última actualización:** 13 de junio de 2026  
**Repositorio:** github.com/matjaviernunez/PM  
**Producción:** huzerpro.pythonanywhere.com  

---

## 1. Visión General

Aplicación web de predicciones del FIFA World Cup 2026, conocida internamente como **"polla mundialista"**. Permite a grupos de amigos competir prediciendo resultados de partidos, acumulando puntos y siguiendo un ranking en tiempo real.

El torneo 2026 tiene formato expandido: 48 selecciones, 12 grupos de 4 equipos (grupos A–L), fase de 16avos de final, y bracket eliminatorio hasta la final.

---

## 2. Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python 3.11 / Flask |
| Base de datos | SQLite (archivo `data/mundial2026.db`) |
| ORM / DB | sqlite3 nativo con `row_factory` |
| Autenticación | Flask-Login + Werkzeug (bcrypt) |
| Scheduler | APScheduler (BackgroundScheduler) |
| Frontend | HTML/CSS/JS vanilla (sin framework) |
| Hosting | PythonAnywhere (free tier) |
| Control de versiones | Git / GitHub |
| Zona horaria de negocio | Ecuador (UTC-5) |

---

## 3. Arquitectura del Proyecto

```
PM/
├── app.py                  # Entry point, blueprints, scheduler
├── config.py               # Constantes, rutas, multiplicadores
├── db.py                   # Helper get_db() → conexión SQLite
├── data/
│   ├── mundial2026.db      # Base de datos principal
│   └── equipos.json        # Catálogo de selecciones con códigos e ISO
├── game/
│   ├── models.py           # Queries de partidos y predicciones
│   ├── scoring.py          # Motor de puntuación + get_ranking()
│   ├── espn_sync.py        # Sync server-side vía APScheduler
│   └── bracket.py          # Generación de cruces 16avos
├── auth/                   # Blueprint autenticación
├── predicciones/           # Blueprint predicciones (grupos + eliminatorias)
├── ranking/                # Blueprint ranking + endpoint push-scores
├── admin/                  # Blueprint panel administrador
├── torneo/                 # Blueprint tabla de posiciones del torneo real
├── hub/                    # Blueprint noticias/estadísticas del mundial
├── templates/              # Jinja2 templates por blueprint
├── static/                 # CSS, imágenes
└── migrate_*.py            # Scripts de migración de DB (correr manualmente)
```

---

## 4. Base de Datos

### Tablas principales

**`partidos`**
```sql
id, equipo_local, equipo_visita, fecha, hora,
goles_local, goles_visita,
penales_local, penales_visita, penales_ganador,
fase, grupo, abierto (BOOL), estado TEXT DEFAULT 'pre'
```
- `abierto`: FALSE cierra predicciones para ese partido
- `estado`: `pre` (no iniciado) | `in` (en juego) | `post` (finalizado)

**`usuarios`**
```sql
id, nickname, username, email, password_hash,
es_admin, created_at, ultima_posicion,
campeon_favorito, jugador_favorito, goleador_mundial,
equipo_mas_goleador, equipo_sorpresa, equipo_decepcion,
equipo_favorito, codigo
```

**`predicciones`**
```sql
id, usuario_id, partido_id,
goles_local, goles_visita,
penales_local, penales_visita,
puntos_obtenidos
UNIQUE(usuario_id, partido_id)
```

**`puntajes_fase`**
```sql
usuario_id, fase, puntos
UNIQUE(usuario_id, fase)
```
Acumula puntos por fase para cálculo eficiente del ranking.

**`ligas`** / **`usuario_liga`**
Grupos privados de competencia. Un usuario puede pertenecer a múltiples ligas.

**`goleadores`** / **`tarjetas`**
Estadísticas del torneo real para el Hub.

---

## 5. Sistema de Puntuación

Definido en `game/scoring.py`:

```
Acertar resultado (W/D/L)    → 1 pt
+ Diferencia de goles exacta → +1 pt  (requiere resultado correcto)
+ Marcador exacto            → +2 pts (requiere diferencia correcta)
Máximo base: 4 pts por partido
```

**Eliminatorias con penales** (criterios independientes):
```
Marcador en tiempo reglamentario → hasta 4 pts (igual que arriba)
Ganador en penales               → +1 pt (requiere haber predicho empate + ganador correcto)
```

**Multiplicadores por fase:**
| Fase | Multiplicador |
|---|---|
| Grupos / 16avos | ×1 |
| Octavos / Cuartos | ×2 |
| Semis / 3er Puesto / Final | ×3 |

Ejemplo: marcador exacto en Final → 4 × 3 = **12 pts**

`recalcular_partido(partido_id)` es **idempotente**: resta puntos anteriores antes de aplicar los nuevos. Puede llamarse múltiples veces sin duplicar puntajes.

---

## 6. Módulos y Blueprints

### 6.1 Auth (`/auth`)
- Registro con nickname, username, email, password
- Login/logout con Flask-Login
- Perfil editable (equipo favorito, campeón, goleador del mundial, etc.)
- Reset de contraseña (admin puede hacerlo desde el panel)

### 6.2 Predicciones (`/predicciones`)
- Vista **grupos**: muestra los 72 partidos de la fase de grupos, agrupados por fecha
- Vista **eliminatorias**: partidos knockout por fase
- Predicción guarda/actualiza vía AJAX mientras el partido esté abierto
- Guardado por lote (todos los partidos de un día con un solo botón)
- Partidos cerrados: inputs disabled, muestra predicción guardada + resultado real + puntos obtenidos
- **Ordenamiento por estado**: partidos `pre`/`in` arriba, `post` al fondo de cada fecha; fechas completamente jugadas van al final de la lista

### 6.3 Ranking (`/ranking`)
- Tabla de posiciones global y por liga
- Desglose de puntos por fase (barras visuales)
- Estadísticas de la polla: campeón favorito, jugador favorito, marcadores más predichos, goleador, equipo sorpresa, equipo decepción
- Sistema de flechas de posición (▲/▼) con animación, persistidas en `localStorage`
- Endpoint `POST /ranking/push-scores`: recibe scores desde el cliente, actualiza DB, recalcula puntos, retorna cambio de posición del usuario actual

### 6.4 Admin (`/admin`)
- Carga manual de resultados (setea `estado='post'` automáticamente)
- **Editar score de partidos completados** (botón ✏️ en panel admin)
- Toggle abrir/cerrar partidos
- Gestión de usuarios: crear, eliminar, reset password, asignar ligas
- Crear ligas
- Ver predicciones por partido o por usuario
- Generar cruces 16avos
- Gestión de goleadores y tarjetas para el Hub

### 6.5 Torneo (`/torneo`)
- Tabla de posiciones real del torneo FIFA 2026 por grupo
- Clasificación con criterios FIFA (DG, GF, enfrentamiento directo)
- Vista bracket 16avos

### 6.6 Hub (`/mundial`)
- Noticias y estadísticas del torneo real
- Tabla de goleadores
- Tabla de tarjetas

---

## 7. Sincronización de Scores en Tiempo Real

### El Problema Estructural

PythonAnywhere (free tier) **bloquea las llamadas HTTP salientes** a dominios no whitelisted. ESPN no está en esa whitelist. Esto significa que `espn_sync.py` con APScheduler (que corre cada 60s en el servidor) **siempre retorna 0 eventos** — nunca puede contactar a ESPN desde el servidor.

### Solución Implementada: Client-Side Sync

El navegador del usuario actúa como intermediario:

```
Navegador → fetch ESPN API → POST /ranking/push-scores → DB actualizada
```

**Flujo detallado:**
1. JS en el cliente hace `fetch` a la ESPN Scoreboard API (sin restricciones de proxy)
2. Filtra eventos `in` (en juego) y `post` (finalizados)
3. Para eventos `post`: hace un segundo fetch a la **ESPN Summary API** (`/summary?event=ID`) que siempre tiene el score definitivo
4. Envía el payload a `POST /ranking/push-scores`
5. El backend actualiza `goles_local`, `goles_visita`, `estado` en DB
6. Llama a `recalcular_partido()` por cada partido actualizado
7. Retorna posición anterior y nueva del usuario actual

**Dónde corre el sync:**
- **`templates/ranking/index.html`**: sync completo con UI (indicador "Conectando con ESPN…"), recarga la página cuando hay actualizaciones. Usa Summary API para `post`.
- **`templates/base.html`**: sync silencioso en **todas las páginas autenticadas**, cada 60 segundos. Mismo patrón con Summary API. Se omite en la página de ranking (flag `window._rankingSyncActive`) para evitar duplicados.

### APIs de ESPN Utilizadas

```
Scoreboard: https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard
Summary:    https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={id}
```

La **Scoreboard API** a veces retorna `score: null` para partidos recién terminados durante la transición de datos. La **Summary API** siempre tiene el score definitivo para partidos `post`.

---

## 8. Columna `estado` en Partidos

### Motivación
Se necesitaba saber con precisión si un partido está por jugarse, en curso, o finalizado — para ordenar la UI, proteger scores finales, y sincronizar correctamente.

### Valores
| Valor | Significado |
|---|---|
| `pre` | Partido no iniciado, predicciones abiertas |
| `in` | Partido en curso |
| `post` | Partido finalizado, score definitivo |

### Migración
`migrate_estado.py` añade la columna y popula valores iniciales:
- Partidos con resultado y `abierto=FALSE` → `post`
- Partidos sin resultado y `abierto=FALSE` → `in`
- Todos los demás → `pre` (default)

### Dónde se setea `estado`

| Acción | Nuevo estado |
|---|---|
| `cerrar_partidos_vencidos()` (automático al cargar predicciones) | `pre` → `in` |
| `push_scores` recibe evento ESPN con `state='in'` o `'post'` | Actualiza según ESPN |
| Admin carga resultado manualmente | Fuerza `post` |

### Protección "estado = post"

Una vez que un partido llega a `post`, **ni `push_scores` ni `espn_sync` lo sobreescriben**. Solo el admin puede corregirlo manualmente. Esto previene que datos transitorios/erróneos de ESPN corrompan un resultado ya definitivo.

---

## 9. Problemas Encontrados y Soluciones

### 9.1 Corrupción de Score (KOR 2-1 CZE → 0-0)

**Problema:** Después de un `git pull` y reinicio del servidor, el score de KOR vs CZE pasó de 2-1 a 0-0.

**Causa raíz:** En el JS de `ranking/index.html`, el código original usaba:
```javascript
home_score: parseInt(home.score ?? 0),  // null → 0 !!!
```
ESPN retorna `score: null` para partidos recién finalizados durante la transición de datos. Al reiniciar el servidor, el cache `_last_known` en `espn_sync.py` se limpiaba, forzando el reprocessing de todos los eventos. El JS convertía `null` a `0` y enviaba `0-0` a `push_scores`, que sobreescribía el 2-1 legítimo.

**Solución (múltiples capas de defensa):**

1. **Filtro null en JS**: si `home.score == null || away.score == null`, el evento se descarta completamente (no se envía como `0-0`)
2. **Protección `estado='post'`**: `push_scores` ignora cualquier actualización para partidos ya marcados como finalizados
3. **Verificación de monotonía**: el total de goles de un partido nunca puede *disminuir* (datos viejos/erróneos)
4. **ESPN Summary API**: para partidos `post`, se consulta la Summary API que siempre tiene el score definitivo, eliminando el riesgo de scores null del scoreboard

### 9.2 Internal Server Error Después del Primer Deploy con `estado`

**Problema:** La app crasheó inmediatamente después de hacer `git pull` y recargar, antes de correr la migración.

**Causa:** El código nuevo referenciaba la columna `estado` en queries SQL, pero la columna no existía aún en la DB de producción.

**Solución:** Establecer el orden correcto de deploy:
```
1. git pull
2. python migrate_estado.py
3. Reload app en PythonAnywhere
```

El script `migrate_estado.py` es idempotente — si la columna ya existe, imprime `"Columna 'estado' ya existe — nada que hacer."` y termina sin error.

### 9.3 APScheduler No Funciona en PythonAnywhere

**Problema:** `espn_sync.py` corría cada 60s pero nunca actualizaba nada.

**Causa:** PythonAnywhere free tier bloquea llamadas HTTP salientes a ESPN. El scheduler intentaba conectar, fallaba silenciosamente, y retornaba `0 actualizados`.

**Solución:** Migrar completamente la lógica de sync al cliente (JS en el navegador), que no tiene restricciones de proxy. El APScheduler se mantiene en el código como fallback por si en el futuro se migra a otro hosting, pero no es funcional en PythonAnywhere.

### 9.4 Flechas de Posición Desaparecían

**Problema:** Las flechas ▲▼ en el ranking desaparecían 5 minutos después del último cambio de score.

**Causa:** La implementación original tenía un timer de expiración de 5 minutos basado en `sessionStorage`. Además, `sessionStorage` se limpia al cerrar la pestaña.

**Solución:**
1. Eliminar el bloque de expiración de 5 minutos
2. Cambiar de `sessionStorage` a `localStorage` para que las flechas persistan entre sesiones
3. Las flechas solo cambian cuando la posición vuelve a moverse — comparan siempre contra el último estado conocido

---

## 10. Popup de Cambio de Posición

Implementado en `base.html` + `ranking/routes.py`.

**Flujo:**
1. El sync silencioso de `base.html` llama a `push_scores`
2. `push_scores` calcula posición del usuario antes y después de actualizar
3. Si hay cambios (`actualizados > 0`) y la posición cambió, devuelve `pos_antes`, `pos_despues`, `total_usuarios`
4. El JS muestra el popup con mensaje contextual

**Mensajes:**
| Situación | Mensaje |
|---|---|
| Llegó al 1er lugar | 👑 ¡Eres el líder! No te duermas... |
| Salió del último lugar | 🎉 ¡Ya no eres el último! Algo es algo |
| Subió varios puestos | 🚀 ¡Subiste X puestos! Vas en el puesto N |
| Subió 1 puesto | 📈 Subiste un puesto, ahora vas N° |
| Cayó al último lugar | 💀 ¡Caíste al último! ¿Vas a dejar eso así? |
| Perdió el 1er lugar | 😤 ¡Te quitaron el liderato! A recuperarlo |
| Bajó varios puestos | 📉 Bajaste X puestos... vas en el puesto N |
| Bajó 1 puesto | 😬 Bajaste un puesto, ojo |
| Sin cambio de posición | (no se muestra nada) |

El popup se auto-cierra a los 6 segundos. Aparece en cualquier página autenticada de la app.

---

## 11. Archivos Clave por Funcionalidad

| Funcionalidad | Archivos |
|---|---|
| Motor de puntuación | `game/scoring.py` |
| Cierre automático de partidos | `game/models.py` → `cerrar_partidos_vencidos()` |
| Sync server-side (no funcional en PA) | `game/espn_sync.py` |
| Sync client-side (activo) | `templates/ranking/index.html`, `templates/base.html` |
| Endpoint receptor de scores | `ranking/routes.py` → `push_scores()` |
| Cálculo de posición para popup | `ranking/routes.py` → `_posicion_usuario()` |
| Carga manual de resultados | `admin/routes.py` → `cargar_resultado()` |
| Ordenamiento predicciones | `predicciones/routes.py` → `index()` |
| Migración columna estado | `migrate_estado.py` |
| Popup y flechas animadas | `templates/base.html`, `templates/ranking/index.html` |

---

## 12. Scripts de Utilidad / Migración

| Script | Propósito |
|---|---|
| `init_db.py` | Crea todas las tablas desde cero |
| `seed_partidos.py` | Carga los 72 partidos de grupos en DB |
| `seed_ligas.py` | Crea ligas iniciales |
| `make_admin.py` | Promueve un usuario a admin |
| `migrate_estado.py` | Añade columna `estado` (idempotente) |
| `migrate_penales.py` | Añade columnas de penales a partidos y predicciones |
| `migrate_extras.py` | Campos adicionales de perfil de usuario |
| `migrate_fix_horas.py` / `migrate_fix_horas_completo.py` | Corrección de horarios ECT |
| `clear_predicciones.py` | Limpia predicciones (para testing) |

---

## 13. Consideraciones de Hosting

### PythonAnywhere (Free Tier)
- ✅ App siempre activa (no se "duerme")
- ✅ HTTPS incluido
- ❌ Bloquea llamadas HTTP salientes a dominios no whitelisted (ESPN bloqueado)
- ❌ APScheduler para sync ESPN no es funcional
- ⚠️ La sync de scores depende 100% de que haya usuarios con la app abierta

### Workaround de Sync
El sync corre en el navegador del cliente. Mientras **cualquier usuario autenticado** tenga la app abierta en cualquier pestaña, los scores se actualizan cada 60 segundos. Durante partidos del Mundial esto es suficiente — siempre hay alguien conectado.

### Alternativas (si se requiere sync server-side)
- **Render** (free tier): permite llamadas salientes, pero el servidor se "duerme" tras 15 min de inactividad
- **Railway**: permite llamadas salientes, pero tiene costo después del período de prueba
- En cualquiera de estos, `espn_sync.py` funcionaría nativamente con APScheduler

---

## 14. Estado Actual (13 junio 2026)

### Funcionando en producción ✅
- Registro, login, perfil de usuario
- Predicciones de fase de grupos (72 partidos) y eliminatorias
- Sistema de puntuación con multiplicadores por fase
- Ranking global y por liga con flechas de posición animadas (▲▼)
- Sync de scores en tiempo real vía cliente
- ESPN Summary API para scores definitivos de partidos finalizados
- Protección multicapa contra corrupción de scores
- Ordenamiento de predicciones: partidos en curso arriba, jugados abajo
- Popup divertido de cambio de posición en ranking
- Panel admin: carga de resultados, edición de scores, gestión de usuarios y ligas
- Tabla del torneo real con posiciones por grupo
- Hub de estadísticas (goleadores, tarjetas, favoritos)

### Limitación conocida ⚠️
- Si ningún usuario tiene la app abierta cuando termina un partido, el score no se actualiza automáticamente. El admin puede corregirlo manualmente desde el panel de administración.

---

*Documento generado automáticamente a partir del estado del repositorio y del historial de desarrollo.*
