"""
PLATAFORMA DE MANTENIMIENTO · FRENOS DE AIRE
Altos de la Sabana S.A.S. · Ruta Bogotá–Cajicá

Páginas: Flota · Bus · Registrar · Órdenes · Indicadores · Asistente · Referencia
Ejecutar:  python -m streamlit run app.py
"""
import datetime as dt
import io
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import almacen
import asistente
import modelo3d
import motor
import simulador
from config import (COLOR_NIVEL, FLOTA, LIMITACIONES, METAS, MODOS, OPERACION, ORDEN_VARIABLES, PESOS, PRIORIDADES,
                    PRUEBAS, RCM, REFERENCIAS, SUPUESTOS, VARIABLES)

st.set_page_config(page_title="Taller · Frenos de aire", page_icon=":material/directions_bus:", layout="wide")

GRIS = "#9aa3ad"
COLOR = {**COLOR_NIVEL, "Sin dato": GRIS}
COLOR_P = {"P1": COLOR_NIVEL["Alarma"], "P2": COLOR_NIVEL["Alerta"], "P3": "#3b6fb6"}
VAR_DE_MODO = {VARIABLES[v]["modo"]: v for v in ORDEN_VARIABLES}
RANGO = {"espesor": (0.0, 25.0), "dT": (0.0, 150.0), "fuga": (0.0, 2.0), "agua": (0.0, 500.0), "recarga": (5.0, 180.0)}
PASO = {"espesor": 0.1, "dT": 1.0, "fuga": 0.01, "agua": 1.0, "recarga": 1.0}

