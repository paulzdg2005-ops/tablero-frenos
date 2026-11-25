"""
MOTOR DE CÁLCULO
Estado por variable, índice de salud, tendencias y tiempo hasta el umbral,
órdenes de trabajo sugeridas e indicadores de proceso.
"""
import numpy as np
import pandas as pd

from config import (BANDAS_IS, METAS, MODOS, NIVELES, OPERACION, ORDEN_VARIABLES, PESOS, PRIORIDADES,
                    PRUEBAS, RCM, SUBINDICE_NIVEL, VARIABLES)


# ------------------------------------------------------------------ niveles y sub-índice
def nivel(var, x):
    if x is None or pd.isna(x):
        return "Sin dato"
    c = VARIABLES[var]
    peor = (lambda a, b: a <= b) if c["sentido"] == "baja" else (lambda a, b: a >= b)
    if peor(x, c["alarma"]):
        return "Alarma"
    if peor(x, c["alerta"]):
        return "Alerta"
    if peor(x, c["vigilancia"]):
        return "Vigilancia"
    return "Normal"


def subindice(var, x):
    """Interpolación lineal: nominal=100, vigilancia=80, alerta=60, alarma=20, F=0."""
    if x is None or pd.isna(x):
        return np.nan
    c = VARIABLES[var]
    puntos = [(c[k], SUBINDICE_NIVEL[k]) for k in ("nominal", "vigilancia", "alerta", "alarma", "F")]
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    if c["sentido"] == "baja":  # np.interp necesita x creciente
        xs, ys = xs[::-1], ys[::-1]
    return float(np.interp(x, xs, ys))


def nivel_is(valor):
    for limite, nom in BANDAS_IS:
        if valor >= limite:
            return nom
    return "Alarma"


def peor(*niveles):
    orden = {n: i for i, n in enumerate(NIVELES)}
    validos = [n for n in niveles if n in orden]
    return max(validos, key=lambda n: orden[n]) if validos else "Sin dato"


# ------------------------------------------------------------------ estado de un bus
def ultimo_valor(datos, bus, var, corte):
    d = datos[(datos.bus == bus) & (datos.variable == var) & (datos.fecha <= corte)]
    if d.empty:
        return None
    return d.iloc[-1]


def estado_bus(datos, pruebas, bus, corte):
    filas = []
    for v in ORDEN_VARIABLES:
        u = ultimo_valor(datos, bus, v, corte)
        x = None if u is None else float(u["valor"])
        s = subindice(v, x)
        filas.append({"var": v, "Variable": VARIABLES[v]["nombre"], "Valor": x, "Unidad": VARIABLES[v]["unidad"],
                      "Nivel": nivel(v, x), "Sub-índice": s, "Peso": PESOS[v],
                      "Aporte": (s * PESOS[v]) if not np.isnan(s) else np.nan,
                      "Fecha": None if u is None else u["fecha"], "km": None if u is None else u["km"],
                      "Origen": None if u is None else u["origen"]})
    tabla = pd.DataFrame(filas)
    validas = tabla.dropna(subset=["Sub-índice"])
    indice = float((validas["Sub-índice"] * validas["Peso"]).sum() / validas["Peso"].sum()) if len(validas) else np.nan

    # Pruebas pasa / no pasa del día
    pr = pruebas[(pruebas.bus == bus) & (pruebas.fecha <= corte)]
    hoy = pr[pr.fecha == pr.fecha.max()].drop_duplicates("prueba", keep="last") if len(pr) else pr
    fallas = hoy[hoy.resultado == "No pasa"]
    nivel_pruebas = "Alarma" if len(fallas) else "Normal"  # todas las pruebas cubren modos con S ≥ 8

    sem = peor(nivel_is(indice), *tabla["Nivel"].tolist(), nivel_pruebas)
    return {"tabla": tabla, "indice": indice, "nivel_indice": nivel_is(indice), "semaforo": sem,
            "pruebas": hoy, "fallas_prueba": fallas}


def estado_flota(datos, pruebas, corte, buses):
    out = []
    for b in buses:
        e = estado_bus(datos, pruebas, b, corte)
        t = e["tabla"]
        criticas = t[t["Nivel"].isin(["Alerta", "Alarma"])]["Variable"].tolist()
        out.append({"bus": b, "indice": e["indice"], "semaforo": e["semaforo"],
                    "criticas": criticas + [PRUEBAS[p]["nombre"] for p in e["fallas_prueba"]["prueba"]]})
    return out


