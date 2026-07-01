/**
 * bracket.js — Llave interactiva del Mundial 2026
 *
 * Lee PARTIDOS_KO y EQUIPOS_MAP (globals inyectados por el template).
 * Renderiza un bracket horizontal: 16avos → Octavos → Cuartos → Semis → Final.
 * Click en un equipo para avanzarlo.  Partidos con resultado real quedan fijos.
 */
(function () {
  'use strict';

  /* ═══ BRACKET TREE — estructura FIFA 2026 (orden visual) ═══
     ci  = indice cronologico dentro de partidos_ko[phase]
     from = [slotId, slotId] de los partidos alimentadores (ganadores avanzan) */

  var ROUNDS = [
    { phase: '16avos', label: '16avos de Final', slots: [
        { id: 'R1',  ci: 0 },  { id: 'R2',  ci: 3 },
        { id: 'R3',  ci: 2 },  { id: 'R4',  ci: 5 },
        { id: 'R5',  ci: 11 }, { id: 'R6',  ci: 10 },
        { id: 'R7',  ci: 9 },  { id: 'R8',  ci: 8 },
        { id: 'R9',  ci: 1 },  { id: 'R10', ci: 4 },
        { id: 'R11', ci: 6 },  { id: 'R12', ci: 7 },
        { id: 'R13', ci: 14 }, { id: 'R14', ci: 13 },
        { id: 'R15', ci: 12 }, { id: 'R16', ci: 15 },
      ]},
    { phase: 'octavos', label: 'Octavos de Final', slots: [
        { id: 'O1', ci: 0, from: ['R1',  'R2'] },
        { id: 'O2', ci: 1, from: ['R3',  'R4'] },
        { id: 'O3', ci: 4, from: ['R5',  'R6'] },
        { id: 'O4', ci: 5, from: ['R7',  'R8'] },
        { id: 'O5', ci: 2, from: ['R9',  'R10'] },
        { id: 'O6', ci: 3, from: ['R11', 'R12'] },
        { id: 'O7', ci: 6, from: ['R13', 'R14'] },
        { id: 'O8', ci: 7, from: ['R15', 'R16'] },
      ]},
    { phase: 'cuartos', label: 'Cuartos de Final', slots: [
        { id: 'Q1', ci: 0, from: ['O1', 'O2'] },
        { id: 'Q2', ci: 1, from: ['O3', 'O4'] },
        { id: 'Q3', ci: 2, from: ['O5', 'O6'] },
        { id: 'Q4', ci: 3, from: ['O7', 'O8'] },
      ]},
    { phase: 'semis', label: 'Semifinales', slots: [
        { id: 'S1', ci: 0, from: ['Q1', 'Q2'] },
        { id: 'S2', ci: 1, from: ['Q3', 'Q4'] },
      ]},
    { phase: 'final', label: 'Final', slots: [
        { id: 'F1', ci: 0, from: ['S1', 'S2'] },
      ]},
  ];

  var THIRD = { phase: '3er_puesto', label: '3er Puesto',
                slot: { id: '3P', ci: 0, fromLosers: ['S1', 'S2'] } };

  /* ═══ STATE ═══ */
  var matches   = {};   // slotId -> { local, visita, gl, gv, pen_ganador, fecha, hora }
  var winners   = {};   // slotId -> teamCode
  var losersMap = {};   // slotId -> teamCode
  var locked    = {};   // slotId -> true
  var slotTeams = {};   // slotId -> [team1, team2]
  var feedsInto = {};   // slotId -> { target, pos }
  var ready     = false;

  /* ═══ INIT ═══ */
  function init() {
    var ko = window.PARTIDOS_KO || {};
    var equipos = window.EQUIPOS_MAP || {};

    // Build feedsInto lookup
    ROUNDS.forEach(function (round) {
      round.slots.forEach(function (slot) {
        if (slot.from) {
          slot.from.forEach(function (srcId, idx) {
            feedsInto[srcId] = { target: slot.id, pos: idx };
          });
        }
      });
    });

    // Populate match data from DB
    ROUNDS.forEach(function (round) {
      var phase = ko[round.phase] || [];
      round.slots.forEach(function (slot) {
        var m = phase[slot.ci];
        if (m) {
          matches[slot.id] = m;
          slotTeams[slot.id] = [m.equipo_local, m.equipo_visita];
          if (m.goles_local !== null && m.goles_local !== undefined && m.estado === 'post') {
            var w, l;
            if (m.goles_local > m.goles_visita)      { w = m.equipo_local;  l = m.equipo_visita; }
            else if (m.goles_visita > m.goles_local)  { w = m.equipo_visita; l = m.equipo_local;  }
            else { // penales
              w = m.penales_ganador === 'local' ? m.equipo_local  : m.equipo_visita;
              l = m.penales_ganador === 'local' ? m.equipo_visita : m.equipo_local;
            }
            winners[slot.id] = w;
            losersMap[slot.id] = l;
            locked[slot.id] = true;
          }
        } else if (slot.from) {
          slotTeams[slot.id] = [winners[slot.from[0]] || null,
                                winners[slot.from[1]] || null];
        }
      });
    });

    // 3er puesto
    var tp = (ko[THIRD.phase] || [])[THIRD.slot.ci];
    if (tp) {
      matches[THIRD.slot.id] = tp;
      slotTeams[THIRD.slot.id] = [tp.equipo_local, tp.equipo_visita];
      if (tp.goles_local !== null && tp.goles_local !== undefined && tp.estado === 'post') {
        winners[THIRD.slot.id] = tp.goles_local > tp.goles_visita ? tp.equipo_local
          : tp.goles_visita > tp.goles_local ? tp.equipo_visita
          : tp.penales_ganador === 'local' ? tp.equipo_local : tp.equipo_visita;
        locked[THIRD.slot.id] = true;
      }
    } else {
      slotTeams[THIRD.slot.id] = [losersMap['S1'] || null, losersMap['S2'] || null];
    }

    ready = true;
    render();
    setTimeout(drawConnectors, 80);
    window.addEventListener('resize', drawConnectors);
  }

  /* ═══ RENDER ═══ */
  function render() {
    var container = document.getElementById('bracket-container');
    if (!container) return;
    container.innerHTML = '';

    var equipos = window.EQUIPOS_MAP || {};
    var filterSel = document.getElementById('bracket-from-round');
    var startIdx = filterSel ? parseInt(filterSel.value) || 0 : 0;

    // Ajustar altura del canvas segun rondas visibles
    var numRounds = ROUNDS.length - startIdx;
    container.dataset.rounds = numRounds;

    // SVG para conectores
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.id = 'bracket-svg';
    svg.classList.add('bkt-svg');
    container.appendChild(svg);

    // Rondas principales
    ROUNDS.forEach(function (round, rIdx) {
      if (rIdx < startIdx) return;
      var col = document.createElement('div');
      col.className = 'bkt-round';
      col.dataset.round = round.phase;

      var hdr = document.createElement('div');
      hdr.className = 'bkt-round-hdr';
      hdr.textContent = round.label;
      col.appendChild(hdr);

      var games = document.createElement('div');
      games.className = 'bkt-games';
      round.slots.forEach(function (slot) {
        games.appendChild(buildGame(slot, equipos));
      });
      col.appendChild(games);
      container.appendChild(col);
    });

    // 3er puesto — columna propia al nivel de la Final
    if (startIdx <= 3) {
      var tCol = document.createElement('div');
      tCol.className = 'bkt-round bkt-round--third';
      tCol.dataset.round = '3er_puesto';

      var tHdr = document.createElement('div');
      tHdr.className = 'bkt-round-hdr';
      tHdr.textContent = '3er Puesto';
      tCol.appendChild(tHdr);

      var tGames = document.createElement('div');
      tGames.className = 'bkt-games';
      tGames.appendChild(buildGame(THIRD.slot, equipos));
      tCol.appendChild(tGames);
      container.appendChild(tCol);
    }

    // Hint
    var hint = document.createElement('div');
    hint.className = 'bkt-hint';
    hint.textContent = 'Haz click en un equipo para avanzarlo. Los resultados reales están fijos.';
    container.parentElement.appendChild(hint);
    // Remove previous hints
    var hints = container.parentElement.querySelectorAll('.bkt-hint');
    if (hints.length > 1) { for (var i = 0; i < hints.length - 1; i++) hints[i].remove(); }
  }

  function buildGame(slot, equipos) {
    var teams = slotTeams[slot.id] || [null, null];
    var m = matches[slot.id];
    var isLocked = locked[slot.id];
    var win = winners[slot.id];

    var el = document.createElement('div');
    el.className = 'bkt-game';
    el.dataset.slot = slot.id;

    // Header fecha/hora
    var hdr = document.createElement('div');
    hdr.className = 'bkt-game-hdr';
    if (m && m.fecha) {
      var p = m.fecha.split('-');
      hdr.textContent = parseInt(p[2]) + '/' + parseInt(p[1]) + (m.hora ? ' · ' + m.hora : '');
    } else {
      hdr.textContent = '—';
    }
    el.appendChild(hdr);

    // Filas de equipos
    for (var t = 0; t < 2; t++) {
      var team = teams[t];
      var row = document.createElement('div');
      row.className = 'bkt-team';

      if (!team) {
        row.classList.add('bkt-team--empty');
        row.innerHTML = '<span class="bkt-code">Por definir</span>';
      } else {
        var iso = (equipos[team] && equipos[team].iso) || 'un';
        var isWin = (win === team);
        if (isLocked) {
          row.classList.add('bkt-team--locked');
          if (isWin) row.classList.add('bkt-team--selected');
        } else if (isWin) {
          row.classList.add('bkt-team--selected');
        }

        row.innerHTML =
          '<img class="bkt-flag" src="https://flagcdn.com/w40/' + iso + '.png" alt="' + team + '" onerror="this.style.display=\'none\'">' +
          '<span class="bkt-code">' + team + '</span>' +
          (isWin ? '<span class="bkt-check">' + (isLocked ? '🔒' : '✓') + '</span>' : '');

        if (!isLocked) {
          (function (sid, tc) {
            row.addEventListener('click', function () { onTeamClick(sid, tc); });
          })(slot.id, team);
        }
      }
      el.appendChild(row);
    }
    return el;
  }

  /* ═══ CLICK ═══ */
  function onTeamClick(slotId, teamCode) {
    if (locked[slotId]) return;
    var teams = slotTeams[slotId];
    if (!teams || teams.indexOf(teamCode) === -1) return;

    if (winners[slotId] === teamCode) {
      delete winners[slotId];
      delete losersMap[slotId];
    } else {
      winners[slotId] = teamCode;
      losersMap[slotId] = teams[0] === teamCode ? teams[1] : teams[0];
    }
    propagate(slotId);
    render();
    setTimeout(drawConnectors, 80);
  }

  /* ═══ PROPAGACION ═══ */
  function propagate(changedId) {
    var info = feedsInto[changedId];
    if (!info) {
      // Podria ser semifinal -> actualizar 3er puesto
      update3rd();
      return;
    }
    var tid = info.target;

    // Si el slot destino tiene match real en DB, no lo tocamos
    if (matches[tid]) { update3rd(); return; }

    var teams = slotTeams[tid] || [null, null];
    teams[info.pos] = winners[changedId] || null;
    slotTeams[tid] = teams;

    // Siempre resetear predicción downstream cuando un alimentador cambia
    delete winners[tid];
    delete losersMap[tid];
    propagate(tid);
  }

  function update3rd() {
    if (matches[THIRD.slot.id]) return; // ya tiene match real
    slotTeams[THIRD.slot.id] = [losersMap['S1'] || null, losersMap['S2'] || null];
    if (winners['3P'] && slotTeams['3P'].indexOf(winners['3P']) === -1) {
      delete winners['3P'];
      delete losersMap['3P'];
    }
  }

  /* ═══ CONECTORES SVG ═══ */
  function drawConnectors() {
    var svg = document.getElementById('bracket-svg');
    var canvas = document.getElementById('bracket-container');
    if (!svg || !canvas) return;

    svg.innerHTML = '';
    svg.setAttribute('width', canvas.scrollWidth);
    svg.setAttribute('height', canvas.scrollHeight);

    var cr = canvas.getBoundingClientRect();
    var filterSel = document.getElementById('bracket-from-round');
    var startIdx = filterSel ? parseInt(filterSel.value) || 0 : 0;

    ROUNDS.forEach(function (round, rIdx) {
      if (rIdx < startIdx) return;
      round.slots.forEach(function (slot) {
        if (!slot.from) return;
        var tgt = canvas.querySelector('[data-slot="' + slot.id + '"]');
        if (!tgt) return;

        slot.from.forEach(function (srcId) {
          var src = canvas.querySelector('[data-slot="' + srcId + '"]');
          if (!src) return;
          var sr = src.getBoundingClientRect();
          var tr = tgt.getBoundingClientRect();

          var x1 = sr.right  - cr.left;
          var y1 = sr.top + sr.height / 2 - cr.top;
          var x2 = tr.left   - cr.left;
          var y2 = tr.top + tr.height / 2 - cr.top;
          var mx = (x1 + x2) / 2;

          var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
          p.setAttribute('d', 'M' + x1 + ',' + y1 + ' H' + mx + ' V' + y2 + ' H' + x2);
          p.setAttribute('fill', 'none');
          p.setAttribute('stroke', 'rgba(255,255,255,0.12)');
          p.setAttribute('stroke-width', '1.5');
          svg.appendChild(p);
        });
      });
    });
  }

  /* ═══ FILTRO ═══ */
  window.bracketFilterChange = function () {
    if (!ready) return;
    render();
    setTimeout(drawConnectors, 80);
  };

  /* ═══ BOOT ═══ */
  window.initBracketView = function () {
    if (!ready) init();
    else { render(); setTimeout(drawConnectors, 80); }
  };

})();
