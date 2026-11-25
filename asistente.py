"""
ASISTENTE DE LA PLATAFORMA
Dos modos:
  · IA (Claude): si hay una clave de API de Anthropic, envía la pregunta junto con el estado actual de la flota.
  · Básico (sin conexión): reconoce las preguntas frecuentes y responde con los datos del tablero.
"""
import os
import re
import unicodedata

import numpy as np
import requests

import motor
from config import METAS, MODOS, OPERACION, ORDEN_VARIABLES, PRIORIDADES, RCM, VARIABLES

MODELO_IA = "claude-haiku-5-5"
URL_API = "https://api.anthropic.com/v1/messages"


def clave_api(secrets=None, ingresada=None):
    if ingresada:
        return ingresada.strip()
    try:
        if secrets is not None and "ANTHROPIC_API_KEY" in secrets:
            return secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


# ------------------------------------------------------------------ contexto compartido
def foto_flota(datos, eventos, pruebas, corte, buses):
    """Resumen estructurado del estado actual (lo usan ambos modos)."""
    flota = {}
    for b in buses:
        e = motor.estado_bus(datos, pruebas, b, corte)
        vars_ = {}
        for _, r in e["tabla"].iterrows():
            t = motor.analisis_tendencia(datos, eventos, b, r["var"], corte)
            vars_[r["var"]] = {"valor": r["Valor"], "nivel": r["Nivel"], "km_alarma": t.get("km_alarma"),
                               "decision": None if t.get("ajuste") is None else t["decision"][0]}
        flota[b] = {"semaforo": e["semaforo"], "indice": e["indice"], "vars": vars_,
                    "pruebas_falladas": list(e["fallas_prueba"]["prueba"]) if len(e["fallas_prueba"]) else []}
    ots, avisos = motor.ordenes(datos, eventos, pruebas, corte, buses)
    _, kpi, _ = motor.indicadores(datos, eventos, corte, buses)
    return {"corte": corte, "flota": flota, "ots": ots, "avisos": avisos, "kpi": kpi}


def contexto_texto(f):
    L = [f"Fecha de consulta: {f['corte']:%d-%m-%Y}. Flota de {len(f['flota'])} buses Chevrolet MS 4.9 (40 pasajeros), ruta Bogotá–Cajicá, "
         f"{OPERACION['km_dia']} km/día. Componente: sistema de frenos de aire. Datos simulados para el proyecto."]
    L.append("\nUMBRALES (vigilancia / alerta=P / alarma=paro / F):")
    for v in ORDEN_VARIABLES:
        c = VARIABLES[v]
        L.append(f"- {c['nombre']} ({c['unidad']}, {'peor si baja' if c['sentido'] == 'baja' else 'peor si sube'}): "
                 f"{c['vigilancia']} / {c['alerta']} / {c['alarma']} / {c['F']}. Modo {c['modo']} ({MODOS[c['modo']]['nombre']}, S={MODOS[c['modo']]['S']}). "
                 f"Medición: {c['frecuencia']}. Fuente alarma: {c['fuentes']['alarma']}")
    L.append("\nESTADO POR BUS:")
    for b, x in f["flota"].items():
        partes = []
        for v, d in x["vars"].items():
            km = d["km_alarma"]
            kmt = "" if km is None else (" (ya en alarma)" if km == 0 else f" (≈{km:,.0f} km para alarma)")
            val = "sin dato" if d["valor"] is None or d["valor"] != d["valor"] else f"{d['valor']:g} {VARIABLES[v]['unidad']}"
            partes.append(f"{VARIABLES[v]['corto']}: {val} {d['nivel']}{kmt}")
        pf = f"; pruebas NO PASA: {', '.join(x['pruebas_falladas'])}" if x["pruebas_falladas"] else ""
        L.append(f"- {b}: semáforo {x['semaforo']}, índice {x['indice']:.0f}/100. " + "; ".join(partes) + pf)
    L.append("\nÓRDENES DE TRABAJO ABIERTAS:")
    if not f["ots"]:
        L.append("- Ninguna")
    for o in f["ots"]:
        L.append(f"- {o['id']} {o['bus']} {o['prioridad_nombre']}: {o['hallazgo']}. Tarea: {o['tarea']}. Plazo: {o['plazo']} "
                 f"(límite {o['fecha_limite']:%d-%m-%Y}). Recurso: {o['recurso']}. {o['horas']} h, ${o['costo']:,.0f}.")
    k = f["kpi"]
    L.append(f"\nINDICADORES (año a la fecha): disponibilidad por frenos {k['disponibilidad']:.1f}% (meta {METAS['disponibilidad']['valor']}%), "
             f"MTBF {k['mtbf_km']:,.0f} km (meta {METAS['mtbf_km']['valor']:,}), MTTR {k['mttr_h']:.1f} h (meta {METAS['mttr_h']['valor']}), "
             f"costo ${k['costo']:,.0f} vs presupuesto ${k['presupuesto']:,.0f}.")
    L.append("\nREGLAS DE PRIORIDAD: " + " | ".join(f"{p['nombre']}: {p['regla']} → {p['plazo']}" for p in PRIORIDADES.values()))
    return "\n".join(L)