# ------------------------------------------------------------------ tendencias
def tramo_actual(datos, eventos, bus, var, corte):
    """Mediciones desde la última intervención que restableció la variable."""
    d = datos[(datos.bus == bus) & (datos.variable == var) & (datos.fecha <= corte)].copy()
    if eventos is not None and len(eventos):
        ev = eventos[(eventos.bus == bus) & (eventos.variable == var) & (eventos.fecha <= corte)]
        if len(ev):
            f_ev = ev.fecha.max()
            # el mismo día de la reparación solo cuenta la última medición (la de verificación después de reparar)
            d = pd.concat([d[d.fecha == f_ev].tail(1), d[d.fecha > f_ev]])
    return d


def _r2(y, yhat):
    ss = ((y - y.mean()) ** 2).sum()
    return float(1 - ((y - yhat) ** 2).sum() / ss) if ss > 0 else np.nan


R2_MINIMO = 0.5  # por debajo, la tendencia no explica los datos: se trata como ruido


def ventana(var):
    """Puntos usados en el ajuste según la frecuencia de medición (≈ últimos 1–2 meses o el tramo completo)."""
    f = VARIABLES[var]["frec_km"]
    return 30 if f <= 300 else (10 if f <= 2_000 else 15)


def ajustar(var, tramo, max_puntos=None):
    """Ajuste lineal y exponencial contra km. Devuelve ambos y el elegido por la configuración."""
    c = VARIABLES[var]
    t = tramo.tail(max_puntos or ventana(var))
    if len(t) < 3 or t["km"].nunique() < 3:  # se necesitan al menos 3 odómetros distintos
        return None
    x0 = float(t["km"].iloc[0])
    x = t["km"].to_numpy(float) - x0
    y = t["valor"].to_numpy(float)

    # lineal
    b1, b0 = np.polyfit(x, y, 1)
    lin = {"tipo": "lineal", "a": b0, "b": b1, "r2": _r2(y, b0 + b1 * x)}

    # exponencial y = a·e^(b·x)   (se desplaza para que todos los valores sean positivos)
    eps = 0.02 * abs(c["alerta"] - c["nominal"]) + 1e-6
    if c["sentido"] == "sube":
        ylog = np.log(np.maximum(y, 0) + eps)
        k, lna = np.polyfit(x, ylog, 1)
        exp_ = {"tipo": "exponencial", "a": float(np.exp(lna)), "b": float(k), "eps": eps}
        exp_["r2"] = _r2(y, exp_["a"] * np.exp(k * x) - eps)
    else:
        exp_ = {"tipo": "exponencial", "a": np.nan, "b": np.nan, "r2": np.nan, "eps": 0}

    elegido = exp_ if c["tendencia"] == "exponencial" else lin
    return {"x0": x0, "x_ult": float(x[-1]), "lineal": lin, "exponencial": exp_, "modelo": elegido, "n": len(t)}


def predecir(aj, km_rel, modelo=None):
    m = modelo or aj["modelo"]
    if m["tipo"] == "lineal":
        return m["a"] + m["b"] * km_rel
    return m["a"] * np.exp(m["b"] * km_rel) - m["eps"]


def km_hasta(var, aj, umbral, modelo=None):
    """km desde la última medición hasta que la tendencia cruza el umbral (None si no se dirige hacia él)."""
    c = VARIABLES[var]
    m = modelo or aj["modelo"]
    xu = aj["x_ult"]
    actual = predecir(aj, xu, m)
    ya = actual <= umbral if c["sentido"] == "baja" else actual >= umbral
    if ya:
        return 0.0
    if m["tipo"] == "lineal":
        if m["b"] == 0 or (c["sentido"] == "baja" and m["b"] > 0) or (c["sentido"] == "sube" and m["b"] < 0):
            return None
        x = (umbral - m["a"]) / m["b"]
    else:
        if m["b"] <= 0 or m["a"] <= 0:
            return None
        x = np.log((umbral + m["eps"]) / m["a"]) / m["b"]
    rest = x - xu
    return float(rest) if rest >= 0 else 0.0


