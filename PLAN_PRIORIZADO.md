# Plan Priorizado — Diagnóstico PM (Polla Mundialista 2026)

**Fecha:** 13 junio 2026
**Decisiones tomadas:** Hosting = PythonAnywhere (free). El sync ESPN permanece *client-side* (el servidor no puede salir a ESPN en PA) → se **unifica y blinda**, no se elimina.
**Orden de ejecución:** Fase 0 → 4.

> Regla de trabajo: conversamos y confirmamos antes de implementar cada fase. Nada se programa sin luz verde.

---

## Modelo de los 3 scores (transversal)

Cada partido tiene tres marcadores con roles distintos:

| Score | Origen | Cambia | Cuenta puntos |
|-------|--------|--------|---------------|
| **Predicción** | El usuario | No (una vez cerrado el partido) | — |
| **Parcial** | ESPN `state='in'` | Sí, **con cada gol** en vivo | **Sí, en vivo** |
| **Final** | ESPN `state='post'` | No (marcador congelado) | Sí |

Estos 3 scores aparecen en **predicciones** (cada vista de partido) y el **admin** puede ver y editar el marcador (parcial/final) de cualquier partido.

Implementación: un solo marcador almacenado (`goles_local`/`goles_visita`) + `estado` indica si es *parcial* o *final*. El parcial se muestra en vivo en predicciones/torneo/ranking.

**Los puntos se recalculan SIEMPRE que cambia el marcador (parcial o final).** El ranking se mueve en vivo y las flechas de posición se actualizan con cada gol del parcial — esa es la experiencia buscada. Lo único que hace el estado `final` es **congelar el marcador** (una vez `post`, ESPN no lo sobreescribe; solo el admin), como protección anti-corrupción. No congela los puntos.

---

## Resumen de prioridades

| # | Tarea | Fase | Impacto | Esfuerzo | Riesgo del cambio |
|---|-------|------|---------|----------|-------------------|
| 1 | Cargar `.env` real → `DEBUG=false` + `SECRET_KEY` | 0 | Alto (seguridad) | Bajo | Bajo |
| 2 | SQLite WAL + `busy_timeout` | 0 | Medio-alto | Bajo | Bajo |
| 3 | Quitar APScheduler muerto del arranque | 0 | Bajo | Bajo | Bajo |
| 4 | "Jugado = tiene resultado" (fuente única) + ordenamiento | 1 | Alto (visible) | Medio | Medio |
| 5 | Consistencia de scores en predicciones/torneo/ranking | 1 | Alto | Medio | Medio |
| 6 | Unificar el sync duplicado (base.html + ranking) | 2 | Medio | Medio | Medio |
| 7 | Blindar `/push-scores` (validación + auditoría) | 2 | Alto (integridad) | Medio | Medio |
| 8 | Sincronizar penales en el push | 2 | Medio | Bajo | Bajo |
| 9 | Backups automáticos de la DB | 2 | Alto | Bajo-medio | Bajo |
| 10 | Popups: delta calculado server-side por visita | 3 | Medio | Medio | Medio |
| 11 | Flechas de posición: persistencia correcta | 3 | Medio | Bajo | Bajo |
| 12 | Limpieza de código muerto + git + docs | 4 | Bajo | Bajo | Bajo |
| 13 | Validar bracket vs fixture oficial FIFA | 4 | Alto (futuro) | Medio | Medio |
| 14 | Refresh estético | 4 | Medio | Medio | Bajo |

---

## Fase 0 — Seguridad rápida (bajo riesgo, alto impacto)

**Problema:** No hay `load_dotenv()` en ningún archivo, pese a que `python-dotenv` está en `requirements`. Como `config.py` lee `os.environ`, en producción `SECRET_KEY` se queda en el default y `DEBUG` en `"true"`. Eso deja el debugger de Werkzeug expuesto (consola interactiva ante cualquier error = riesgo de ejecución remota) y sesiones falsificables.

- [ ] Añadir `load_dotenv()` al inicio (o fijar variables en el WSGI de PythonAnywhere).
- [ ] `DEBUG=false` y `SECRET_KEY` aleatorio y secreto en producción.
- [ ] Activar `PRAGMA journal_mode=WAL` y `PRAGMA busy_timeout=5000` en `db.py` (evita `database is locked` con escrituras concurrentes).
- [ ] Quitar el bloque de APScheduler en `app.py` (no funciona en PA; solo arranca un hilo inútil).

---

## Fase 1 — Fuente única de resultados (arregla lo más visible)