SISTEMA = ("Eres el asistente de mantenimiento de la flota de buses de Altos de la Sabana S.A.S. Respondes a técnicos y "
           "jefes de taller. Reglas: responde en español, corto y directo (máximo 6 líneas o una lista breve); usa solo los "
           "datos del contexto y di cuando algo no está en ellos; nunca inventes mediciones; ante cualquier duda de "
           "seguridad recomienda no despachar el bus; cita el bus, el valor y el umbral cuando des una recomendación.")


def responder_ia(pregunta, historial, foto, clave, modelo=MODELO_IA):
    mensajes = [{"role": m["rol"], "content": m["texto"]} for m in historial[-8:] if m["rol"] in ("user", "assistant")]
    mensajes.append({"role": "user", "content": pregunta})
    r = requests.post(URL_API, timeout=40, headers={"x-api-key": clave, "anthropic-version": "2023-06-01",
                                                    "content-type": "application/json"},
                      json={"model": modelo, "max_tokens": 600,
                            "system": SISTEMA + "\n\nCONTEXTO ACTUAL DE LA FLOTA:\n" + contexto_texto(foto),
                            "messages": mensajes})
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return "".join(b.get("text", "") for b in r.json().get("content", []))


# ------------------------------------------------------------------ modo básico
def _norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn")


PALABRAS_VAR = {
    "espesor": ["forro", "pastilla", "zapata", "balata", "espesor", "desgaste"],
    "dT": ["temperatura", "caliente", "arrastr", "pirometr", "dt", "fading", "recalent"],
    "fuga": ["fuga", "manguera", "racor", "perdida", "escape", "diafragma"],
    "agua": ["agua", "purga", "secador", "humedad", "desecante", "aceite"],
    "recarga": ["compresor", "recarga", "llenado", "cargar aire"],
}


def _fmt_val(v, x):
    return "sin dato" if x is None or x != x else f"{x:g} {VARIABLES[v]['unidad']}".replace(".", ",")