st.markdown("""
<style>
.block-container {padding-top: 3.6rem; max-width: 1400px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.num {font-variant-numeric: tabular-nums;}
.pill {display:inline-flex; align-items:center; gap:6px; padding:2px 10px; border-radius:4px; font-size:12px;
       font-weight:700; text-transform:uppercase; letter-spacing:.04em;}
.pill i {width:8px; height:8px; border-radius:50%; display:inline-block;}
.lbl {font-size:12px !important; color:#5b6470; text-transform:uppercase; letter-spacing:.05em; font-weight:600; margin:0;}
.big {font-size:30px !important; font-weight:700; line-height:1.15; margin:2px 0; font-variant-numeric: tabular-nums;}
.sub {font-size:13px !important; color:#5b6470; margin:0;}
.kpi {border:1px solid #dfe3e8; border-radius:6px; padding:12px 16px; background:#fff;}
.banner {border-radius:6px; padding:12px 16px; font-weight:600; margin:4px 0 10px 0; font-size:15px;}
.dots {display:flex; gap:4px; margin:8px 0 4px 0;}
.dots div {flex:1; text-align:center; font-size:10.5px; color:#5b6470;}
.dots span {display:block; height:8px; border-radius:2px; margin-bottom:3px;}
.otc {border:1px solid #dfe3e8; border-left-width:5px; border-radius:6px; padding:10px 12px; margin-bottom:8px; background:#fff;}
.otc b {font-size:15px;}
.check {display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid #eef0f3; font-size:14px;}
.origen {font-size:11px; color:#7a828c; border:1px solid #dfe3e8; border-radius:3px; padding:0 5px;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ utilidades visuales
def pill(nivel, texto=None):
    c = COLOR.get(nivel, GRIS)
    return f'<span class="pill" style="background:{c}1f;color:{c}"><i style="background:{c}"></i>{texto or nivel}</span>'


def fmt(x, dec=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def val(v, x):
    if x is None or x != x:
        return "—"
    if v == "fuga":
        return fmt(x, 3).rstrip("0").rstrip(",") if x else "0"
    return fmt(x, 1 if v == "espesor" else 0)


_CSS = []


def css_borde(key, color):
    _CSS.append(f".st-key-{key} {{border-left:5px solid {color} !important;}}")


def css_aplicar():
    """Escribe todos los bordes de color en un solo bloque (evita espacios vacíos entre secciones)."""
    if _CSS:
        st.html("<style>" + "".join(_CSS) + "</style>")
        _CSS.clear()


def kpi(col, titulo, valor, sub="", color=None):
    estilo = f"border-top:3px solid {color};" if color else ""
    col.markdown(f'<div class="kpi" style="{estilo}"><p class="lbl">{titulo}</p><p class="big">{valor}</p><p class="sub">{sub}</p></div>',
                 unsafe_allow_html=True)


def sincronizar(clave, opciones, defecto):
    """Valor persistente entre páginas para un widget (los widgets se borran al cambiar de página)."""
    if st.session_state.get(clave) not in opciones:
        st.session_state[clave] = defecto
    st.session_state["w_" + clave] = st.session_state[clave]


def guardar_widget(clave):
    if st.session_state.get("w_" + clave) is not None:
        st.session_state[clave] = st.session_state["w_" + clave]


# ------------------------------------------------------------------ datos (en caché)
@st.cache_data(show_spinner=False)
def base():
    return simulador.simular()


def version():
    return tuple(os.path.getmtime(f) if os.path.exists(f) else 0 for f in almacen.ARCH.values())


@st.cache_data(show_spinner=False)
def cargar(ver):
    return almacen.cargar(base())


@st.cache_data(show_spinner=False)
def foto(ver, corte):
    d, e, p = cargar(ver)
    return asistente.foto_flota(d, e, p, corte, sorted(d["bus"].unique()))


@st.cache_data(show_spinner=False)
def estado(ver, corte, bus):
    d, e, p = cargar(ver)
    return motor.estado_bus(d, p, bus, corte)


@st.cache_data(show_spinner=False)
def tendencia(ver, corte, bus, var):
    d, e, p = cargar(ver)
    return motor.analisis_tendencia(d, e, bus, var, corte)


@st.cache_data(show_spinner=False)
def kpis(ver, corte):
    d, e, p = cargar(ver)
    return motor.indicadores(d, e, corte, sorted(d["bus"].unique()))


VER = version()
DATOS, EVENTOS, PRUEBAS_DF = cargar(VER)
BUSES = sorted(DATOS["bus"].unique())
FECHAS = [pd.Timestamp(f) for f in sorted(DATOS["fecha"].dt.normalize().unique())]

# ------------------------------------------------------------------ barra lateral: fecha de consulta
with st.sidebar:
    st.markdown("**Fecha de consulta**")
    st.toggle("Ver el sistema en una fecha pasada", key="hist_on")
    if st.session_state.get("hist_on"):
        if st.session_state.get("corte_hist") not in FECHAS:
            st.session_state.corte_hist = FECHAS[-1]
        st.select_slider("Fecha", options=FECHAS, key="corte_hist", label_visibility="collapsed",
                         format_func=lambda f: pd.Timestamp(f).strftime("%d %b %Y"))

        def ir_demo():
            ini = pd.Timestamp(simulador.FIN) - pd.Timedelta(days=40)
            st.session_state.corte_hist = min(FECHAS, key=lambda f: abs(f - ini))
            st.session_state.bus = "B-03"

        st.button("Demostración: fuga del B-03", icon=":material/play_circle:", on_click=ir_demo, width="stretch")
        st.caption("Mueva la fecha hacia adelante para ver cómo la fuga pasa de normal a paro.")
    st.divider()
    st.caption("Historial base simulado · los registros que se ingresan quedan guardados como «Medido».")

CORTE = pd.Timestamp(st.session_state.corte_hist) if st.session_state.get("hist_on") else FECHAS[-1]
FOTO = foto(VER, CORTE)


# ------------------------------------------------------------------ componentes reutilizables
def sparkline(bus, var, color, key):
    h = DATOS[(DATOS.bus == bus) & (DATOS.variable == var) & (DATOS.fecha <= CORTE)].tail(40)
    fig = go.Figure(go.Scatter(x=h["km"], y=h["valor"], mode="lines", line=dict(color=color, width=2), hoverinfo="skip"))
    fig.add_hline(y=VARIABLES[var]["alarma"], line_dash="dot", line_color=COLOR_NIVEL["Alarma"], line_width=1)
    lim = h["valor"].tolist() + [VARIABLES[var]["alarma"]]
    fig.update_layout(height=54, margin=dict(l=0, r=0, t=4, b=0), showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False),
                      yaxis=dict(visible=False, range=[min(lim) - 0.05 * (max(lim) - min(lim) + 1e-9), max(lim) * 1.05 + 1e-9]))
    st.plotly_chart(fig, config={"staticPlot": True}, key=key, width="stretch")


def grafico_tendencia(bus, var, t, alto=380):
    c = VARIABLES[var]
    hist = DATOS[(DATOS.bus == bus) & (DATOS.variable == var) & (DATOS.fecha <= CORTE)]
    fig = go.Figure()
    if hist.empty:
        return fig
    xmin, xmax = hist["km"].min(), hist["km"].max()
    aj = t["ajuste"]
    proy = xmax
    if aj is not None and t.get("km_alarma") not in (None, 0):
        proy = xmax + min(t["km_alarma"] * 1.15, 40_000)
    lim = [c["nominal"], c["vigilancia"], c["alerta"], c["alarma"], c["F"]]
    y_lo, y_hi = min(lim + hist["valor"].tolist()), max(lim + hist["valor"].tolist())
    pad = (y_hi - y_lo) * 0.06
    bandas = [("Normal", c["nominal"], c["vigilancia"]), ("Vigilancia", c["vigilancia"], c["alerta"]),
              ("Alerta", c["alerta"], c["alarma"]), ("Alarma", c["alarma"], c["F"])]
    for nom, a, b in bandas:
        lo, hi = sorted([a, b])
        if nom == "Normal":
            lo, hi = (lo, y_hi + pad) if c["sentido"] == "baja" else (y_lo - pad, hi)
        if nom == "Alarma":
            lo, hi = (y_lo - pad, hi) if c["sentido"] == "baja" else (lo, y_hi + pad)
        fig.add_hrect(y0=lo, y1=hi, fillcolor=COLOR_NIVEL[nom], opacity=0.08, line_width=0)
    fig.add_hline(y=c["alerta"], line_dash="dash", line_color=COLOR_NIVEL["Alerta"], line_width=1,
                  annotation_text=f"Alerta {c['alerta']:g}", annotation_position="top left", annotation_font_size=11)
    fig.add_hline(y=c["alarma"], line_dash="dash", line_color=COLOR_NIVEL["Alarma"], line_width=1,
                  annotation_text=f"Paro {c['alarma']:g}", annotation_position="top left", annotation_font_size=11)
    viejos = hist[~hist.index.isin(t["tramo"].index)]
    hov = "%{y} " + c["unidad"] + "<br>%{x:,.0f} km · %{customdata}<extra></extra>"
    fig.add_trace(go.Scatter(x=viejos["km"], y=viejos["valor"], mode="markers", name="Antes de la última reparación",
                             marker=dict(color="#c3c9d1", size=5), customdata=viejos["fecha"].dt.strftime("%d %b"), hovertemplate=hov))
    tr = t["tramo"]
    med = tr[tr["origen"].astype(str).str.startswith("Medido")]
    fig.add_trace(go.Scatter(x=tr["km"], y=tr["valor"], mode="markers", name="Mediciones",
                             marker=dict(color="#3b6fb6", size=7), customdata=tr["fecha"].dt.strftime("%d %b"), hovertemplate=hov))
    if len(med):
        fig.add_trace(go.Scatter(x=med["km"], y=med["valor"], mode="markers", name="Registradas en la plataforma",
                                 marker=dict(color="#111827", size=10, symbol="diamond"),
                                 customdata=med["fecha"].dt.strftime("%d %b"), hovertemplate=hov))
    if aj is not None:
        xs = np.linspace(0, aj["x_ult"], 60)
        fig.add_trace(go.Scatter(x=aj["x0"] + xs, y=motor.predecir(aj, xs), mode="lines", name="Tendencia",
                                 line=dict(color="#1f2a44", width=2.5)))
        if t.get("km_alarma") not in (None, 0):
            xp = np.linspace(aj["x_ult"], aj["x_ult"] + t["km_alarma"], 40)
            fig.add_trace(go.Scatter(x=aj["x0"] + xp, y=motor.predecir(aj, xp), mode="lines", name="Proyección",
                                     line=dict(color="#1f2a44", width=2, dash="dot")))
            xa = aj["x0"] + aj["x_ult"] + t["km_alarma"]
            fig.add_trace(go.Scatter(x=[xa], y=[c["alarma"]], mode="markers+text", text=[f"paro en ≈ {fmt(t['km_alarma'])} km"],
                                     textposition="top center", marker=dict(color=COLOR_NIVEL["Alarma"], size=11, symbol="x"),
                                     showlegend=False, hoverinfo="skip"))
    evb = EVENTOS[(EVENTOS.bus == bus) & (EVENTOS.variable == var) & (EVENTOS.fecha <= CORTE)]
    for _, ev in evb.iterrows():
        fig.add_vline(x=ev["km"], line_color="#5b6470", line_dash="dot", line_width=1)
        fig.add_annotation(x=ev["km"], y=y_hi + pad * 0.4, text="reparación", showarrow=False, font=dict(size=10, color="#5b6470"))
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
                      xaxis_title="Odómetro (km)", yaxis_title=f"{c['corto']} ({c['unidad']})",
                      xaxis_range=[xmin - (xmax - xmin) * 0.02, max(xmax, proy) + (xmax - xmin) * 0.03],
                      yaxis_range=[y_lo - pad, y_hi + pad], legend=dict(orientation="h", y=-0.2), hovermode="closest")
    fig.update_xaxes(showgrid=True, gridcolor="#f0f2f5")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f2f5")
    return fig


def ultimo_km(bus, hasta=None):
    d = DATOS[DATOS.bus == bus]
    if hasta is not None:
        d = d[d.fecha <= pd.Timestamp(hasta)]
    return (float(d["km"].max()), d["fecha"].max()) if len(d) else (0.0, None)


def km_sugerido(bus, fecha):
    km, f = ultimo_km(bus, fecha)
    if f is None:
        return 0
    dias = max(0, np.busday_count(f.date(), fecha, weekmask="1111110"))
    return int(round(km + dias * OPERACION["km_dia"], -1))


def resultado_registro(filas):
    """Muestra el nivel de cada valor recién guardado."""
    cols = st.columns(len(filas))
    for col, (v, x) in zip(cols, filas):
        n = motor.nivel(v, x)
        col.markdown(f'<div class="kpi" style="border-top:3px solid {COLOR[n]}"><p class="lbl">{VARIABLES[v]["corto"]}</p>'
                     f'<p class="big">{val(v, x)} <span style="font-size:14px">{VARIABLES[v]["unidad"]}</span></p>{pill(n)}</div>',
                     unsafe_allow_html=True)


# ================================================================== FLOTA
def pagina_flota():
    flota = FOTO["flota"]
    ots = FOTO["ots"]
    rojos = [b for b, x in flota.items() if x["semaforo"] == "Alarma"]
    k = FOTO["kpi"]
    st.markdown(f"## Flota · {CORTE:%d %b %Y}")
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Pueden salir", f"{len(flota) - len(rojos)} / {len(flota)}", "buses habilitados hoy",
        COLOR_NIVEL["Normal"] if not rojos else COLOR_NIVEL["Alerta"])
    kpi(c2, "No despachar", str(len(rojos)), ", ".join(rojos) if rojos else "ninguno", COLOR_NIVEL["Alarma"] if rojos else None)
    kpi(c3, "Órdenes abiertas", str(len(ots)), " · ".join(f"{p}: {sum(o['prioridad'] == p for o in ots)}" for p in ("P1", "P2", "P3")))
    meta = METAS["disponibilidad"]["valor"]
    kpi(c4, "Disponibilidad", f"{fmt(k['disponibilidad'], 1)} %", f"meta {fmt(meta)} %",
        COLOR_NIVEL["Normal"] if k["disponibilidad"] >= meta else COLOR_NIVEL["Alarma"])
    st.write("")

    cols = st.columns(len(flota))
    for col, (b, x) in zip(cols, flota.items()):
        key = f"card_{b.replace('-', '')}"
        css_borde(key, COLOR[x["semaforo"]])
        with col.container(border=True, key=key):
            puntos = "".join(f'<div><span style="background:{COLOR[x["vars"][v]["nivel"]]}"></span>{VARIABLES[v]["corto"].replace("ΔT ruedas", "ΔT")}</div>'
                             for v in ORDEN_VARIABLES)
            fallas = x["pruebas_falladas"]
            motivo = asistente._motivo(x) if x["semaforo"] != "Normal" or fallas else "Todo en orden"
            st.markdown(f'<p class="lbl">{FLOTA.get(b, "").split("·")[-1].strip()}</p>'
                        f'<p class="big">{b}</p>{pill(x["semaforo"], "No despachar" if x["semaforo"] == "Alarma" else x["semaforo"])}'
                        f'<div class="dots">{puntos}</div>'
                        f'<p class="sub" style="min-height:38px">{motivo[:70]}</p>', unsafe_allow_html=True)
            if st.button("Abrir", key=f"abrir_{b}", icon=":material/arrow_forward:", width="stretch"):
                st.session_state.bus = b
                st.switch_page(PAG["bus"])
    css_aplicar()
    izq, der = st.columns([3, 2], gap="large")
    with izq:
        st.markdown("#### Días hasta el paro")
        filas = []
        for b, x in flota.items():
            for v, d in x["vars"].items():
                if d["km_alarma"] is not None:
                    filas.append({"item": f"{b} · {VARIABLES[v]['corto']}", "dias": d["km_alarma"] / OPERACION["km_dia"],
                                  "nivel": d["nivel"], "km": d["km_alarma"]})
        if filas:
            df = pd.DataFrame(filas).sort_values("dias").head(8).iloc[::-1]
            vis = df["dias"].clip(lower=0.3, upper=60)
            fig = go.Figure(go.Bar(x=vis, y=df["item"], orientation="h", marker_color=[COLOR[n] for n in df["nivel"]],
                                   text=["YA" if d == 0 else f"{d:.0f} d" for d in df["dias"]], textposition="outside",
                                   customdata=df["km"], hovertemplate="%{customdata:,.0f} km<extra></extra>"))
            fig.add_vline(x=OPERACION["dias_reaccion"], line_dash="dash", line_color="#5b6470",
                          annotation_text="tiempo de reacción", annotation_position="top", annotation_font_size=11)
            fig.update_layout(height=60 + 34 * len(df), margin=dict(l=10, r=40, t=24, b=10), plot_bgcolor="white",
                              xaxis_title="días de operación (263 km/día)", xaxis_range=[0, 68], showlegend=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.info("Ninguna variable se está deteriorando hacia el paro.")
    with der:
        st.markdown("#### Para hoy")
        if not ots:
            st.success("Sin órdenes abiertas.")
        for o in ots[:5]:
            st.markdown(f'<div class="otc" style="border-left-color:{COLOR_P[o["prioridad"]]}">'
                        f'<span class="pill" style="background:{COLOR_P[o["prioridad"]]};color:white">{o["prioridad"]}</span> '
                        f'<b>{o["bus"]}</b> · {o["hallazgo"]}<br><span class="sub">{o["tarea"].split(";")[0]} · '
                        f'límite {o["fecha_limite"]:%d %b}</span></div>', unsafe_allow_html=True)
        if ots:
            st.page_link(PAG["ordenes"], label="Ver todas las órdenes", icon=":material/arrow_forward:")


# ================================================================== BUS
def pagina_bus():
    sincronizar("bus", BUSES, BUSES[0])
    st.segmented_control("Bus", BUSES, key="w_bus", on_change=guardar_widget, args=("bus",), label_visibility="collapsed")
    bus = st.session_state.bus
    e = estado(VER, CORTE, bus)
    tabla = e["tabla"].set_index("var")
    x = FOTO["flota"][bus]
    km_act, f_act = ultimo_km(bus, CORTE)

    a, b = st.columns([3, 2])
    a.markdown(f'<p class="big" style="font-size:34px">{bus} <span style="font-size:16px;color:#5b6470;font-weight:500">'
               f'{FLOTA.get(bus, "")}</span></p>', unsafe_allow_html=True)
    b.markdown(f'<p style="text-align:right;margin-top:10px">{pill(x["semaforo"])} &nbsp; '
               f'<span class="sub">Índice <b class="num">{fmt(e["indice"])}</b>/100 · {fmt(km_act)} km · {f_act:%d %b}</span></p>',
               unsafe_allow_html=True)
    if x["semaforo"] == "Alarma":
        st.markdown(f'<div class="banner" style="background:{COLOR_NIVEL["Alarma"]};color:white">NO DESPACHAR · {asistente._motivo(x)}</div>',
                    unsafe_allow_html=True)
    elif x["semaforo"] == "Alerta":
        st.markdown(f'<div class="banner" style="background:{COLOR_NIVEL["Alerta"]}26;color:#7a5200">Puede salir · programar orden: '
                    f'{asistente._motivo(x)}</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    for col, v in zip(cols, ORDEN_VARIABLES):
        r = tabla.loc[v]
        c = VARIABLES[v]
        km = x["vars"][v]["km_alarma"]
        resta = "ya en paro" if km == 0 else ("estable" if km is None else f"paro en ≈ {fmt(km / OPERACION['km_dia'])} días")
        key = f"tile_{v}"
        css_borde(key, COLOR[r["Nivel"]])
        with col.container(border=True, key=key):
            st.markdown(f'<p class="lbl">{c["corto"]}</p><p class="big">{val(v, r["Valor"])} '
                        f'<span style="font-size:14px;font-weight:500">{c["unidad"]}</span></p>{pill(r["Nivel"])}',
                        unsafe_allow_html=True)
            sparkline(bus, v, COLOR[r["Nivel"]], f"sp_{bus}_{v}")
            st.markdown(f'<p class="sub">{resta}</p>', unsafe_allow_html=True)
    css_aplicar()

    izq, der = st.columns([3, 2], gap="large")
    with izq:
        peor_rueda = motor.peor(tabla.loc["espesor", "Nivel"], tabla.loc["dT", "Nivel"])
        st.plotly_chart(modelo3d.figura(e["tabla"], peor_rueda, alto=430), width="stretch")
        st.caption("Gire con el mouse · el color de cada pieza es su estado.")
    with der:
        st.markdown("#### Pruebas de hoy")
        filas = ""
        for k_, p in PRUEBAS.items():
            pr = e["pruebas"][e["pruebas"].prueba == k_]
            res = pr["resultado"].iloc[0] if len(pr) else "Sin registro"
            n = "Normal" if res == "Pasa" else ("Alarma" if res == "No pasa" else "Sin dato")
            filas += f'<div class="check"><span>{p["nombre"]}</span>{pill(n, res)}</div>'
        st.markdown(filas, unsafe_allow_html=True)
        st.write("")
        g = go.Figure(go.Indicator(mode="gauge+number", value=e["indice"], number={"suffix": "/100", "font": {"size": 30}, "valueformat": ".0f"},
                                   gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#1f2a44", "thickness": 0.25},
                                          "steps": [{"range": [0, 20], "color": COLOR_NIVEL["Alarma"]},
                                                    {"range": [20, 60], "color": COLOR_NIVEL["Alerta"]},
                                                    {"range": [60, 80], "color": COLOR_NIVEL["Vigilancia"]},
                                                    {"range": [80, 100], "color": COLOR_NIVEL["Normal"]}]}))
        g.update_layout(height=190, margin=dict(l=25, r=25, t=20, b=0))
        st.markdown('<p class="lbl">Índice de salud</p>', unsafe_allow_html=True)
        st.plotly_chart(g, width="stretch", config={"displayModeBar": False})
        with st.popover("¿Cómo se calcula?", icon=":material/help:"):
            st.markdown("Cada variable vale de **100** (nueva) a **0** (falla). El índice es el promedio ponderado por el NPR del AMFEC.")
            st.dataframe(pd.DataFrame({"Variable": [VARIABLES[v]["corto"] for v in ORDEN_VARIABLES],
                                       "Puntaje": [fmt(tabla.loc[v, "Sub-índice"]) for v in ORDEN_VARIABLES],
                                       "Peso": [f"{PESOS[v] * 100:.0f} %" for v in ORDEN_VARIABLES]}), hide_index=True)
            st.caption("El color del bus es el peor estado entre el índice, cada variable y las pruebas.")

    st.markdown("#### Tendencia")
    orden_n = {"Alarma": 0, "Alerta": 1, "Vigilancia": 2, "Normal": 3, "Sin dato": 4}
    peor_var = min(ORDEN_VARIABLES, key=lambda v: orden_n[tabla.loc[v, "Nivel"]])
    if st.session_state.get("_bus_var") != bus:
        st.session_state.var = peor_var
        st.session_state._bus_var = bus
    sincronizar("var", ORDEN_VARIABLES, peor_var)
    st.segmented_control("Variable", ORDEN_VARIABLES, key="w_var", on_change=guardar_widget, args=("var",),
                         format_func=lambda v: VARIABLES[v]["corto"], label_visibility="collapsed")
    var = st.session_state.var
    t = tendencia(VER, CORTE, bus, var)
    st.plotly_chart(grafico_tendencia(bus, var, t), width="stretch")
    if t["ajuste"] is None:
        st.info("Pocas mediciones desde la última reparación: todavía no hay tendencia.")
    else:
        titulo, texto = t["decision"]
        col = {"Ya en alarma": "Alarma", "No alcanza": "Alarma", "Intervenir antes de la próxima medición": "Alerta"}.get(titulo, "Normal")
        st.markdown(f'<div class="banner" style="background:{COLOR[col]}1a;border-left:5px solid {COLOR[col]};font-weight:500">'
                    f'<b>{titulo}.</b> {texto}</div>', unsafe_allow_html=True)
        with st.popover("Detalle del cálculo", icon=":material/functions:"):
            aj = t["ajuste"]
            c = VARIABLES[var]
            st.markdown(f"Modelo **{aj['modelo']['tipo']}** con {aj['n']} mediciones · R² {aj['modelo']['r2']:.2f}")
            st.caption(c["justif_tendencia"])
            st.markdown(f"- Tiempo de reacción del taller: {OPERACION['km_reaccion']} km ({OPERACION['dias_reaccion']} días)\n"
                        f"- Intervalo P-F: {fmt(c['pf_km'][0])}–{fmt(c['pf_km'][1])} km\n- Se mide: {c['frecuencia'].lower()}")
            if not t.get("significativa", True):
                st.caption(f"R² < {motor.R2_MINIMO}: la variable está estable, no se proyecta.")


# ================================================================== REGISTRAR
def pagina_registrar():
    st.markdown("## Registrar")
    hoy = dt.date.today()
    f_min = FECHAS[0].date()
    tipo = st.segmented_control("Tipo de registro", ["Inspección diaria", "Revisión de taller", "Reparación", "Mis registros"],
                                default="Inspección diaria", key="tipo_reg", label_visibility="collapsed")
    if tipo is None:
        tipo = "Inspección diaria"

    if tipo in ("Inspección diaria", "Revisión de taller"):
        diaria = tipo == "Inspección diaria"
        vars_f = ["fuga", "agua"] if diaria else ["espesor", "dT", "recarga"]
        st.caption("Conductor, antes de salir · 5 minutos" if diaria else "Técnico de frenos · cada 5.000 km (ΔT: semanal)")
        c1, c2, c3, c4 = st.columns(4)
        bus = c1.selectbox("Bus", BUSES, key="r_bus")
        fecha = c2.date_input("Fecha", value=hoy, min_value=f_min, key="r_fecha")
        km = c3.number_input("Odómetro (km)", min_value=0, step=10, value=km_sugerido(bus, fecha), key=f"r_km_{bus}_{fecha}")
        quien = c4.text_input("Responsable", key="r_quien", placeholder="Nombre")

        with st.form(f"form_{tipo}", border=True):
            cols = st.columns(len(vars_f))
            valores = {}
            for col, v in zip(cols, vars_f):
                c = VARIABLES[v]
                valores[v] = col.number_input(f"{c['corto']} ({c['unidad']})", min_value=RANGO[v][0], max_value=RANGO[v][1],
                                              step=PASO[v], value=None, placeholder="sin medir", help=c["metodo"])
                col.caption(f"alerta {'≤' if c['sentido'] == 'baja' else '≥'} {c['alerta']:g} · paro {c['alarma']:g}")
            res_pruebas = {}
            if diaria:
                st.markdown('<p class="lbl" style="margin-top:8px">Pruebas</p>', unsafe_allow_html=True)
                pc = st.columns(3)
                for col, (k_, p) in zip(pc, PRUEBAS.items()):
                    res_pruebas[k_] = col.segmented_control(p["nombre"], ["Pasa", "No pasa"], default="Pasa", key=f"p_{k_}",
                                                            help=p["criterio"])
            enviar = st.form_submit_button("Guardar", icon=":material/save:", type="primary")
        if enviar:
            km_prev, f_prev = ultimo_km(bus, fecha)
            medidas = {v: x for v, x in valores.items() if x is not None}
            if not medidas and not res_pruebas:
                st.warning("No hay valores para guardar.")
            elif km < km_prev:
                st.error(f"El odómetro no puede ser menor que el último registrado ({fmt(km_prev)} km, {f_prev:%d %b}).")
            else:
                ts = pd.Timestamp(fecha)
                who = quien or "Sin nombre"
                if medidas:
                    almacen.agregar("mediciones", [{"fecha": ts, "bus": bus, "km": km, "variable": v, "valor": x, "origen": "Medido",
                                                    "registrado_por": who} for v, x in medidas.items()])
                if res_pruebas:
                    almacen.agregar("pruebas", [{"fecha": ts, "bus": bus, "prueba": k_, "resultado": r or "Pasa", "origen": "Medido",
                                                 "registrado_por": who} for k_, r in res_pruebas.items()])
                st.session_state.ultimo_registro = {"bus": bus, "medidas": medidas, "fallas": [k_ for k_, r in res_pruebas.items() if r == "No pasa"]}
                st.rerun()
        if "ultimo_registro" in st.session_state:
            u = st.session_state.ultimo_registro
            st.success(f"Guardado para {u['bus']}.", icon=":material/check_circle:")
            if u["medidas"]:
                resultado_registro(list(u["medidas"].items()))
            if u["fallas"]:
                st.error("Prueba que no pasa: " + ", ".join(PRUEBAS[k_]["nombre"] for k_ in u["fallas"]) + " → el bus no se despacha.")
            st.page_link(PAG["bus"], label=f"Ver el estado del {u['bus']}", icon=":material/arrow_forward:")

    elif tipo == "Reparación":
        st.caption("Registre el trabajo hecho. La tendencia de la variable reinicia desde aquí.")
        with st.form("form_rep", border=True):
            c1, c2, c3 = st.columns(3)
            bus = c1.selectbox("Bus", BUSES)
            fecha = c2.date_input("Fecha", value=hoy, min_value=f_min)
            km = c3.number_input("Odómetro (km)", min_value=0, step=10, value=km_sugerido(BUSES[0], hoy))
            modo = st.selectbox("¿Qué se reparó?", list(MODOS), format_func=lambda m: f"{MODOS[m]['nombre']}")
            c4, c5, c6 = st.columns(3)
            en_ruta = c4.toggle("Falló en ruta")
            horas = c5.number_input("Horas de paro", min_value=0.0, step=0.5, value=None, placeholder="según RCM")
            costo = c6.number_input("Costo (COP)", min_value=0, step=50_000, value=None, placeholder="según RCM")
            valor_post = st.number_input("Valor medido después de reparar (si aplica)", value=None, placeholder="sin medir",
                                         help="Forros: espesor nuevo · Fuga, purga, ΔT, recarga: valor de verificación")
            desc = st.text_input("Descripción", placeholder="Qué se encontró y qué se cambió")
            quien = st.text_input("Técnico")
            enviar = st.form_submit_button("Guardar reparación", icon=":material/build:", type="primary")
        if enviar:
            guardar_reparacion(bus, pd.Timestamp(fecha), km, modo, en_ruta, horas, costo, valor_post, desc, quien)
            st.success("Reparación guardada.", icon=":material/check_circle:")

    else:
        u = almacen.registros_usuario()
        total = sum(len(x) for x in u.values())
        if total == 0:
            st.info("Todavía no hay registros ingresados en la plataforma.")
        a1, a2, a3 = st.columns(3)
        kpi(a1, "Mediciones", str(len(u["mediciones"])))
        kpi(a2, "Pruebas", str(len(u["pruebas"])))
        kpi(a3, "Reparaciones", str(len(u["eventos"])))
        st.write("")
        if len(u["mediciones"]):
            m = u["mediciones"].copy()
            m["Nivel"] = [motor.nivel(v, x) for v, x in zip(m["variable"], m["valor"])]
            m["variable"] = m["variable"].map(lambda v: VARIABLES[v]["corto"])
            m["fecha"] = m["fecha"].dt.strftime("%d %b %Y")
            st.dataframe(m[["fecha", "bus", "km", "variable", "valor", "Nivel", "registrado_por"]].iloc[::-1],
                         hide_index=True, width="stretch",
                         column_config={"Nivel": st.column_config.TextColumn("Estado"), "registrado_por": "Responsable"})
        if len(u["eventos"]):
            ev = u["eventos"].copy()
            ev["modo"] = ev["modo"].map(lambda m: MODOS[int(m)]["nombre"])
            ev["fecha"] = ev["fecha"].dt.strftime("%d %b %Y")
            st.dataframe(ev[["fecha", "bus", "km", "modo", "tipo", "horas_paro", "costo", "registrado_por"]].iloc[::-1],
                         hide_index=True, width="stretch")
        if total:
            d1, d2 = st.columns([1, 1])
            d1.download_button("Descargar en Excel", excel(u["mediciones"], u["eventos"], u["pruebas"]), "registros.xlsx",
                               icon=":material/download:", width="stretch")
            with d2.popover("Borrar mis registros", icon=":material/delete:", width="stretch"):
                st.write("Se eliminan todos los registros ingresados. El historial simulado no cambia.")
                if st.button("Sí, borrar", type="primary"):
                    almacen.borrar_registros()
                    st.session_state.pop("ultimo_registro", None)
                    st.rerun()


def guardar_reparacion(bus, fecha, km, modo, en_ruta, horas, costo, valor_post, desc, quien, prueba=None):
    r = RCM[modo]
    var = VAR_DE_MODO.get(modo)
    from config import CORRECTIVO_EN_RUTA
    h = horas if horas is not None else r["horas"] + (CORRECTIVO_EN_RUTA["horas_extra"] if en_ruta else 0)
    c = costo if costo is not None else r["costo"] + (CORRECTIVO_EN_RUTA["costo_extra"] if en_ruta else 0)
    who = quien or "Sin nombre"
    almacen.agregar("eventos", [{"fecha": fecha, "bus": bus, "km": km, "modo": modo, "variable": var,
                                 "tipo": "Correctivo en ruta" if en_ruta else "Preventivo a condición", "detiene_servicio": en_ruta,
                                 "descripcion": desc or MODOS[modo]["nombre"], "tarea": r["tarea"], "horas_paro": h, "costo": c,
                                 "origen": "Medido", "registrado_por": who}])
    if var and valor_post is not None:
        almacen.agregar("mediciones", [{"fecha": fecha, "bus": bus, "km": km, "variable": var, "valor": valor_post,
                                        "origen": "Medido", "registrado_por": who}])
    if prueba:
        almacen.agregar("pruebas", [{"fecha": fecha, "bus": bus, "prueba": prueba, "resultado": "Pasa", "origen": "Medido",
                                     "registrado_por": who}])


def excel(d, e, p):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        d.to_excel(w, sheet_name="mediciones", index=False)
        e.to_excel(w, sheet_name="eventos", index=False)
        p.to_excel(w, sheet_name="pruebas", index=False)
    return buf.getvalue()


# ================================================================== ÓRDENES
@st.dialog("Cerrar orden")
def cerrar_orden(o):
    var = VAR_DE_MODO.get(o["modo"])
    prueba = next((k_ for k_, p in PRUEBAS.items() if p["modo"] == o["modo"]), None) if var is None else None
    st.markdown(f"**{o['bus']}** · {o['hallazgo']}")
    st.caption(o["tarea"])
    hoy = max(dt.date.today(), CORTE.date())
    c1, c2 = st.columns(2)
    fecha = c1.date_input("Fecha", value=hoy, min_value=CORTE.date())
    km = c2.number_input("Odómetro (km)", min_value=0, step=10, value=km_sugerido(o["bus"], fecha))
    valor_post = None
    if var:
        c = VARIABLES[var]
        nominal = c["nominal"]
        valor_post = st.number_input(f"{c['corto']} después de reparar ({c['unidad']})", min_value=RANGO[var][0],
                                     max_value=RANGO[var][1], step=PASO[var], value=float(nominal))
    c3, c4 = st.columns(2)
    horas = c3.number_input("Horas", min_value=0.0, step=0.5, value=float(o["horas"]))
    costo = c4.number_input("Costo (COP)", min_value=0, step=50_000, value=int(o["costo"]))
    quien = st.text_input("Técnico")
    if st.button("Cerrar orden", type="primary", icon=":material/task_alt:", width="stretch"):
        km_prev, _ = ultimo_km(o["bus"], fecha)
        if km < km_prev:
            st.error(f"El odómetro debe ser ≥ {fmt(km_prev)} km.")
            return
        guardar_reparacion(o["bus"], pd.Timestamp(fecha), km, o["modo"], False, horas, costo, valor_post,
                           f"Cierre {o['id']}: {o['hallazgo']}", quien, prueba=prueba)
        st.session_state.orden_cerrada = o["id"]
        st.rerun()


def pagina_ordenes():
    ots, avisos = FOTO["ots"], FOTO["avisos"]
    st.markdown("## Órdenes de trabajo")
    if st.session_state.pop("orden_cerrada", None):
        st.toast("Orden cerrada y reparación registrada", icon=":material/task_alt:")
    cols = st.columns(3, gap="medium")
    for col, p in zip(cols, ("P1", "P2", "P3")):
        lista = [o for o in ots if o["prioridad"] == p]
        nombre = PRIORIDADES[p]["nombre"].split("·")[-1].strip()
        col.markdown(f'<div style="border-bottom:3px solid {COLOR_P[p]};padding-bottom:4px;margin-bottom:10px">'
                     f'<b style="font-size:17px">{p} · {nombre}</b> <span class="sub">({len(lista)})</span><br>'
                     f'<span class="sub">{PRIORIDADES[p]["plazo"].split(";")[0].split("(")[0]}</span></div>', unsafe_allow_html=True)
        if not lista:
            col.caption("Sin órdenes")
        for o in lista:
            with col.container(border=True):
                vence = (o["fecha_limite"] - CORTE).days
                st.markdown(f'<b style="font-size:16px">{o["bus"]}</b> &nbsp;<span class="sub">{o["id"]}</span><br>'
                            f'{o["hallazgo"]}<br><span class="sub">{o["tarea"].split(";")[0]}</span><br>'
                            f'<span class="sub">{"hoy" if vence <= 0 else f"en {vence} días"} · {fmt(o["horas"], 1)} h · '
                            f'${fmt(o["costo"])}</span>', unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                if b1.button("Cerrar", key=f"cerrar_{o['id']}", icon=":material/check:", width="stretch"):
                    cerrar_orden(o)
                with b2.popover("Detalle", width="stretch"):
                    st.markdown(f"**Modo:** {o['modo_nombre']} (S {o['S']}, NPR {o['NPR']})\n\n**Efecto:** {o['efecto']}\n\n"
                                f"**Tarea completa:** {o['tarea']}\n\n**Recurso:** {o['recurso']}\n\n**Regla:** {o['regla']}\n\n"
                                f"**Umbral:** {o['fuente_umbral']}")
    if avisos:
        st.markdown("#### En vigilancia")
        st.caption("Sin orden: medir con más frecuencia.")
        corto = {VARIABLES[v]["nombre"]: VARIABLES[v]["corto"] for v in ORDEN_VARIABLES}
        st.markdown(" ".join(pill("Vigilancia", f"{a['Bus']} · {corto.get(a['Variable'], a['Variable'])} "
                                                f"{fmt(a['Valor'], 2 if a['Unidad'] == 'bar/min' else 1)} {a['Unidad']}")
                             for a in avisos), unsafe_allow_html=True)


# ================================================================== INDICADORES
def pagina_indicadores():
    mens, k, ev = kpis(VER, CORTE)
    st.markdown(f"## Indicadores · {CORTE.year}")
    c1, c2, c3, c4 = st.columns(4)

    def tile(col, titulo, valor, meta, mejor_alto, sufijo):
        ok = (valor >= meta) if mejor_alto else (valor <= meta)
        kpi(col, titulo, f"{valor}{sufijo}" if isinstance(valor, str) else f"{fmt(valor, 1 if sufijo in (' %', ' h') else 0)}{sufijo}",
            f"meta {'≥' if mejor_alto else '≤'} {fmt(meta, 1 if sufijo in (' %', ' h') else 0)}{sufijo}",
            COLOR_NIVEL["Normal"] if ok else COLOR_NIVEL["Alarma"])

    tile(c1, "Disponibilidad", k["disponibilidad"], METAS["disponibilidad"]["valor"], True, " %")
    tile(c2, "MTBF (km entre fallas)", k["mtbf_km"] if k["mtbf_km"] == k["mtbf_km"] else 0, METAS["mtbf_km"]["valor"], True, " km")
    tile(c3, "MTTR", k["mttr_h"] if k["mttr_h"] == k["mttr_h"] else 0, METAS["mttr_h"]["valor"], False, " h")
    kpi(c4, "Costo vs presupuesto", f"{k['costo'] / k['presupuesto'] * 100:.0f} %", f"${fmt(k['costo'] / 1e6, 1)} M de ${fmt(k['presupuesto'] / 1e6, 1)} M",
        COLOR_NIVEL["Normal"] if k["costo"] <= k["presupuesto"] else COLOR_NIVEL["Alarma"])
    st.write("")

    def base_fig(alto=260):
        f = go.Figure()
        f.update_layout(height=alto, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="white", showlegend=False)
        f.update_yaxes(gridcolor="#f0f2f5")
        return f

    g1, g2 = st.columns(2, gap="large")
    with g1:
        f = base_fig()
        meta = METAS["disponibilidad"]["valor"]
        f.add_bar(x=mens["mes"], y=mens["disponibilidad"], marker_color=[COLOR_NIVEL["Normal"] if v >= meta else COLOR_NIVEL["Alarma"]
                                                                         for v in mens["disponibilidad"]])
        f.add_hline(y=meta, line_dash="dash", annotation_text=f"meta {meta:g} %", annotation_position="bottom right")
        f.update_layout(title="Disponibilidad por mes (%)", yaxis_range=[min(85, mens["disponibilidad"].min() - 1), 100.5])
        st.plotly_chart(f, width="stretch", config={"displayModeBar": False})
    with g2:
        f = base_fig()
        f.add_scatter(x=mens["mes"], y=mens["costo_acum"] / 1e6, mode="lines+markers", line=dict(color="#1f2a44", width=2.5), name="Gasto")
        f.add_scatter(x=mens["mes"], y=mens["presupuesto_acum"] / 1e6, mode="lines", line=dict(color=GRIS, dash="dash"), name="Presupuesto")
        f.update_layout(title="Gasto acumulado vs presupuesto (millones COP)", showlegend=True, legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(f, width="stretch", config={"displayModeBar": False})
    g3, g4 = st.columns(2, gap="large")
    with g3:
        f = base_fig()
        f.add_scatter(x=mens["mes"], y=mens["mtbf_km"], mode="lines+markers", line=dict(color="#1f2a44", width=2.5))
        f.add_hline(y=METAS["mtbf_km"]["valor"], line_dash="dash", annotation_text="meta", annotation_position="bottom right")
        f.update_layout(title="MTBF acumulado (km entre fallas en ruta)")
        st.plotly_chart(f, width="stretch", config={"displayModeBar": False})
    with g4:
        f = base_fig()
        cnt = ev.groupby("modo").agg(n=("modo", "size"), costo=("costo", "sum")).reset_index().sort_values("costo")
        f.add_bar(y=[MODOS[int(m)]["nombre"][:32] for m in cnt["modo"]], x=cnt["costo"] / 1e6, orientation="h",
                  marker_color="#3b6fb6", text=[f"{n} interv." for n in cnt["n"]], textposition="auto")
        f.update_layout(title="¿En qué se gasta? (millones COP)")
        st.plotly_chart(f, width="stretch", config={"displayModeBar": False})
    with st.popover("Fórmulas y metas", icon=":material/help:"):
        st.markdown("- **Disponibilidad** = 1 − horas de paro por frenos / horas programadas (16 h × días × buses)\n"
                    "- **MTBF** = km recorridos / fallas en ruta\n- **MTTR** = horas de paro promedio por falla en ruta")
        st.dataframe(pd.DataFrame([{"Indicador": n, "Meta": f"{m['valor']:,} {m['unidad']}", "Origen": m["origen"]}
                                   for n, m in METAS.items()]), hide_index=True)


# ================================================================== ASISTENTE
SUGERENCIAS = ["¿Qué buses no pueden salir hoy?", "¿Qué órdenes son urgentes?", "¿Cómo están los forros?",
               "¿Cuánto le falta al B-05 para el paro?", "¿Cuál es el umbral de fuga?", "¿Cómo vamos en indicadores?"]


def pagina_asistente():
    st.markdown("## Asistente")
    clave = asistente.clave_api(st.secrets if _hay_secrets() else None, st.session_state.get("api_key"))
    a, b = st.columns([4, 1])
    a.markdown(pill("Normal", "IA conectada") if clave else pill("Sin dato", "Modo básico (sin IA)"), unsafe_allow_html=True)
    with b.popover("Conectar IA", icon=":material/key:", width="stretch"):
        st.text_input("Clave de API de Anthropic", type="password", key="api_key", help="Se usa solo en esta sesión; no se guarda.")
        st.text_input("Modelo", value=asistente.MODELO_IA, key="modelo_ia")
        st.caption("Sin clave, el asistente responde las preguntas frecuentes con los datos del tablero.")
    if "chat" not in st.session_state:
        st.session_state.chat = []

    pregunta = None
    if not st.session_state.chat:
        pregunta = st.pills("Preguntas frecuentes", SUGERENCIAS, key="sug", label_visibility="collapsed")
    for m in st.session_state.chat:
        with st.chat_message(m["rol"], avatar=":material/person:" if m["rol"] == "user" else ":material/build:"):
            st.markdown(m["texto"])
    escrita = st.chat_input("Pregunte por un bus, una variable, las órdenes…")
    pregunta = escrita or pregunta
    if pregunta:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(pregunta)
        with st.chat_message("assistant", avatar=":material/build:"):
            with st.spinner(""):
                resp = None
                if clave:
                    try:
                        resp = asistente.responder_ia(pregunta, st.session_state.chat, FOTO, clave,
                                                      st.session_state.get("modelo_ia") or asistente.MODELO_IA)
                    except Exception as ex:
                        st.caption(f"No se pudo usar la IA ({str(ex)[:80]}). Respuesta en modo básico:")
                if not resp:
                    resp = asistente.responder_basico(pregunta, FOTO)
            st.markdown(resp)
        st.session_state.chat += [{"rol": "user", "texto": pregunta}, {"rol": "assistant", "texto": resp}]
    if st.session_state.chat:
        if st.button("Nueva conversación", icon=":material/refresh:"):
            st.session_state.chat = []
            st.session_state.pop("sug", None)
            st.rerun()


def _hay_secrets():
    try:
        return "ANTHROPIC_API_KEY" in st.secrets
    except Exception:
        return False


# ================================================================== REFERENCIA
def pagina_referencia():
    st.markdown("## Referencia")
    sec = st.segmented_control("Sección", ["Umbrales", "Curva P-F", "RCM", "Supuestos y fuentes", "Importar datos"],
                               default="Umbrales", key="ref_sec", label_visibility="collapsed") or "Umbrales"
    if sec == "Umbrales":
        filas = []
        for v in ORDEN_VARIABLES:
            c = VARIABLES[v]
            s = "≤" if c["sentido"] == "baja" else "≥"
            filas.append({"Variable": c["nombre"], "Normal": f"{c['nominal']:g}", "Vigilancia": f"{s} {c['vigilancia']:g}",
                          "Alerta (P)": f"{s} {c['alerta']:g}", "Paro": f"{s} {c['alarma']:g}", "F": f"{c['F']:g}",
                          "Unidad": c["unidad"], "Se mide": c["frecuencia"], "Cómo": c["metodo"]})
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
        v = st.selectbox("Fuente de cada umbral", ORDEN_VARIABLES, format_func=lambda v: VARIABLES[v]["nombre"])
        c = VARIABLES[v]
        st.dataframe(pd.DataFrame([{"Nivel": n, "Origen": c["origen_umbral"][n], "Fuente": c["fuentes"][n]}
                                   for n in ("vigilancia", "alerta", "alarma", "F")]), hide_index=True, width="stretch")
        st.markdown("**Pruebas diarias**")
        st.dataframe(pd.DataFrame([{"Prueba": p["nombre"], "Criterio": p["criterio"], "Fuente": p["fuente"]} for p in PRUEBAS.values()]),
                     hide_index=True, width="stretch")
    elif sec == "Curva P-F":
        v = st.segmented_control("Variable", ORDEN_VARIABLES, default="espesor", format_func=lambda v: VARIABLES[v]["corto"],
                                 key="pf_var") or "espesor"
        c = VARIABLES[v]
        pf = c["pf_km"][0]
        x_al = pf * (c["alerta"] - c["alarma"]) / (c["alerta"] - c["F"])
        px, py = [-0.35 * pf, 0, x_al, pf], [c["nominal"], c["alerta"], c["alarma"], c["F"]]
        xs = np.linspace(px[0], px[-1], 80)
        f = go.Figure(go.Scatter(x=xs, y=np.interp(xs, px, py), mode="lines", line=dict(color="#1f2a44", width=3),
                                 hoverinfo="skip", showlegend=False))
        for x_, y_, txt, col in [(0, c["alerta"], f"P · {c['alerta']:g}", COLOR_NIVEL["Alerta"]),
                                 (x_al, c["alarma"], f"Paro · {c['alarma']:g}", COLOR_NIVEL["Alarma"]), (pf, c["F"], f"F · {c['F']:g}", "#333")]:
            f.add_trace(go.Scatter(x=[x_], y=[y_], mode="markers+text", marker=dict(size=13, color=col), text=[txt],
                                   textposition="top right" if c["sentido"] == "baja" else "bottom right", showlegend=False))
        f.add_vrect(x0=x_al, x1=pf, fillcolor=COLOR_NIVEL["Alarma"], opacity=0.07, line_width=0)
        f.update_layout(height=330, margin=dict(l=10, r=60, t=10, b=10), plot_bgcolor="white",
                        xaxis_title="km desde el punto P", yaxis_title=f"{c['corto']} ({c['unidad']})")
        st.plotly_chart(f, width="stretch")
        a1, a2, a3 = st.columns(3)
        kpi(a1, "Intervalo P-F", f"{fmt(pf)} km", f"hasta {fmt(c['pf_km'][1])} km")
        kpi(a2, "Margen paro → F", f"{fmt(pf - x_al)} km", f"reacción del taller {OPERACION['km_reaccion']} km")
        kpi(a3, "Se mide", c["frecuencia"], "debe ser ≤ ½ P-F")
    elif sec == "RCM":
        st.caption("SAE JA1011/JA1012 · Moubray (RCM II) · sobre el AMFEC y la curva P-F del grupo")
        st.dataframe(pd.DataFrame([{"Modo": f"{k_} · {MODOS[k_]['nombre']}", "S": MODOS[k_]["S"], "NPR": MODOS[k_]["NPR"],
                                    "Consecuencia": r["consecuencia"], "Tarea": r["tarea"], "Intervalo": r["intervalo"],
                                    "Horas": r["horas"], "Costo": f"${fmt(r['costo'])}"} for k_, r in RCM.items()]),
                     hide_index=True, width="stretch", height=390)
        st.dataframe(pd.DataFrame([{"Prioridad": p["nombre"], "Regla": p["regla"], "Plazo": p["plazo"]} for p in PRIORIDADES.values()]),
                     hide_index=True, width="stretch")
    elif sec == "Supuestos y fuentes":
        st.markdown("**Origen de los datos:** Medido (ingresado en la plataforma) · Inferido (calculado) · Supuesto (asumido) · "
                    "Simulado (historial de demostración)")
        st.dataframe(pd.DataFrame(SUPUESTOS, columns=["Supuesto", "Origen", "Justificación"]), hide_index=True, width="stretch")
        with st.expander("Limitaciones"):
            st.markdown("\n".join(f"- {x}" for x in LIMITACIONES))
        with st.expander("Referencias"):
            st.markdown("\n".join(f"- {x}" for x in REFERENCIAS))
    else:
        st.caption("Suba un Excel o CSV con columnas fecha, bus, km, variable, valor. Las filas se agregan a los registros como «Medido».")
        archivo = st.file_uploader("Archivo", type=["csv", "xlsx"], label_visibility="collapsed")
        if archivo is not None:
            try:
                if archivo.name.lower().endswith(".csv"):
                    d = pd.read_csv(archivo)
                else:
                    hojas = pd.read_excel(archivo, sheet_name=None)
                    d = next((h for n, h in hojas.items() if n.strip().lower() == "mediciones"), list(hojas.values())[0])
                d.columns = [str(c).strip().lower() for c in d.columns]
                faltan = {"fecha", "bus", "km", "variable", "valor"} - set(d.columns)
                if faltan:
                    raise ValueError("faltan columnas: " + ", ".join(sorted(faltan)))
                d = d[d["variable"].astype(str).isin(VARIABLES)].copy()
                d["fecha"] = pd.to_datetime(d["fecha"])
                d["origen"] = d.get("origen", "Medido")
                d["registrado_por"] = "Importado"
                st.dataframe(d.head(10), hide_index=True)
                if st.button(f"Agregar {len(d)} mediciones", type="primary"):
                    almacen.agregar("mediciones", d.to_dict("records"))
                    st.success("Importado.")
                    st.rerun()
            except Exception as ex:
                st.error(f"No se pudo leer el archivo: {ex}")
        plantilla = pd.DataFrame({"fecha": ["2026-11-25"] * 2, "bus": ["B-01"] * 2, "km": [262000] * 2,
                                  "variable": ["fuga", "agua"], "valor": [0.03, 2]})
        st.download_button("Descargar plantilla", plantilla.to_csv(index=False).encode("utf-8"), "plantilla_mediciones.csv",
                           icon=":material/download:")
        st.caption("Variables válidas: " + ", ".join(f"{v} ({VARIABLES[v]['unidad']})" for v in ORDEN_VARIABLES))
        st.download_button("Descargar todos los datos (Excel)", excel(DATOS, EVENTOS, PRUEBAS_DF), "datos_frenos.xlsx",
                           icon=":material/download:")


# ================================================================== NAVEGACIÓN
PAG = {
    "flota": st.Page(pagina_flota, title="Flota", icon=":material/dashboard:", url_path="flota", default=True),
    "bus": st.Page(pagina_bus, title="Bus", icon=":material/directions_bus:", url_path="bus"),
    "registrar": st.Page(pagina_registrar, title="Registrar", icon=":material/edit_note:", url_path="registrar"),
    "ordenes": st.Page(pagina_ordenes, title=f"Órdenes ({len(FOTO['ots'])})", icon=":material/assignment:", url_path="ordenes"),
    "indicadores": st.Page(pagina_indicadores, title="Indicadores", icon=":material/monitoring:", url_path="indicadores"),
    "asistente": st.Page(pagina_asistente, title="Asistente", icon=":material/forum:", url_path="asistente"),
    "referencia": st.Page(pagina_referencia, title="Referencia", icon=":material/menu_book:", url_path="referencia"),
}
LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.svg")
if os.path.exists(LOGO):
    st.logo(LOGO, size="large")
st.navigation(list(PAG.values()), position="top").run()
