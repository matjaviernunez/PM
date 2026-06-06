// predicciones.js — Filtros y guardado por día

// ── Estado de filtros ────────────────────────────────────────────
let grupoActivo  = "todos";
let estadoActivo = "todos";
let diaActivo    = "todos";

// Calcular fechas futuras con partidos abiertos (orden cronológico)
function getFechasProximas() {
  const hoy = new Date().toISOString().slice(0, 10);
  const secciones = [...document.querySelectorAll(".dia-section")];
  return secciones
    .map(s => s.dataset.fecha)
    .filter(f => f >= hoy)
    .sort();
}

// ── Filtro por día ───────────────────────────────────────────────
document.querySelectorAll(".filtro-dia-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filtro-dia-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    diaActivo = btn.dataset.dia;
    aplicarFiltros();
  });
});

// ── Filtro por grupo ─────────────────────────────────────────────
document.querySelectorAll(".filtro-grupo").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filtro-grupo").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    grupoActivo = btn.dataset.grupo;
    aplicarFiltros();
  });
});

// ── Filtro por estado ────────────────────────────────────────────
document.querySelectorAll(".filtro-estado-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filtro-estado-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    estadoActivo = btn.dataset.estado;
    aplicarFiltros();
  });
});

// ── Aplicar filtros ──────────────────────────────────────────────
function aplicarFiltros() {
  // Calcular qué fechas mostrar según filtro de día
  let fechasPermitidas = null;
  if (diaActivo !== "todos") {
    const proximas = getFechasProximas();
    const idx = parseInt(diaActivo) - 1;
    if (idx < proximas.length) {
      fechasPermitidas = new Set([proximas[idx]]);
    }
  }

  document.querySelectorAll(".dia-section").forEach(section => {
    const fecha = section.dataset.fecha;

    // Filtro de día
    if (fechasPermitidas && !fechasPermitidas.has(fecha)) {
      section.style.display = "none";
      return;
    }

    // Filtrar cards dentro de la sección
    const cards = section.querySelectorAll(".partido-card");
    cards.forEach(card => {
      const pasaGrupo  = grupoActivo  === "todos" || card.dataset.grupo  === grupoActivo;
      const pasaEstado = estadoActivo === "todos" || card.dataset.estado === estadoActivo;
      card.style.display = (pasaGrupo && pasaEstado) ? "" : "none";
    });

    const visibles = [...cards].filter(c => c.style.display !== "none");
    section.style.display = visibles.length > 0 ? "" : "none";
  });
}

// ── Actualizar estado del card al escribir ───────────────────────
document.querySelectorAll(".gol-input").forEach(input => {
  input.addEventListener("input", () => {
    const partidoId   = input.dataset.partido;
    const card        = document.querySelector(`[data-partido-id="${partidoId}"]`);
    const localInput  = card.querySelector(".gol-local");
    const visitaInput = card.querySelector(".gol-visita");
    const gl = localInput.value;
    const gv = visitaInput.value;

    // Marcar card como "modificado" visualmente
    if (gl !== "" && gv !== "") {
      card.classList.add("partido-card--editado");
    }
  });
});

// ── Guardar predicciones de un día ──────────────────────────────
document.querySelectorAll(".btn-guardar-dia").forEach(btn => {
  btn.addEventListener("click", async () => {
    const fecha    = btn.dataset.fecha;
    const section  = document.querySelector(`.dia-section[data-fecha="${fecha}"]`);
    const statusEl = document.getElementById(`save-status-${fecha}`);
    const cards    = section.querySelectorAll(".partido-card:not(.partido-card--cerrado)");

    const predicciones = [];
    let incompletos = 0;

    cards.forEach(card => {
      // Solo incluir cards visibles (no filtradas)
      if (card.style.display === "none") return;

      const gl = card.querySelector(".gol-local")?.value;
      const gv = card.querySelector(".gol-visita")?.value;
      const id = card.dataset.partidoId;

      if (gl === "" || gv === "") {
        incompletos++;
        card.classList.add("partido-card--incompleto");
        setTimeout(() => card.classList.remove("partido-card--incompleto"), 2000);
      } else {
        card.classList.remove("partido-card--incompleto");
        predicciones.push({
          partido_id:   parseInt(id),
          goles_local:  parseInt(gl),
          goles_visita: parseInt(gv),
        });
      }
    });

    if (predicciones.length === 0) {
      statusEl.innerHTML = '<span class="status-error">Completa al menos un partido</span>';
      return;
    }

    btn.disabled = true;
    statusEl.innerHTML = '<span class="status-guardando">⏳ Guardando...</span>';

    try {
      const res  = await fetch("/predicciones/guardar-lote", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ predicciones }),
      });
      const data = await res.json();

      if (data.ok) {
        // Actualizar status de cada card guardada
        predicciones.forEach(p => {
          const card = document.querySelector(`[data-partido-id="${p.partido_id}"]`);
          if (card) {
            card.dataset.estado = "guardado";
            const statusCard = document.getElementById(`status-${p.partido_id}`);
            if (statusCard) {
              statusCard.innerHTML = `<span class="status-guardado">✓ ${p.goles_local} – ${p.goles_visita}</span>`;
            }
            card.classList.remove("partido-card--editado");
          }
        });

        const msg = incompletos > 0
          ? `✓ ${data.guardados} guardados · ${incompletos} sin completar`
          : `✓ ${data.guardados} predicciones guardadas`;
        statusEl.innerHTML = `<span class="status-guardado">${msg}</span>`;
      } else {
        statusEl.innerHTML = `<span class="status-error">✗ ${data.error}</span>`;
      }
    } catch {
      statusEl.innerHTML = '<span class="status-error">✗ Error de conexión</span>';
    } finally {
      btn.disabled = false;
    }
  });
});
