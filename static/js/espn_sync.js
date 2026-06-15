// espn_sync.js — Módulo único de sincronización de marcadores desde ESPN.
// Lo usan: base.html (sync silencioso), ranking (con UI + recarga) y el
// botón "Actualizar desde ESPN" del admin. El fetch se hace en el navegador
// porque PythonAnywhere bloquea las salidas a ESPN desde el servidor.
(function () {
  const ESPN_SB =
    'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard';
  const ESPN_SUMMARY =
    'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=';

  // Fecha UTC del evento ESPN -> fecha Ecuador (UTC-5) 'YYYY-MM-DD'
  function utcToEct(s) {
    if (!s) return null;
    try {
      const d = new Date(s);
      const ect = new Date(d.getTime() - 5 * 3600 * 1000);
      return `${ect.getUTCFullYear()}-${String(ect.getUTCMonth() + 1).padStart(2, '0')}-${String(ect.getUTCDate()).padStart(2, '0')}`;
    } catch (_) {
      return null;
    }
  }

  // Arma el payload de eventos (en juego + finalizados). Para 'post' usa la
  // Summary API, que siempre trae el marcador definitivo.
  async function buildPayload() {
    const r = await fetch(ESPN_SB);
    const data = await r.json();
    const events = (data.events || []).filter((e) => {
      const s = e.status?.type?.state;
      return s === 'in' || s === 'post';
    });
    if (!events.length) return [];

    const items = await Promise.all(
      events.map(async (ev) => {
        const comp = ev.competitions?.[0] || {};
        const home = comp.competitors?.find((c) => c.homeAway === 'home') || {};
        const away = comp.competitors?.find((c) => c.homeAway === 'away') || {};
        const state = ev.status?.type?.state || '';
        let hs = home.score;
        let as = away.score;

        if (state === 'post') {
          try {
            const sr = await fetch(ESPN_SUMMARY + ev.id);
            const sd = await sr.json();
            const sc = sd.header?.competitions?.[0] || {};
            const sh = (sc.competitors || []).find((c) => c.homeAway === 'home') || {};
            const sa = (sc.competitors || []).find((c) => c.homeAway === 'away') || {};
            if (sh.score != null) hs = sh.score;
            if (sa.score != null) as = sa.score;
          } catch (_) {
            /* fallback al score del scoreboard */
          }
        }

        if (hs == null || as == null) return null;
        // Tanda de penales (solo en eliminatorias decididas por penales).
        // ESPN expone el marcador de la tanda en competitor.shootoutScore.
        const ph = home.shootoutScore;
        const pa = away.shootoutScore;
        return {
          home: home.team?.abbreviation || '',
          away: away.team?.abbreviation || '',
          home_score: parseInt(hs),
          away_score: parseInt(as),
          pen_home: ph != null ? parseInt(ph) : null,
          pen_away: pa != null ? parseInt(pa) : null,
          state,
          fecha_ect: utcToEct(ev.date || comp.date || ''),
        };
      })
    );
    return items.filter(Boolean);
  }

  // Hace el fetch + POST a /ranking/push-scores. Devuelve el JSON del backend
  // (o {actualizados:0, empty:true} si no hay eventos en juego/finalizados).
  async function fetchAndPush() {
    const payload = await buildPayload();
    if (!payload.length) {
      return { ok: true, actualizados: 0, recalculados: 0, empty: true };
    }
    const url = window.PUSH_SCORES_URL || '/ranking/push-scores';
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events: payload }),
    });
    return await resp.json();
  }

  window.EspnSync = { fetchAndPush, buildPayload };
})();
