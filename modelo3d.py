"""
MODELO 3D ESQUEMÁTICO DEL SISTEMA DE FRENOS DE AIRE
Chasis, ruedas con tambor, cámaras de freno (pulmones), compresor, secador, tanques,
válvula de pedal y líneas de aire. Cada componente toma el color del nivel de la variable
que lo vigila. Es un esquema simplificado, no el plano del fabricante.
"""
import numpy as np
import plotly.graph_objects as go

from config import COLOR_NIVEL, VARIABLES

GRIS = "#9aa0a6"


def _cilindro(c, r, largo, eje, n=28):
    """Malla de un cilindro cerrado. c = centro, eje = 'x' | 'y' | 'z'."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    a, b = r * np.cos(t), r * np.sin(t)
    h = largo / 2
    if eje == "y":
        p1 = np.c_[c[0] + a, np.full(n, c[1] - h), c[2] + b]
        p2 = np.c_[c[0] + a, np.full(n, c[1] + h), c[2] + b]
    elif eje == "x":
        p1 = np.c_[np.full(n, c[0] - h), c[1] + a, c[2] + b]
        p2 = np.c_[np.full(n, c[0] + h), c[1] + a, c[2] + b]
    else:
        p1 = np.c_[c[0] + a, c[1] + b, np.full(n, c[2] - h)]
        p2 = np.c_[c[0] + a, c[1] + b, np.full(n, c[2] + h)]
    pts = np.vstack([p1, p2, [np.mean(p1, 0)], [np.mean(p2, 0)]])
    i, j, k = [], [], []
    for s in range(n):
        s2 = (s + 1) % n
        i += [s, s2]; j += [s2, n + s2]; k += [n + s, n + s]
        i += [2 * n, 2 * n + 1]; j += [s2, n + s]; k += [s, n + s2]
    return pts, i, j, k


def _caja(c, d):
    x0, x1 = c[0] - d[0] / 2, c[0] + d[0] / 2
    y0, y1 = c[1] - d[1] / 2, c[1] + d[1] / 2
    z0, z1 = c[2] - d[2] / 2, c[2] + d[2] / 2
    pts = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                    [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    i = [0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3]
    j = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4]
    k = [2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7]
    return pts, i, j, k


def _malla(fig, geo, color, hover, opacidad=1.0):
    pts, i, j, k = geo
    fig.add_trace(go.Mesh3d(x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], i=i, j=j, k=k, color=color,
                            opacity=opacidad, flatshading=True, hovertext=hover, hoverinfo="text",
                            lighting=dict(ambient=0.55, diffuse=0.8, specular=0.2), showlegend=False))


def _linea(fig, pts, color, hover, ancho=9):
    pts = np.array(pts)
    fig.add_trace(go.Scatter3d(x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], mode="lines",
                               line=dict(color=color, width=ancho), hovertext=hover, hoverinfo="text", showlegend=False))


def _txt(var, tabla):
    r = tabla.set_index("var").loc[var]
    c = VARIABLES[var]
    v = "sin dato" if r["Valor"] is None or r["Valor"] != r["Valor"] else f"{r['Valor']:g} {c['unidad']}"
    return r["Nivel"], f"{c['nombre']}: {v} · <b>{r['Nivel']}</b>"


def figura(tabla, peor_rueda, alto=520):
    """tabla: estado_bus()['tabla']; peor_rueda: nivel combinado de forros y temperatura."""
    fig = go.Figure()

    # Carrocería (silueta translúcida) y chasis
    _malla(fig, _caja((4.1, 0, 1.75), (9.6, 2.5, 2.3)), "#cfd8e3", "Carrocería del bus (referencia)", 0.10)
    for y in (-0.55, 0.55):
        _malla(fig, _caja((4.3, y, 0.62), (8.6, 0.14, 0.22)), GRIS, "Larguero del chasis")
    for x in (1.6, 3.6, 5.6, 7.6):
        _malla(fig, _caja((x, 0, 0.62), (0.12, 1.1, 0.16)), GRIS, "Travesaño del chasis")

    n_f, h_f = _txt("espesor", tabla)
    n_t, h_t = _txt("dT", tabla)
    n_fu, h_fu = _txt("fuga", tabla)
    n_a, h_a = _txt("agua", tabla)
    n_r, h_r = _txt("recarga", tabla)

    # Ejes, ruedas y tambores (delantero sencillo, trasero dual)
    ruedas = [(1.6, -1.18), (1.6, 1.18), (5.6, -1.05), (5.6, -1.37), (5.6, 1.05), (5.6, 1.37)]
    for x in (1.6, 5.6):
        _malla(fig, _cilindro((x, 0, 0.5), 0.07, 2.5, "y"), "#6b7280", "Eje")
    for x, y in ruedas:
        _malla(fig, _cilindro((x, y, 0.5), 0.5, 0.26, "y"), "#2b2b2b", "Llanta", 0.85)
        _malla(fig, _cilindro((x, y * 0.9, 0.5), 0.3, 0.12, "y"), COLOR_NIVEL[peor_rueda],
               f"<b>Tambor y forros</b><br>{h_f}<br>{h_t}")
        if abs(y) in (1.18, 1.37):  # disco de color en la cara exterior para ver el estado
            cara = y + (0.14 if y > 0 else -0.14)
            _malla(fig, _cilindro((x, cara, 0.5), 0.3, 0.03, "y"), COLOR_NIVEL[peor_rueda],
                   f"<b>Tambor y forros</b><br>{h_f}<br>{h_t}")

    # Cámaras de freno (pulmones) junto a cada rueda, colores por fuga
    camaras = [(1.95, -0.85), (1.95, 0.85), (5.95, -0.8), (5.95, 0.8)]
    for x, y in camaras:
        _malla(fig, _cilindro((x, y, 0.8), 0.16, 0.22, "x"), COLOR_NIVEL[n_fu],
               f"<b>Cámara de freno (pulmón)</b><br>{h_fu}")

    # Compresor (en el motor), secador, tanques y válvula de pedal
    _malla(fig, _caja((0.7, 0.45, 0.95), (0.45, 0.35, 0.35)), COLOR_NIVEL[n_r], f"<b>Compresor</b><br>{h_r}")
    _malla(fig, _cilindro((2.5, 0.85, 0.95), 0.16, 0.45, "z"), COLOR_NIVEL[n_a], f"<b>Secador de aire</b><br>{h_a}")
    for y in (-0.85, 0.85):
        _malla(fig, _cilindro((3.9, y, 0.85), 0.22, 1.3, "x"), COLOR_NIVEL[n_a],
               f"<b>Tanque de aire</b><br>{h_a}")
    _malla(fig, _caja((0.35, -0.7, 1.35), (0.2, 0.2, 0.25)), "#6b7280",
           "<b>Válvula de pedal</b><br>Se vigila de forma indirecta con ΔT entre ruedas (modo 10)")

    # Líneas de aire: compresor → secador → tanques → cámaras (color por fuga)
    c_l = COLOR_NIVEL[n_fu]
    _linea(fig, [(0.92, 0.45, 0.95), (2.35, 0.85, 0.95)], c_l, f"Línea de descarga<br>{h_fu}")
    _linea(fig, [(2.5, 0.85, 0.72), (3.25, 0.85, 0.85)], c_l, f"Línea secador → tanque<br>{h_fu}")
    _linea(fig, [(3.25, 0.85, 0.85), (3.25, -0.85, 0.85)], c_l, f"Línea entre tanques<br>{h_fu}")
    for x, y in camaras:
        org = (3.25 if x < 3 else 4.55, 0.85 if y > 0 else -0.85, 0.85)
        _linea(fig, [org, (org[0], y, 1.05), (x, y, 1.05), (x, y, 0.95)], c_l, f"Manguera de servicio<br>{h_fu}", 7)
    _linea(fig, [(0.35, -0.7, 1.22), (3.25, -0.85, 1.22), (3.25, -0.85, 1.07)], "#6b7280", "Línea de mando (válvula de pedal)", 3)

    # Rótulos
    rot = [((0.7, 0.45, 1.35), "Compresor"), ((2.5, 0.85, 1.4), "Secador"), ((3.9, 0, 1.35), "Tanques"),
           ((1.6, 0, 0.05), "Eje delantero"), ((5.6, 0, 0.05), "Eje trasero (dual)"), ((0.35, -0.7, 1.7), "Pedal")]
    fig.add_trace(go.Scatter3d(x=[p[0][0] for p in rot], y=[p[0][1] for p in rot], z=[p[0][2] for p in rot],
                               mode="text", text=[p[1] for p in rot], textfont=dict(size=12, color="#1f2937"),
                               hoverinfo="skip", showlegend=False))

    fig.update_layout(height=alto, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
                                 aspectmode="data", camera=dict(eye=dict(x=-1.15, y=-1.35, z=0.75),
                                                                center=dict(x=0, y=0, z=-0.15))))
    return fig