def responder_basico(pregunta, foto):
    q = _norm(pregunta)
    flota = foto["flota"]
    m = re.search(r"b\s*-?\s*0?(\d)", q)
    bus = f"B-0{m.group(1)}" if m and f"B-0{m.group(1)}" in flota else None
    var = next((v for v, ps in PALABRAS_VAR.items() if any(p in q for p in ps)), None)

    if any(p in q for p in ["hola", "ayuda", "que puedes", "que sabes"]) and not bus and not var:
        return ("Puedo responder sobre el estado de cada bus, qué buses no deben salir, las órdenes pendientes, "
                "cuántos km faltan para una alarma, los umbrales y los indicadores. Prueba con: "
                "*¿Qué buses no pueden salir hoy?* o *¿Cómo están los forros del B-02?*")

    if any(p in q for p in ["despach", "salir", "sale", "operar", "rodar", "puede trabajar", "pueden trabajar"]):
        rojos = [b for b, x in flota.items() if x["semaforo"] == "Alarma"]
        amar = [b for b, x in flota.items() if x["semaforo"] == "Alerta"]
        if bus:
            x = flota[bus]
            if x["semaforo"] == "Alarma":
                return f"**No.** {bus} está en **alarma**: {_motivo(x)}. Debe corregirse antes de la próxima salida."
            return f"**Sí**, {bus} puede salir (semáforo {x['semaforo'].lower()}). " + (f"Ojo: {_motivo(x)}." if x["semaforo"] != "Normal" else "")
        txt = "**No despachar:** " + (", ".join(f"{b} ({_motivo(flota[b])})" for b in rojos) if rojos else "ninguno") + "."
        if amar:
            txt += "\n\n**Pueden salir con orden programada:** " + ", ".join(amar) + "."
        return txt

    if any(p in q for p in ["orden", "ot", "pendiente", "que hago", "que hay que hacer", "atender", "priorid", "urgente", "tarea"]):
        ots = [o for o in foto["ots"] if bus is None or o["bus"] == bus]
        if not ots:
            return "No hay órdenes abiertas" + (f" para {bus}." if bus else ".")
        return "\n".join(f"- **{o['prioridad']} · {o['bus']}** — {o['hallazgo']}. *{o['tarea'].split(';')[0]}*. Límite {o['fecha_limite']:%d-%b}."
                         for o in ots[:6])

    if any(p in q for p in ["disponibilidad", "mtbf", "mttr", "costo", "presupuesto", "indicador", "kpi"]):
        k = foto["kpi"]
        return (f"- Disponibilidad por frenos: **{k['disponibilidad']:.1f} %** (meta {METAS['disponibilidad']['valor']} %)\n"
                f"- MTBF: **{k['mtbf_km']:,.0f} km** entre fallas (meta {METAS['mtbf_km']['valor']:,})\n"
                f"- MTTR: **{k['mttr_h']:.1f} h** (meta {METAS['mttr_h']['valor']} h)\n"
                f"- Costo: **${k['costo']:,.0f}** de ${k['presupuesto']:,.0f} presupuestados").replace(",", ".")

    if var and any(p in q for p in ["umbral", "limite", "norma", "maximo", "minimo", "cuanto debe", "valor normal"]):
        c = VARIABLES[var]
        s = "≤" if c["sentido"] == "baja" else "≥"
        return (f"**{c['nombre']}** — alerta (P) {s} {c['alerta']:g} {c['unidad']} · alarma/paro {s} {c['alarma']:g} {c['unidad']} · "
                f"F {c['F']:g} {c['unidad']}.\n\nFuente de la alarma: {c['fuentes']['alarma']}.")

    if var:
        buses = [bus] if bus else list(flota)
        lineas = []
        for b in buses:
            d = flota[b]["vars"][var]
            km = d["km_alarma"]
            kmt = "" if km is None else (" · ya en alarma" if km == 0 else f" · faltan ≈ {km:,.0f} km ({km / OPERACION['km_dia']:.0f} días) para la alarma".replace(",", "."))
            lineas.append(f"- **{b}**: {_fmt_val(var, d['valor'])} → {d['nivel']}{kmt}")
        return f"**{VARIABLES[var]['nombre']}**\n" + "\n".join(lineas)

    if any(p in q for p in ["indice", "salud", "semaforo", "como se calcula"]) and not bus:
        return ("Cada variable se convierte en un puntaje de 0 a 100 (100 = nuevo, 60 = punto P, 20 = paro). El índice es el promedio "
                "ponderado por el NPR del AMFEC. El semáforo toma el peor estado: una sola variable en alarma pone el bus en rojo.")

    if bus:
        x = flota[bus]
        lineas = [f"**{bus}** · semáforo **{x['semaforo']}** · índice {x['indice']:.0f}/100"]
        for v in ORDEN_VARIABLES:
            d = x["vars"][v]
            if d["nivel"] != "Normal":
                lineas.append(f"- {VARIABLES[v]['corto']}: {_fmt_val(v, d['valor'])} → {d['nivel']}")
        if len(lineas) == 1:
            lineas.append("Todas las variables en condición normal.")
        return "\n".join(lineas)

    rojos = sum(x["semaforo"] == "Alarma" for x in flota.values())
    return (f"No entendí del todo la pregunta. Resumen rápido: {len(flota)} buses, {rojos} en alarma y {len(foto['ots'])} órdenes abiertas. "
            "Puedes preguntar por un bus (B-01 a B-05), por una variable (forros, fuga, purga, temperatura, compresor), "
            "por las órdenes o por los indicadores.")


def _motivo(x):
    malas = [f"{VARIABLES[v]['corto']} {_fmt_val(v, d['valor'])}" for v, d in x["vars"].items() if d["nivel"] in ("Alerta", "Alarma")]
    nombres = {"alarma": "alarma de baja presión", "resorte": "freno de estacionamiento", "abs": "testigo ABS"}
    malas += [f"{nombres.get(p, p)} no pasa" for p in x["pruebas_falladas"]]
    return ", ".join(malas) if malas else "sin hallazgos"
