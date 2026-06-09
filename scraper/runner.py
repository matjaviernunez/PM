"""
scraper/runner.py -- Obtiene resultados, goleadores y tarjetas del Mundial 2026 desde ESPN API.
No requiere API key ni Playwright.

ESPN endpoints:
  Scoreboard:  https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard
  Stats leaders: https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/statistics/leaders
"""

import requests
from db import get_db
from game.scoring import recalcular_partido

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
ESPN_STATS      = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/statistics/leaders"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Mapeo de nombres ESPN -> codigos FIFA usados en nuestra DB
NOMBRES_ESPN = {
    "Mexico":               "MEX",
    "South Africa":         "RSA",
    "Korea Republic":       "KOR",
    "Czech Republic":       "CZE",
    "Czechia":              "CZE",
    "Canada":               "CAN",
    "Bosnia and Herzegovina":"BIH",
    "Qatar":                "QAT",
    "Switzerland":          "SUI",
    "Brazil":               "BRA",
    "Morocco":              "MAR",
    "Haiti":                "HAI",
    "Scotland":             "SCO",
    "United States":        "USA",
    "Paraguay":             "PAR",
    "Australia":            "AUS",
    "Turkey":               "TUR",
    "Turkiye":              "TUR",
    "Germany":              "GER",
    "Curacao":              "CUW",
    "Ivory Coast":          "CIV",
    "Ecuador":              "ECU",
    "Netherlands":          "NED",
    "Japan":                "JPN",
    "Sweden":               "SWE",
    "Tunisia":              "TUN",
    "Belgium":              "BEL",
    "Egypt":                "EGY",
    "Iran":                 "IRN",
    "New Zealand":          "NZL",
    "Spain":                "ESP",
    "Cape Verde":           "CPV",
    "Saudi Arabia":         "KSA",
    "Uruguay":              "URU",
    "France":               "FRA",
    "Senegal":              "SEN",
    "Iraq":                 "IRQ",
    "Norway":               "NOR",
    "Argentina":            "ARG",
    "Algeria":              "ALG",
    "Austria":              "AUT",
    "Jordan":               "JOR",
    "Portugal":             "POR",
    "DR Congo":             "COD",
    "Congo":                "COD",
    "Uzbekistan":           "UZB",
    "Colombia":             "COL",
    "England":              "ENG",
    "Croatia":              "CRO",
    "Ghana":                "GHA",
    "Panama":               "PAN",
}


def _codigo(nombre: str) -> str | None:
    return NOMBRES_ESPN.get(nombre)


# -- Resultados de partidos ------------------------------------------------

def scrape_resultados() -> dict:
    """
    Llama al ESPN scoreboard, detecta partidos finalizados y actualiza la DB.
    Retorna {"actualizados": N, "errores": [...]}
    """
    try:
        resp = requests.get(ESPN_SCOREBOARD, timeout=10, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"actualizados": 0, "errores": [str(e)]}

    eventos     = data.get("events", [])
    actualizados = 0
    errores      = []

    with get_db() as conn:
        for evento in eventos:
            try:
                status = evento.get("status", {})
                if status.get("type", {}).get("completed") is not True:
                    continue

                competidores = evento["competitions"][0]["competitors"]
                home = next(c for c in competidores if c["homeAway"] == "home")
                away = next(c for c in competidores if c["homeAway"] == "away")

                nombre_local  = home["team"]["displayName"]
                nombre_visita = away["team"]["displayName"]
                goles_local   = int(home["score"])
                goles_visita  = int(away["score"])

                cod_local  = _codigo(nombre_local)
                cod_visita = _codigo(nombre_visita)

                if not cod_local or not cod_visita:
                    errores.append("Sin mapeo: {} vs {}".format(nombre_local, nombre_visita))
                    continue

                partido = conn.execute("""
                    SELECT id, goles_local, goles_visita FROM partidos
                    WHERE equipo_local = ? AND equipo_visita = ?
                      AND fase = 'grupos'
                """, (cod_local, cod_visita)).fetchone()

                if not partido:
                    continue

                if (partido["goles_local"] == goles_local and
                        partido["goles_visita"] == goles_visita):
                    continue

                conn.execute("""
                    UPDATE partidos
                    SET goles_local = ?, goles_visita = ?, abierto = FALSE
                    WHERE id = ?
                """, (goles_local, goles_visita, partido["id"]))
                conn.commit()

                recalcular_partido(partido["id"])
                actualizados += 1

            except Exception as e:
                errores.append(str(e))

    return {"actualizados": actualizados, "errores": errores}


