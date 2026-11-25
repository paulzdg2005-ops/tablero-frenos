"""
SIMULADOR DE LA FLOTA (datos declarados como SIMULADOS)

Genera, para 5 buses, las mediciones de las 5 variables de condición con su frecuencia real
(diaria, semanal o cada 5.000 km), con ruido de medición, y los eventos de mantenimiento.

Escenarios inyectados (a la fecha de corte final):
  B-01  Condición normal (referencia)
  B-02  Forros llegando al punto P (alerta)
  B-03  Fuga progresiva en mangueras SIN intervención: escenario completo de normal a paro
  B-04  Secador de aire saturándose (alerta)
  B-05  Freno que arrastra (ΔT en alerta) y compresor desgastándose (vigilancia)

Además hay episodios pasados que sí se corrigieron (generan órdenes ejecutadas, MTTR y costos)
y algunas fallas en ruta (correctivos) para calcular el MTBF.
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from config import CORRECTIVO_EN_RUTA, FLOTA, RCM, VARIABLES

INICIO = date(2026, 1, 5)
FIN = date(2026, 11, 21)

# ---------------------------------------------------------------- escenarios por bus
PARAMS = {
    "B-01": {"odo": 182_400, "kmd": 266, "desgaste": 0.30, "forro_final": 15.2, "recarga_base": 25.5, "recarga_deriva": 0.000015},
    "B-02": {"odo": 214_900, "kmd": 261, "desgaste": 0.33, "forro_final": 9.5, "recarga_base": 26.0, "recarga_deriva": 0.000020},
    "B-03": {"odo": 151_300, "kmd": 268, "desgaste": 0.29, "forro_final": 13.4, "recarga_base": 25.0, "recarga_deriva": 0.000020},
    "B-04": {"odo": 236_700, "kmd": 259, "desgaste": 0.30, "forro_final": 12.1, "recarga_base": 26.5, "recarga_deriva": 0.000025},
    "B-05": {"odo": 198_200, "kmd": 263, "desgaste": 0.32, "forro_final": 11.0, "recarga_base": 26.0, "recarga_deriva": 0.000105},
}

# Episodios de deterioro progresivo: (bus, variable, inicio, base, amplitud, k por día, se_repara)
#   valor = base + A·(e^{k·t} − 1),  t = días desde el inicio del episodio
EPISODIOS = [
    ("B-01", "fuga", date(2026, 3, 2), 0.03, 0.004, 0.10, True),
    ("B-04", "fuga", date(2026, 7, 6), 0.03, 0.004, 0.09, True),
    ("B-03", "fuga", FIN - timedelta(days=40), 0.03, 0.004, 0.10, False),   # escenario de demostración
    ("B-02", "agua", date(2026, 4, 13), 1.5, 0.6, 0.11, True),
    ("B-04", "agua", FIN - timedelta(days=30), 1.5, 0.6, 0.105, False),
    ("B-03", "dT", date(2026, 2, 9), 6.0, 2.0, 0.085, True),
    ("B-05", "dT", FIN - timedelta(days=36), 6.0, 2.0, 0.078, False),
]

# Fallas no progresivas (correctivos): (bus, fecha, modo, en_ruta, descripción)
CORRECTIVOS = [
    ("B-02", date(2026, 8, 14), 8, True, "Manguera rota en ruta (roce contra el chasis)"),
    ("B-04", date(2026, 6, 3), 4, False, "Testigo ABS encendido en la prueba diaria: bus no despachado"),
    ("B-01", date(2026, 4, 22), 6, False, "Alarma de baja presión no sonó en la prueba diaria"),
    ("B-05", date(2026, 9, 17), 10, True, "Válvula relé agarrotada: frenadas bruscas en ruta"),
    ("B-03", date(2026, 10, 7), 5, False, "Freno de estacionamiento no retuvo en la prueba de tirón"),
]


def dias_operacion():
    d, out = INICIO, []
    while d <= FIN:
        if d.weekday() != 6:  # opera de lunes a sábado (≈ 300 días/año)
            out.append(d)
        d += timedelta(days=1)
    return out


def _simular_forros(odos, insp_idx, t0, desgaste, rng, medir=True):
    """Devuelve (mediciones, reemplazos). Reemplazo preventivo al detectar alerta (≤ 10 mm)."""
    alerta = VARIABLES["espesor"]["alerta"]
    nuevo = VARIABLES["espesor"]["nominal"]
    km_instal = odos[0] - (nuevo - t0) / desgaste * 1000
    med, reemplazos = [], []
    for i in insp_idx:
        verdadero = nuevo - desgaste * (odos[i] - km_instal) / 1000
        valor = verdadero + (rng.normal(0, 0.15) if medir else 0)
        med.append((i, round(valor, 2), verdadero))
        if verdadero <= alerta and i != len(odos) - 1 and i + 1 < len(odos):
            reemplazos.append(i + 1)
            km_instal = odos[i + 1]
    return med, reemplazos


def simular(semilla: int = 7):
    rng = np.random.default_rng(semilla)
    dias = dias_operacion()
    n = len(dias)
    filas, eventos, pruebas = [], [], []

    for bus, p in PARAMS.items():
        kms = np.clip(rng.normal(p["kmd"], 12, n), 220, 300)
        odos = p["odo"] + np.cumsum(kms) - kms[0]

        # Taller cada 5.000 km; la última visita coincide con la fecha final (estado actual)
        insp_idx, cur = [n - 1], n - 1
        while True:
            prev = [j for j in range(cur) if odos[j] <= odos[cur] - 5_000]
            if not prev:
                break
            cur = prev[-1]
            insp_idx.append(cur)
        insp_idx = sorted(insp_idx)

        # --- forros: buscar el espesor inicial que lleva al valor final deseado
        mejor = None
        for t0 in np.arange(7.0, 18.0, 0.02):
            med, _ = _simular_forros(odos, insp_idx, t0, p["desgaste"], rng, medir=False)
            err = abs(med[-1][2] - p["forro_final"])
            if mejor is None or err < mejor[0]:
                mejor = (err, t0)
        med, reemplazos = _simular_forros(odos, insp_idx, mejor[1], p["desgaste"], np.random.default_rng(semilla + list(PARAMS).index(bus)))
        for i, valor, _ in med:
            filas.append((dias[i], bus, odos[i], "espesor", valor))
        for i in reemplazos:
            eventos.append(_evento(dias[i], bus, odos[i], 1, "espesor", "Preventivo a condición", False,
                                   "Cambio de forros al detectar el punto P (≤ 10 mm)"))

        # --- recarga del compresor (mismas visitas a taller)
        for i in insp_idx:
            v = p["recarga_base"] + p["recarga_deriva"] * (odos[i] - odos[0]) + rng.normal(0, 0.7)
            filas.append((dias[i], bus, odos[i], "recarga", round(v, 1)))

        # --- variables diarias / semanales con episodios
        for var, cada in (("fuga", 1), ("agua", 1), ("dT", 6)):
            eps = [e for e in EPISODIOS if e[0] == bus and e[1] == var]
            usados, activo = set(), None
            indices = list(range(0, n, cada))
            if indices[-1] != n - 1:
                indices.append(n - 1)
            for i in indices:
                d = dias[i]
                if activo is None:
                    cand = [e for e in eps if e[2] <= d and e not in usados]
                    if cand:
                        activo = cand[0]
                        usados.add(activo)
                if var == "fuga":
                    base = max(0.0, rng.normal(0.03, 0.008))
                elif var == "agua":
                    base = max(0.0, rng.normal(1.5, 1.0))
                else:
                    base = abs(rng.normal(6.0, 3.5))
                valor = base
                if activo is not None:
                    t = (d - activo[2]).days
                    valor = base + activo[4] * (np.exp(activo[5] * t) - 1)
                valor = round(valor, 3 if var == "fuga" else 1)
                filas.append((d, bus, odos[i], var, valor))
                cfg = VARIABLES[var]
                if activo is not None and activo[6] and valor >= cfg["alerta"]:
                    j = min(i + 1, n - 1)
                    eventos.append(_evento(dias[j], bus, odos[j], cfg["modo"], var, "Preventivo a condición", False,
                                           f"Corrección al detectar el punto P de {cfg['corto'].lower()}"))
                    activo = None

        # --- correctivos y pruebas pasa / no pasa
        for b, f, modo, en_ruta, desc in CORRECTIVOS:
            if b == bus:
                i = min(range(n), key=lambda k: abs((dias[k] - f).days))
                eventos.append(_evento(dias[i], bus, odos[i], modo, None,
                                       "Correctivo en ruta" if en_ruta else "Correctivo (detectado en prueba diaria)",
                                       en_ruta, desc))
        dias_falla = {}
        for b, f, modo, _, _ in CORRECTIVOS:
            if b == bus:
                dias_falla[modo] = min(dias, key=lambda k: abs((k - f).days))
        for i in range(n):
            for prueba, modo in (("alarma", 6), ("resorte", 5), ("abs", 4)):
                falla = dias_falla.get(modo) == dias[i]
                pruebas.append((dias[i], bus, prueba, "No pasa" if falla else "Pasa"))

    datos = pd.DataFrame(filas, columns=["fecha", "bus", "km", "variable", "valor"])
    datos["fecha"] = pd.to_datetime(datos["fecha"])
    datos["km"] = datos["km"].round(0)
    datos["origen"] = "Simulado"
    datos = datos.sort_values(["bus", "variable", "fecha"]).reset_index(drop=True)

    ev = pd.DataFrame(eventos)
    ev["fecha"] = pd.to_datetime(ev["fecha"])
    ev = ev.sort_values(["fecha", "bus"]).reset_index(drop=True)

    pr = pd.DataFrame(pruebas, columns=["fecha", "bus", "prueba", "resultado"])
    pr["fecha"] = pd.to_datetime(pr["fecha"])
    pr["origen"] = "Simulado"
    return datos, ev, pr


def _evento(fecha, bus, km, modo, variable, tipo, en_ruta, descripcion):
    r = RCM[modo]
    horas = r["horas"] + (CORRECTIVO_EN_RUTA["horas_extra"] if en_ruta else 0)
    costo = r["costo"] + (CORRECTIVO_EN_RUTA["costo_extra"] if en_ruta else 0)
    return {"fecha": fecha, "bus": bus, "km": round(km), "modo": modo, "variable": variable, "tipo": tipo,
            "detiene_servicio": tipo.startswith("Correctivo"), "descripcion": descripcion,
            "tarea": r["tarea"], "horas_paro": horas, "costo": costo,
            "origen": "Simulado (horas y costos: supuestos)"}


if __name__ == "__main__":
    d, e, p = simular()
    print(d.groupby(["bus", "variable"]).size().unstack())
    print(e[["fecha", "bus", "modo", "tipo", "horas_paro", "costo"]])
    print(d.sort_values("fecha").groupby(["bus", "variable"]).tail(1).pivot(index="bus", columns="variable", values="valor"))