def analisis_tendencia(datos, eventos, bus, var, corte):
    c = VARIABLES[var]
    tr = tramo_actual(datos, eventos, bus, var, corte)
    aj = ajustar(var, tr)
    if aj is None:
        return {"tramo": tr, "ajuste": None}
    k_alerta = km_hasta(var, aj, c["alerta"])
    k_alarma = km_hasta(var, aj, c["alarma"])
    kmd = OPERACION["km_dia"]
    reac = OPERACION["km_reaccion"]
    pf_min = c["pf_km"][0]
    # La última medición manda: si ya cruzó un umbral, la distancia a ese umbral es 0
    nivel_ult = nivel(var, float(tr["valor"].iloc[-1]))
    if nivel_ult == "Alarma":
        k_alerta = k_alarma = 0.0
    elif nivel_ult == "Alerta":
        k_alerta = 0.0
    significativa = aj["modelo"]["r2"] >= R2_MINIMO if not np.isnan(aj["modelo"]["r2"]) else False
    if not significativa and nivel_ult in ("Normal", "Vigilancia"):
        k_alerta = k_alarma = None
    # Decisión
    if k_alarma is None:
        decision = ("Sin tendencia hacia la alarma", "La variable no se está deteriorando en el tramo actual. Seguir con la frecuencia normal.")
    elif k_alarma == 0:
        decision = ("Ya en alarma", "La tendencia ya alcanzó el umbral de paro: no despachar el bus y ejecutar la tarea del RCM.")
    elif k_alarma < reac:
        decision = ("No alcanza", f"Faltan {k_alarma:,.0f} km, menos que el tiempo de reacción ({reac} km). Intervenir de inmediato.")
    elif k_alarma < reac + c["frec_km"]:
        decision = ("Intervenir antes de la próxima medición",
                    f"Faltan {k_alarma:,.0f} km; la próxima medición sería en {c['frec_km']:,} km. Programar la intervención ya.")
    else:
        decision = ("Alcanza para planear",
                    f"Faltan {k_alarma:,.0f} km (≈ {k_alarma / kmd:,.0f} días). Hay margen para programar dentro de {k_alarma - reac:,.0f} km.")
    # Cuánto del intervalo P-F se ha consumido (si ya pasó el punto P)
    consumo = None
    paso_p = tr[(tr["valor"] <= c["alerta"]) if c["sentido"] == "baja" else (tr["valor"] >= c["alerta"])]
    if len(paso_p):
        km_desde_p = float(tr["km"].iloc[-1] - paso_p["km"].iloc[0])
        consumo = km_desde_p / pf_min * 100
    return {"tramo": tr, "ajuste": aj, "km_alerta": k_alerta, "km_alarma": k_alarma, "significativa": significativa,
            "dias_alarma": None if k_alarma is None else k_alarma / kmd,
            "decision": decision, "consumo_pf": consumo}


# ------------------------------------------------------------------ órdenes de trabajo
def prioridad(modo, niv):
    s = MODOS[modo]["S"]
    if niv == "Alarma":
        return "P1" if s >= 9 else "P2"
    if niv == "Alerta":
        return "P2" if s >= 9 else "P3"
    return None


