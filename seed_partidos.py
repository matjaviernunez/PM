"""
seed_partidos.py — Pobla la tabla partidos con los 72 partidos
reales de la fase de grupos del Mundial 2026.

Horas en ET (Eastern Time). Idempotente: no duplica si ya existen.

Uso:
    python seed_partidos.py
"""

from db import get_db

PARTIDOS = [
    # ── GRUPO A: México, Sudáfrica, Corea del Sur, Rep. Checa ─────────────
    ("grupos","A","2026-06-11","15:00","MEX","RSA"),
    ("grupos","A","2026-06-11","22:00","KOR","CZE"),
    ("grupos","A","2026-06-18","12:00","CZE","RSA"),
    ("grupos","A","2026-06-18","21:00","MEX","KOR"),
    ("grupos","A","2026-06-24","21:00","CZE","MEX"),
    ("grupos","A","2026-06-24","21:00","RSA","KOR"),

    # ── GRUPO B: Canadá, Bosnia-Herz., Qatar, Suiza ───────────────────────
    ("grupos","B","2026-06-12","15:00","CAN","BIH"),
    ("grupos","B","2026-06-13","15:00","QAT","SUI"),
    ("grupos","B","2026-06-18","15:00","SUI","BIH"),
    ("grupos","B","2026-06-18","18:00","CAN","QAT"),
    ("grupos","B","2026-06-24","15:00","SUI","CAN"),
    ("grupos","B","2026-06-24","15:00","BIH","QAT"),

    # ── GRUPO C: Brasil, Marruecos, Haití, Escocia ────────────────────────
    ("grupos","C","2026-06-13","18:00","BRA","MAR"),
    ("grupos","C","2026-06-13","21:00","HAI","SCO"),
    ("grupos","C","2026-06-19","18:00","SCO","MAR"),
    ("grupos","C","2026-06-19","20:30","BRA","HAI"),
    ("grupos","C","2026-06-24","18:00","SCO","BRA"),
    ("grupos","C","2026-06-24","18:00","MAR","HAI"),

    # ── GRUPO D: EE.UU., Paraguay, Australia, Turquía ────────────────────
    ("grupos","D","2026-06-12","21:00","USA","PAR"),
    ("grupos","D","2026-06-13","00:00","AUS","TUR"),
    ("grupos","D","2026-06-19","15:00","USA","AUS"),
    ("grupos","D","2026-06-19","23:00","TUR","PAR"),
    ("grupos","D","2026-06-25","22:00","TUR","USA"),
    ("grupos","D","2026-06-25","22:00","PAR","AUS"),

    # ── GRUPO E: Alemania, Curazao, Costa de Marfil, Ecuador ─────────────
    ("grupos","E","2026-06-14","13:00","GER","CUW"),
    ("grupos","E","2026-06-14","19:00","CIV","ECU"),
    ("grupos","E","2026-06-20","16:00","GER","CIV"),
    ("grupos","E","2026-06-20","20:00","ECU","CUW"),
    ("grupos","E","2026-06-25","16:00","CUW","CIV"),
    ("grupos","E","2026-06-25","16:00","ECU","GER"),

    # ── GRUPO F: Países Bajos, Japón, Suecia, Túnez ──────────────────────
    ("grupos","F","2026-06-14","16:00","NED","JPN"),
    ("grupos","F","2026-06-14","22:00","SWE","TUN"),
    ("grupos","F","2026-06-20","13:00","NED","SWE"),
    ("grupos","F","2026-06-20","00:00","TUN","JPN"),
    ("grupos","F","2026-06-25","19:00","JPN","SWE"),
    ("grupos","F","2026-06-25","19:00","TUN","NED"),

    # ── GRUPO G: Bélgica, Egipto, Irán, Nueva Zelanda ────────────────────
    ("grupos","G","2026-06-15","15:00","BEL","EGY"),
    ("grupos","G","2026-06-15","21:00","IRN","NZL"),
    ("grupos","G","2026-06-21","15:00","BEL","IRN"),
    ("grupos","G","2026-06-21","21:00","NZL","EGY"),
    ("grupos","G","2026-06-26","23:00","EGY","IRN"),
    ("grupos","G","2026-06-26","23:00","NZL","BEL"),

    # ── GRUPO H: España, Cabo Verde, Arabia Saudita, Uruguay ─────────────
    ("grupos","H","2026-06-15","12:00","ESP","CPV"),
    ("grupos","H","2026-06-15","18:00","KSA","URU"),
    ("grupos","H","2026-06-21","12:00","ESP","KSA"),
    ("grupos","H","2026-06-21","18:00","URU","CPV"),
    ("grupos","H","2026-06-26","20:00","CPV","KSA"),
    ("grupos","H","2026-06-26","20:00","URU","ESP"),

    # ── GRUPO I: Francia, Senegal, Irak, Noruega ─────────────────────────
    ("grupos","I","2026-06-16","15:00","FRA","SEN"),
    ("grupos","I","2026-06-16","18:00","IRQ","NOR"),
    ("grupos","I","2026-06-22","17:00","FRA","IRQ"),
    ("grupos","I","2026-06-22","20:00","NOR","SEN"),
    ("grupos","I","2026-06-26","15:00","NOR","FRA"),
    ("grupos","I","2026-06-26","15:00","SEN","IRQ"),

    # ── GRUPO J: Argentina, Argelia, Austria, Jordania ───────────────────
    ("grupos","J","2026-06-16","21:00","ARG","ALG"),
    ("grupos","J","2026-06-17","00:00","AUT","JOR"),
    ("grupos","J","2026-06-22","13:00","ARG","AUT"),
    ("grupos","J","2026-06-22","23:00","JOR","ALG"),
    ("grupos","J","2026-06-27","22:00","JOR","ARG"),
    ("grupos","J","2026-06-27","22:00","ALG","AUT"),

    # ── GRUPO K: Portugal, RD Congo, Uzbekistán, Colombia ────────────────
    ("grupos","K","2026-06-17","13:00","POR","COD"),
    ("grupos","K","2026-06-17","22:00","UZB","COL"),
    ("grupos","K","2026-06-23","13:00","POR","UZB"),
    ("grupos","K","2026-06-23","22:00","COL","COD"),
    ("grupos","K","2026-06-27","19:30","COL","POR"),
    ("grupos","K","2026-06-27","19:30","COD","UZB"),

    # ── GRUPO L: Inglaterra, Croacia, Ghana, Panamá ──────────────────────
    ("grupos","L","2026-06-17","16:00","ENG","CRO"),
    ("grupos","L","2026-06-17","19:00","GHA","PAN"),
    ("grupos","L","2026-06-23","16:00","ENG","GHA"),
    ("grupos","L","2026-06-23","19:00","PAN","CRO"),
    ("grupos","L","2026-06-27","17:00","PAN","ENG"),
    ("grupos","L","2026-06-27","17:00","CRO","GHA"),
]


def seed():
    with get_db() as conn:
        insertados = 0
        for fase, grupo, fecha, hora, local, visita in PARTIDOS:
            # No duplicar si ya existe ese partido
            existe = conn.execute("""
                SELECT id FROM partidos
                WHERE fase=? AND grupo=? AND equipo_local=? AND equipo_visita=?
            """, (fase, grupo, local, visita)).fetchone()

            if not existe:
                conn.execute("""
                    INSERT INTO partidos
                        (fase, grupo, fecha, hora, equipo_local, equipo_visita, abierto)
                    VALUES (?, ?, ?, ?, ?, ?, TRUE)
                """, (fase, grupo, fecha, hora, local, visita))
                insertados += 1

        conn.commit()
        print(f"✓ {insertados} partidos insertados ({len(PARTIDOS) - insertados} ya existían)")


if __name__ == "__main__":
    seed()