# -- Goleadores y tarjetas -------------------------------------------------

def scrape_goleadores_tarjetas() -> dict:
    """
    Obtiene tabla de goleadores y tarjetas desde ESPN Stats API.
    Reemplaza todos los datos en DB con los valores actuales.
    Retorna {"goleadores": N, "tarjetas": N, "errores": [...]}
    """
    errores = []

    try:
        resp = requests.get(ESPN_STATS, timeout=10, headers=HEADERS,
                            params={"limit": 20})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"goleadores": 0, "tarjetas": 0, "errores": [str(e)]}

    # ESPN devuelve lista de categorias bajo data["leaders"]
    categories = data.get("leaders", [])

    goleadores_data  = []
    amarillas_data   = []
    rojas_data       = []

    for cat in categories:
        name = cat.get("name", "").lower()
        leaders = cat.get("leaders", [])

        if name in ("goals", "goalsscored"):
            for entry in leaders:
                try:
                    jugador = entry["athlete"]["displayName"]
                    equipo  = entry.get("team", {}).get("abbreviation", "")
                    goles   = int(float(entry.get("value", 0)))
                    goleadores_data.append((jugador, equipo, goles))
                except Exception as e:
                    errores.append("goleador: {}".format(e))

        elif name in ("yellowcards", "yellowcard"):
            for entry in leaders:
                try:
                    jugador   = entry["athlete"]["displayName"]
                    equipo    = entry.get("team", {}).get("abbreviation", "")
                    amarillas = int(float(entry.get("value", 0)))
                    amarillas_data.append((jugador, equipo, amarillas))
                except Exception as e:
                    errores.append("amarilla: {}".format(e))

        elif name in ("redcards", "redcard"):
            for entry in leaders:
                try:
                    jugador = entry["athlete"]["displayName"]
                    equipo  = entry.get("team", {}).get("abbreviation", "")
                    rojas   = int(float(entry.get("value", 0)))
                    rojas_data.append((jugador, equipo, rojas))
                except Exception as e:
                    errores.append("roja: {}".format(e))

    with get_db() as conn:
        # -- Goleadores: reemplazar tabla entera
        if goleadores_data:
            conn.execute("DELETE FROM goleadores")
            conn.executemany(
                "INSERT INTO goleadores (jugador, equipo, goles) VALUES (?, ?, ?)",
                goleadores_data
            )

        # -- Tarjetas: merge por jugador (upsert)
        # Combinar amarillas y rojas en un dict keyed por (jugador, equipo)
        tarjetas_map = {}
        for jugador, equipo, n in amarillas_data:
            tarjetas_map.setdefault((jugador, equipo), {"amarillas": 0, "rojas": 0})
            tarjetas_map[(jugador, equipo)]["amarillas"] = n
        for jugador, equipo, n in rojas_data:
            tarjetas_map.setdefault((jugador, equipo), {"amarillas": 0, "rojas": 0})
            tarjetas_map[(jugador, equipo)]["rojas"] = n

        if tarjetas_map:
            conn.execute("DELETE FROM tarjetas")
            conn.executemany(
                "INSERT INTO tarjetas (jugador, equipo, amarillas, rojas) VALUES (?, ?, ?, ?)",
                [(j, e, v["amarillas"], v["rojas"]) for (j, e), v in tarjetas_map.items()]
            )

        conn.commit()

    return {
        "goleadores": len(goleadores_data),
        "tarjetas":   len(tarjetas_map) if 'tarjetas_map' in dir() else 0,
        "errores":    errores,
    }


# -- Scrape completo (resultados + stats) ---------------------------------

def scrape_todo() -> dict:
    """Corre scrape_resultados y scrape_goleadores_tarjetas en secuencia."""
    res1 = scrape_resultados()
    res2 = scrape_goleadores_tarjetas()
    return {
        "resultados":  res1,
        "goleadores":  res2.get("goleadores", 0),
        "tarjetas":    res2.get("tarjetas", 0),
        "errores":     res1.get("errores", []) + res2.get("errores", []),
    }
