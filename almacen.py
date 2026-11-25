"""
ALMACÉN DE DATOS
Une el historial base (simulado) con los registros que ingresan los usuarios desde la plataforma.
Los registros nuevos se guardan en la carpeta datos/ como CSV, así no se pierden al cerrar la app.
"""
import os

import pandas as pd

import simulador

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
ARCH = {
    "mediciones": os.path.join(CARPETA, "registros_mediciones.csv"),
    "eventos": os.path.join(CARPETA, "registros_eventos.csv"),
    "pruebas": os.path.join(CARPETA, "registros_pruebas.csv"),
}
COLS = {
    "mediciones": ["fecha", "bus", "km", "variable", "valor", "origen", "registrado_por"],
    "eventos": ["fecha", "bus", "km", "modo", "variable", "tipo", "detiene_servicio", "descripcion", "tarea",
                "horas_paro", "costo", "origen", "registrado_por"],
    "pruebas": ["fecha", "bus", "prueba", "resultado", "origen", "registrado_por"],
}


def _leer(tipo):
    if not os.path.exists(ARCH[tipo]):
        return pd.DataFrame(columns=COLS[tipo])
    df = pd.read_csv(ARCH[tipo])
    if len(df):
        df["fecha"] = pd.to_datetime(df["fecha"])
    if tipo == "eventos" and len(df):
        df["detiene_servicio"] = df["detiene_servicio"].astype(str).str.lower().isin(["true", "1", "sí", "si"])
        df["variable"] = df["variable"].where(df["variable"].notna(), None)
    return df


def registros_usuario():
    return {t: _leer(t) for t in ARCH}


def cargar(base=None):
    """Historial base + registros del usuario, ordenados."""
    d, e, p = base if base is not None else simulador.simular()
    u = registros_usuario()
    if len(u["mediciones"]):
        d = pd.concat([d, u["mediciones"][d.columns.intersection(u["mediciones"].columns)]], ignore_index=True)
    if len(u["eventos"]):
        e = pd.concat([e, u["eventos"][e.columns.intersection(u["eventos"].columns)]], ignore_index=True)
    if len(u["pruebas"]):
        p = pd.concat([p, u["pruebas"][p.columns.intersection(u["pruebas"].columns)]], ignore_index=True)
    d["fecha"] = pd.to_datetime(d["fecha"])
    e["fecha"] = pd.to_datetime(e["fecha"])
    p["fecha"] = pd.to_datetime(p["fecha"])
    d = d.sort_values(["bus", "variable", "fecha", "km"], kind="stable").reset_index(drop=True)
    e = e.sort_values(["fecha", "bus"], kind="stable").reset_index(drop=True)
    p = p.sort_values(["fecha", "bus"], kind="stable").reset_index(drop=True)
    return d, e, p


def agregar(tipo, filas):
    os.makedirs(CARPETA, exist_ok=True)
    nuevo = pd.DataFrame(filas)
    for c in COLS[tipo]:
        if c not in nuevo.columns:
            nuevo[c] = None
    nuevo = nuevo[COLS[tipo]]
    previo = _leer(tipo)
    todo = pd.concat([previo, nuevo], ignore_index=True) if len(previo) else nuevo
    todo.to_csv(ARCH[tipo], index=False)


def borrar_registros():
    for f in ARCH.values():
        if os.path.exists(f):
            os.remove(f)
