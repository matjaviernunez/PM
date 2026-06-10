"""
migrate_fix_horas_completo.py
Resetea TODAS las fechas/horas de grupos a hora Ecuador (UTC-5).
Seguro correrlo multiples veces - siempre deja los valores correctos.
"""
from db import get_db

UPDATES = [
    ('2026-06-11', '14:00', 'MEX', 'RSA'),  # MEX vs RSA
    ('2026-06-11', '21:00', 'KOR', 'CZE'),  # KOR vs CZE
    ('2026-06-18', '11:00', 'CZE', 'RSA'),  # CZE vs RSA
    ('2026-06-18', '20:00', 'MEX', 'KOR'),  # MEX vs KOR
    ('2026-06-24', '20:00', 'CZE', 'MEX'),  # CZE vs MEX
    ('2026-06-24', '20:00', 'RSA', 'KOR'),  # RSA vs KOR
    ('2026-06-12', '14:00', 'CAN', 'BIH'),  # CAN vs BIH
    ('2026-06-13', '14:00', 'QAT', 'SUI'),  # QAT vs SUI
    ('2026-06-18', '14:00', 'SUI', 'BIH'),  # SUI vs BIH
    ('2026-06-18', '17:00', 'CAN', 'QAT'),  # CAN vs QAT
    ('2026-06-24', '14:00', 'SUI', 'CAN'),  # SUI vs CAN
    ('2026-06-24', '14:00', 'BIH', 'QAT'),  # BIH vs QAT
    ('2026-06-13', '17:00', 'BRA', 'MAR'),  # BRA vs MAR
    ('2026-06-13', '20:00', 'HAI', 'SCO'),  # HAI vs SCO
    ('2026-06-19', '17:00', 'SCO', 'MAR'),  # SCO vs MAR
    ('2026-06-19', '19:30', 'BRA', 'HAI'),  # BRA vs HAI
    ('2026-06-24', '17:00', 'SCO', 'BRA'),  # SCO vs BRA
    ('2026-06-24', '17:00', 'MAR', 'HAI'),  # MAR vs HAI
    ('2026-06-12', '20:00', 'USA', 'PAR'),  # USA vs PAR
    ('2026-06-13', '23:00', 'AUS', 'TUR'),  # AUS vs TUR
    ('2026-06-19', '14:00', 'USA', 'AUS'),  # USA vs AUS
    ('2026-06-19', '22:00', 'TUR', 'PAR'),  # TUR vs PAR
    ('2026-06-25', '21:00', 'TUR', 'USA'),  # TUR vs USA
    ('2026-06-25', '21:00', 'PAR', 'AUS'),  # PAR vs AUS
    ('2026-06-14', '12:00', 'GER', 'CUW'),  # GER vs CUW
    ('2026-06-14', '18:00', 'CIV', 'ECU'),  # CIV vs ECU
    ('2026-06-20', '15:00', 'GER', 'CIV'),  # GER vs CIV
    ('2026-06-20', '19:00', 'ECU', 'CUW'),  # ECU vs CUW
    ('2026-06-25', '15:00', 'CUW', 'CIV'),  # CUW vs CIV
    ('2026-06-25', '15:00', 'ECU', 'GER'),  # ECU vs GER
    ('2026-06-14', '15:00', 'NED', 'JPN'),  # NED vs JPN
    ('2026-06-14', '21:00', 'SWE', 'TUN'),  # SWE vs TUN
    ('2026-06-20', '12:00', 'NED', 'SWE'),  # NED vs SWE
    ('2026-06-20', '23:00', 'TUN', 'JPN'),  # TUN vs JPN
    ('2026-06-25', '18:00', 'JPN', 'SWE'),  # JPN vs SWE
    ('2026-06-25', '18:00', 'TUN', 'NED'),  # TUN vs NED
    ('2026-06-15', '14:00', 'BEL', 'EGY'),  # BEL vs EGY
    ('2026-06-15', '20:00', 'IRN', 'NZL'),  # IRN vs NZL
    ('2026-06-21', '14:00', 'BEL', 'IRN'),  # BEL vs IRN
    ('2026-06-21', '20:00', 'NZL', 'EGY'),  # NZL vs EGY
    ('2026-06-26', '22:00', 'EGY', 'IRN'),  # EGY vs IRN
    ('2026-06-26', '22:00', 'NZL', 'BEL'),  # NZL vs BEL
    ('2026-06-15', '11:00', 'ESP', 'CPV'),  # ESP vs CPV
    ('2026-06-15', '17:00', 'KSA', 'URU'),  # KSA vs URU
    ('2026-06-21', '11:00', 'ESP', 'KSA'),  # ESP vs KSA
    ('2026-06-21', '17:00', 'URU', 'CPV'),  # URU vs CPV
    ('2026-06-26', '19:00', 'CPV', 'KSA'),  # CPV vs KSA
    ('2026-06-26', '19:00', 'URU', 'ESP'),  # URU vs ESP
    ('2026-06-16', '14:00', 'FRA', 'SEN'),  # FRA vs SEN
    ('2026-06-16', '17:00', 'IRQ', 'NOR'),  # IRQ vs NOR
    ('2026-06-22', '16:00', 'FRA', 'IRQ'),  # FRA vs IRQ
    ('2026-06-22', '19:00', 'NOR', 'SEN'),  # NOR vs SEN
    ('2026-06-26', '14:00', 'NOR', 'FRA'),  # NOR vs FRA
    ('2026-06-26', '14:00', 'SEN', 'IRQ'),  # SEN vs IRQ
    ('2026-06-16', '20:00', 'ARG', 'ALG'),  # ARG vs ALG
    ('2026-06-16', '23:00', 'AUT', 'JOR'),  # AUT vs JOR
    ('2026-06-22', '12:00', 'ARG', 'AUT'),  # ARG vs AUT
    ('2026-06-22', '22:00', 'JOR', 'ALG'),  # JOR vs ALG
    ('2026-06-27', '21:00', 'JOR', 'ARG'),  # JOR vs ARG
    ('2026-06-27', '21:00', 'ALG', 'AUT'),  # ALG vs AUT
    ('2026-06-17', '12:00', 'POR', 'COD'),  # POR vs COD
    ('2026-06-17', '21:00', 'UZB', 'COL'),  # UZB vs COL
    ('2026-06-23', '12:00', 'POR', 'UZB'),  # POR vs UZB
    ('2026-06-23', '21:00', 'COL', 'COD'),  # COL vs COD
    ('2026-06-27', '18:30', 'COL', 'POR'),  # COL vs POR
    ('2026-06-27', '18:30', 'COD', 'UZB'),  # COD vs UZB
    ('2026-06-17', '15:00', 'ENG', 'CRO'),  # ENG vs CRO
    ('2026-06-17', '18:00', 'GHA', 'PAN'),  # GHA vs PAN
    ('2026-06-23', '15:00', 'ENG', 'GHA'),  # ENG vs GHA
    ('2026-06-23', '18:00', 'PAN', 'CRO'),  # PAN vs CRO
    ('2026-06-27', '16:00', 'PAN', 'ENG'),  # PAN vs ENG
    ('2026-06-27', '16:00', 'CRO', 'GHA'),  # CRO vs GHA
]

with get_db() as conn:
    for fecha, hora, local, visita in UPDATES:
        conn.execute(
            "UPDATE partidos SET fecha=?, hora=? WHERE equipo_local=? AND equipo_visita=? AND fase='grupos'",
            (fecha, hora, local, visita)
        )
    conn.commit()
print(f"Actualizados 72 partidos de grupos a hora Ecuador.")