def ordenes(datos, eventos, pruebas, corte, buses):
    ots, avisos = [], []
    n = 1
    for b in buses:
        e = estado_bus(datos, pruebas, b, corte)
        for _, r in e["tabla"].iterrows():
            v, niv = r["var"], r["Nivel"]
            c = VARIABLES[v]
            if niv == "Vigilancia":
                avisos.append({"Bus": b, "Variable": c["nombre"], "Valor": r["Valor"], "Unidad": c["unidad"],
                               "Acción": "Aumentar la frecuencia de medición y revisar la tendencia"})
                continue
            if niv not in ("Alerta", "Alarma"):
                continue
            modo = c["modo"]
            pr = prioridad(modo, niv)
            t = analisis_tendencia(datos, eventos, b, v, corte)
            dias = PRIORIDADES[pr]["dias"]
            ka = t.get("km_alarma")
            if pr != "P1" and ka:  # nunca más tarde que (alarma − tiempo de reacción)
                dias = min(dias, max(0, int((ka - OPERACION["km_reaccion"]) // OPERACION["km_dia"])))
            ots.append(_ot(n, b, corte, modo, pr, dias, niv, f"{c['nombre']}: {r['Valor']:g} {c['unidad']}".replace(".", ","),
                           c["fuentes"]["alarma" if niv == "Alarma" else "alerta"], t.get("km_alarma"), r["Origen"]))
            n += 1
        for _, f in e["fallas_prueba"].iterrows():
            p = PRUEBAS[f["prueba"]]
            modo = p["modo"]
            pr = "P1" if MODOS[modo]["S"] >= 9 else "P2"
            ots.append(_ot(n, b, corte, modo, pr, PRIORIDADES[pr]["dias"], "Alarma",
                           f"{p['nombre']}: NO PASA", p["fuente"], None, f["origen"]))
            n += 1
    orden = {"P1": 0, "P2": 1, "P3": 2}
    ots.sort(key=lambda o: (orden[o["prioridad"]], -o["NPR"]))
    return ots, avisos


def _ot(n, bus, corte, modo, pr, dias, niv, hallazgo, fuente, km_alarma, origen):
    r, m = RCM[modo], MODOS[modo]
    return {"id": f"OT-{corte:%y%m%d}-{n:02d}", "bus": bus, "nivel": niv, "hallazgo": hallazgo, "fuente_umbral": fuente,
            "modo": modo, "modo_nombre": m["nombre"], "efecto": m["efecto"], "S": m["S"], "NPR": m["NPR"],
            "prioridad": pr, "prioridad_nombre": PRIORIDADES[pr]["nombre"], "regla": PRIORIDADES[pr]["regla"],
            "plazo": PRIORIDADES[pr]["plazo"], "fecha_limite": corte + pd.Timedelta(days=dias),
            "tarea": r["tarea"], "tipo_tarea": r["tipo"], "consecuencia": r["consecuencia"], "recurso": r["recurso"],
            "horas": r["horas"], "costo": r["costo"], "km_alarma": km_alarma, "origen": origen}


# ------------------------------------------------------------------ indicadores
def indicadores(datos, eventos, corte, buses):
    ev = eventos[(eventos.fecha <= corte) & (eventos.bus.isin(buses))].copy()
    d = datos[(datos.fecha <= corte) & (datos.bus.isin(buses))]
    dias = pd.Series(sorted(d.fecha.unique()))
    meses = pd.period_range(dias.min(), corte, freq="M")
    filas = []
    for m in meses:
        dm = dias[(dias.dt.to_period("M") == m)]
        horas_prog = len(dm) * OPERACION["horas_dia"] * len(buses)
        evm = ev[ev.fecha.dt.to_period("M") == m]
        horas_paro = evm["horas_paro"].sum()
        filas.append({"mes": m.to_timestamp(), "horas_prog": horas_prog, "horas_paro": horas_paro,
                      "disponibilidad": 100 * (1 - horas_paro / horas_prog) if horas_prog else np.nan,
                      "fallas": int(evm["detiene_servicio"].sum()),
                      "mttr": evm.loc[evm.detiene_servicio, "horas_paro"].mean() if evm.detiene_servicio.any() else np.nan,
                      "costo": evm["costo"].sum()})
    mens = pd.DataFrame(filas)

    # km recorridos acumulados por la flota (odómetro final − inicial de cada bus)
    km_mes = []
    for m in meses:
        tot = 0
        for b in buses:
            db = d[(d.bus == b)]
            fin = db[db.fecha.dt.to_period("M") <= m]["km"].max()
            tot += fin - db["km"].min()
        km_mes.append(tot)
    mens["km_acum"] = km_mes
    mens["fallas_acum"] = mens["fallas"].cumsum()
    mens["mtbf_km"] = np.where(mens["fallas_acum"] > 0, mens["km_acum"] / mens["fallas_acum"].replace(0, np.nan), np.nan)
    mens["costo_acum"] = mens["costo"].cumsum()
    dias_transc = (mens["mes"] + pd.offsets.MonthEnd(0)).clip(upper=corte) - dias.min()
    mens["presupuesto_acum"] = METAS["costo_anual_bus"]["valor"] * len(buses) * (dias_transc.dt.days + 1) / 365

    horas_prog = mens["horas_prog"].sum()
    paro = ev["horas_paro"].sum()
    fallas = int(ev["detiene_servicio"].sum())
    km_tot = mens["km_acum"].iloc[-1]
    resumen = {
        "disponibilidad": 100 * (1 - paro / horas_prog),
        "mtbf_km": km_tot / fallas if fallas else np.nan,
        "mttr_h": ev.loc[ev.detiene_servicio, "horas_paro"].mean() if fallas else np.nan,
        "costo": ev["costo"].sum(),
        "presupuesto": mens["presupuesto_acum"].iloc[-1],
        "fallas": fallas, "intervenciones": len(ev), "km": km_tot, "horas_paro": paro,
    }
    return mens, resumen, ev
