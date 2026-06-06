"""
scraper/runner.py — Obtiene resultados del Mundial 2026 desde ESPN API.
No requiere API key ni Playwright.

ESPN endpoint:
  https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard
"""

import requests
from db import get_db
from game.scoring import recalcular_partido

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

# Mapeo de nombres ESPN → códigos FIFA usados en nuestra DB
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
    "Türkiye":              "TUR",
    "Germany":              "GER",
    "Curaçao":              "CUW",
    "Curacao":              "CUW",
    "Ivory Coast":          "CIV",
    "Cote d'Ivoire":        "CIV",
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


def scrape_resultados() -> dict:
    """
    Llama al ESPN API, detecta partidos finalizados y actualiza la DB.
    Retorna {"actualizados": N, "errores": [...]}
    """
    try:
        resp = requests.get(ESPN_URL, timeout=10,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"actualizados": 0, "errores": [str(e)]}

    eventos = data.get("events", [])
    actualizados = 0
    errores = []

    with get_db() as conn:
        for evento in eventos:
            try:
                status = evento.get("status", {})
                # Solo procesar partidos finalizados
                if status.get("type", {}).get("completed") is not True:
                    continue

                competidores = evento["competitions"][0]["competitors"]
                home = next(c for c in competidores if c["homeAway"] == "home")
                away = next(c for c in competidores if c["homeAway"] == "away")

                nombre_local   = home["team"]["displayName"]
                nombre_visita  = away["team"]["displayName"]
                goles_local    = int(home["score"])
                goles_visita   = int(away["score"])

                cod_local  = _codigo(nombre_local)
                cod_visita = _codigo(nombre_visita)

                if not cod_local or not cod_visita:
                    errores.append(f"Sin mapeo: {nombre_local} vs {nombre_visita}")
                    continue

                # Buscar el partido en nuestra DB
                partido = conn.execute("""
                    SELECT id, goles_local, goles_visita FROM partidos
                    WHERE equipo_local = ? AND equipo_visita = ?
                      AND fase = 'grupos'
                """, (cod_local, cod_visita)).fetchone()

                if not partido:
                    continue

                # Solo actualizar si no tenía resultado o cambió
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
