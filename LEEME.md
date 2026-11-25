# Plataforma de taller · Frenos de aire
Altos de la Sabana S.A.S. · Flota de buses Bogotá–Cajicá · Taller en Énfasis II (Gestión de Mantenimiento)

## Cómo abrirla
**En VS Code:** abra esta carpeta (la que contiene `app.py`), abra una terminal y ejecute
```
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
**En Windows con doble clic:** `INSTALAR.bat` (solo la primera vez) y luego `INICIAR.bat`.

**Link para compartir:** suba la carpeta a GitHub y publíquela en share.streamlit.io con `app.py` como archivo principal.

## Páginas
| Página | Para qué sirve |
|---|---|
| **Flota** | Qué buses pueden salir hoy, días que le quedan a cada variable antes del paro y tareas del día. |
| **Bus** | Estado de un bus: 5 variables, modelo 3D, pruebas del día, índice de salud y tendencia. |
| **Registrar** | Inspección diaria (conductor), revisión de taller, reparaciones y el historial de lo ingresado. |
| **Órdenes** | Órdenes P1 / P2 / P3. «Cerrar» registra la reparación y la medición de verificación. |
| **Indicadores** | Disponibilidad, MTBF, MTTR y costo contra las metas. |
| **Asistente** | Preguntas en lenguaje natural sobre la flota. |
| **Referencia** | Umbrales y fuentes, curva P-F, RCM, supuestos, importación de datos. |

## Asistente con IA
Sin clave funciona en **modo básico** (responde las preguntas frecuentes con los datos del tablero).
Para activar la IA (Claude): botón **«Conectar IA»** y pegue una clave de API de Anthropic, o cree
`.streamlit/secrets.toml` a partir de `secrets.toml.example`. La clave nunca se escribe en el código.

## Datos
- Historial base **simulado** (5 buses, ene–nov 2026). Escenarios: B-01 normal · B-02 forros en alerta · B-03 fuga en paro · B-04 secador en alerta · B-05 freno que arrastra.
- Lo que se ingresa en **Registrar** u **Órdenes** se guarda en la carpeta `datos/` como «Medido». Para empezar de cero: Registrar → Mis registros → Borrar.
- En Streamlit Cloud los registros se pierden cuando la app se reinicia (el servidor no guarda archivos de forma permanente).
- Demostración para la sustentación: barra lateral → «Ver el sistema en una fecha pasada» → «Demostración: fuga del B-03» y mover la fecha.

## Archivos
| Archivo | Qué contiene |
|---|---|
| `config.py` | Variables, umbrales y fuentes, pesos, RCM, prioridades, supuestos y metas. **Todo parámetro se cambia aquí.** |
| `simulador.py` | Historial simulado con fallas progresivas. |
| `almacen.py` | Guarda y une los registros ingresados por los usuarios. |
| `motor.py` | Niveles, índice de salud, tendencias, km hasta el umbral, órdenes e indicadores. |
| `asistente.py` | Asistente: modo básico y conexión a la IA. |
| `modelo3d.py` | Modelo 3D esquemático del sistema de frenos. |
| `app.py` | Las páginas de la plataforma. |