**Problema:** El ordenamiento de predicciones usa `estado == 'post'`, pero `estado` quedó desincronizado (hay partidos con FINAL cargado que siguen apareciendo arriba — confirmado en captura del 12 jun). Además existen 3 campos de estado (`abierto`, `estado`, goles) y 3 caminos de escritura que no siempre concuerdan, por lo que los scores pueden diferir entre vistas.

- [ ] Definir los 3 estados de un partido por una sola verdad: **sin resultado** (no jugado) / **en vivo** (`estado='in'`, parcial) / **final** (`estado='post'`).
- [ ] Reescribir el ordenamiento en `predicciones/routes.py`: dentro de cada fecha, próximos y en-vivo arriba / finalizados al fondo; fechas totalmente finalizadas al final.
- [ ] Mostrar el **parcial en vivo** (etiqueta "EN VIVO") distinto del final, en predicciones/torneo/ranking, todos leyendo de `partidos`.
- [ ] Script de normalización: marcar `estado='post'` donde ya hay resultado final, para sanear datos actuales.
- [ ] **MUST-FIX — Edición de scores en admin no funciona.** Causa probable: `cargar_resultado()` exige penales para **cualquier** empate, incluyendo fase de grupos (donde no hay penales). Gatillar penales solo en knockout (`fase != 'grupos'`) con empate en tiempo reglamentario. Verificar también el guardado/recálculo end-to-end y que el admin pueda editar tanto el parcial en vivo como el final.

---

## Fase 2 — Sync ESPN robusto (sigue client-side, unificado y blindado)

**Problema:** El sync está duplicado en `base.html` y `ranking/index.html`. `/push-scores` acepta marcadores de cualquier usuario autenticado: alguien podría inflar un partido en curso y mover el ranking de todos. Las defensas actuales (no tocar `post`, no decrecer goles) ayudan pero no bastan. Penales no se sincronizan. No hay respaldo de la DB.

- [ ] Unificar el sync en un solo módulo JS reutilizado por todas las páginas.
- [ ] Blindar `/push-scores`: validar que el partido existe y su kickoff ya pasó, acotar goles a rango plausible, mantener guardas de `estado`/monotonía, **registrar auditoría** (usuario + payload) y permitir bloqueo manual por admin.
- [ ] Incluir penales en el payload del cliente y en el endpoint (hoy se pierden).
- [ ] Afinar el "tiempo real": polling más fino mientras hay partido en vivo, indicador de conexión claro, fallo no-silencioso.
- [ ] Backups automáticos de `data/mundial2026.db` (snapshot diario descargable / copia fuera del server).
- [ ] Marcar o retirar los caminos muertos `scraper/runner.py` y `game/espn_sync.py` para no confundir.

---

## Fase 3 — Popups y flechas

**Problema (popups):** Hay dos sistemas y ambos dependen de updates en vivo que casi nunca ocurren. El de login solo dispara si la posición cambió entre dos logins; el `rcp` solo si el sync actualiza un score y tu posición cambia en ese mismo tick de 60s.

**Problema (flechas):** En cada render el JS sobreescribe `localStorage` con la posición actual, así que al segundo render `prev == current` y la flecha desaparece — lo contrario de lo que dice su comentario.

- [ ] Calcular el delta de posición **en el servidor en cada visita** a predicciones/ranking (guardando la última posición vista por usuario) y disparar el popup ahí.
- [ ] Flechas: persistir el **delta** (o una baseline estable) y avanzarlo solo cuando la posición cambia de verdad, para que la diferencia se vea siempre.
- [ ] El ranking y las flechas se actualizan también con el **parcial en vivo** (cada gol mueve puntos → mueve posiciones → actualiza flechas), no solo con el final.

---

## Fase 4 — Limpieza y estética

- [ ] Borrar código muerto: `game/tiebreakers.py` (placeholder), `dashboard/*` (stubs), `polla.db` (0 bytes), `beautifulsoup4` sin uso en `requirements`.
- [ ] Higiene de git (mensajes de commit reales; hoy todos dicen "jn: ya?").
- [ ] Unificar documentación: `PROGRESO.md` (9 jun) contradice a `ESTADO_DEL_ARTE.md` (13 jun).
- [ ] **Validar `bracket.py` contra el fixture oficial FIFA 2026**: la plantilla de cruces y la asignación de mejores terceros (greedy anti-clash) es una aproximación, no la tabla oficial. Importante antes de generar los 16avos.
- [ ] Refresh estético (definir alcance: tipografía, tarjetas, contraste, mobile).
