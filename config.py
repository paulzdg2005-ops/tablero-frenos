"""
CONFIGURACIÓN DEL TABLERO DE CONDICIÓN
Sistema de frenos de aire · Flota de buses Altos de la Sabana S.A.S. (Bogotá–Cajicá)

Aquí están TODOS los parámetros que la plataforma usa: variables, umbrales con su fuente,
pesos del índice de salud, RCM, supuestos, costos y metas. Cambie un número aquí y toda
la plataforma se actualiza.

Etiquetas de origen (enunciado del proyecto):
  Medido   -> lo registró un instrumento o una persona en el activo
  Inferido -> se calculó a partir de datos medidos
  Supuesto -> se asumió por falta de dato (se justifica y se lista)
  Simulado -> dato generado por el simulador de la plataforma (en operación real sería "Medido")
"""

# ------------------------------------------------------------------
# OPERACIÓN (fuente: documentos del grupo)
# ------------------------------------------------------------------
OPERACION = {
    "km_dia": 263,              # Curva P-F del grupo: 96.000 km/año
    "km_anio": 96_000,          # AMFEC y documento Altos de la Sabana
    "dias_operacion_anio": 300,  # Documento Altos de la Sabana
    "horas_dia": 16,            # AMFEC: jornadas de hasta 16 h
    "km_reaccion": 800,         # Curva P-F del grupo: hasta 3 días para programar y ejecutar
    "dias_reaccion": 3,
    "pasajeros": 40,
    "pbv_kg": 11_000,
}

FLOTA = {
    "B-01": "Chevrolet MS 4.9 · placa TSA-101",
    "B-02": "Chevrolet MS 4.9 · placa TSA-102",
    "B-03": "Chevrolet MS 4.9 · placa TSA-103",
    "B-04": "Chevrolet MS 4.9 · placa TSA-104",
    "B-05": "Chevrolet MS 4.9 · placa TSA-105",
}

# ------------------------------------------------------------------
# MODOS DE FALLA (AMFEC del grupo, tabla 6.2)
# ------------------------------------------------------------------
MODOS = {
    1: {"nombre": "Desgaste de forros bajo el espesor mínimo", "S": 9, "O": 6, "D": 5, "NPR": 270,
        "efecto": "Mayor distancia de frenado a plena carga; contacto metal-metal que raya el tambor. Riesgo de colisión con hasta 40 pasajeros."},
    2: {"nombre": "Bajo caudal del compresor", "S": 8, "O": 4, "D": 3, "NPR": 96,
        "efecto": "La presión no se recupera entre paradas; cae bajo 6,5 bar y los frenos de resorte detienen el bus en la vía."},
    3: {"nombre": "Diafragma roto en cámara de freno", "S": 8, "O": 4, "D": 4, "NPR": 128,
        "efecto": "Una rueda frena menos; el bus se desvía al frenar y se desgastan llantas y forros de forma desigual."},
    4: {"nombre": "Falla del sensor ABS", "S": 8, "O": 4, "D": 2, "NPR": 64,
        "efecto": "El ABS se desactiva; en frenada de emergencia con pavimento mojado las ruedas pueden bloquearse."},
    5: {"nombre": "Resorte de estacionamiento debilitado", "S": 9, "O": 2, "D": 6, "NPR": 108,
        "efecto": "El bus puede desplazarse estacionado en pendiente o en parada; riesgo de atropello."},
    6: {"nombre": "Alarma de baja presión inoperante", "S": 9, "O": 3, "D": 7, "NPR": 189,
        "efecto": "Falla oculta: el conductor no recibe aviso si la presión cae."},
    7: {"nombre": "Secador de aire saturado", "S": 6, "O": 6, "D": 4, "NPR": 144,
        "efecto": "Agua y aceite llegan a tanques, líneas y válvulas: corrosión y agarrotamiento (lleva al modo 10)."},
    8: {"nombre": "Fuga en mangueras o racores", "S": 9, "O": 5, "D": 4, "NPR": 180,
        "efecto": "Menor capacidad de frenado; el compresor trabaja más; posible detención en ruta si se rompe una manguera."},
    9: {"nombre": "Sobrecalentamiento de frenos (fading)", "S": 9, "O": 3, "D": 7, "NPR": 189,
        "efecto": "Los forros pierden fricción; en el caso extremo se pierde casi todo el frenado."},
    10: {"nombre": "Válvula de pedal o relé agarrotada", "S": 7, "O": 3, "D": 5, "NPR": 105,
         "efecto": "Frenadas bruscas o freno que no suelta del todo; caídas de pasajeros y desgaste acelerado."},
}

# ------------------------------------------------------------------
# VARIABLES DE CONDICIÓN (5) Y UMBRALES DE CUATRO NIVELES
#   sentido = "sube": el valor empeora al subir; "baja": empeora al bajar
#   nominal  -> sub-índice 100
#   vigilancia -> 80  (nivel adicional; mitad del camino entre nominal y alerta)
#   alerta  -> 60  (punto P de la curva P-F)
#   alarma  -> 20  (detención obligatoria, antes del punto F)
#   F       -> 0   (falla funcional)
# ------------------------------------------------------------------
VARIABLES = {
    "espesor": {
        "nombre": "Espesor de forros", "corto": "Forros", "unidad": "mm", "sentido": "baja",
        "metodo": "Calibrador de profundidad en el centro de la zapata; se registra la rueda más desgastada",
        "frecuencia": "Cada 5.000 km (taller)", "frec_km": 5_000, "ejecutor": "Técnico de frenos",
        "modo": 1, "modos_secundarios": [],
        "nominal": 18.0, "vigilancia": 14.0, "alerta": 10.0, "alarma": 7.0, "F": 6.4,
        "tendencia": "lineal",
        "justif_tendencia": "El forro pierde material a ritmo casi constante por cada frenada (0,30 mm cada 1.000 km según la curva P-F del grupo).",
        "pf_km": (13_300, 20_000),
        "fuentes": {
            "alerta": "Curva P-F del grupo: P1 = espesor ≤ 10 mm (forro nuevo 18 mm)",
            "alarma": "Documento RCM del proyecto: 7 mm deja 0,6 mm ≈ 2.000 km de margen sobre F, más que el tiempo de reacción de 800 km",
            "F": "49 CFR 393.47(d): frenos de aire de tambor, ejes no direccionales, mínimo 6,4 mm (1/4 in)",
            "vigilancia": "Documento RCM del proyecto (punto medio entre nuevo y P)",
        },
        "origen_umbral": {"alerta": "Medido (documento del grupo)", "alarma": "Supuesto", "F": "Norma", "vigilancia": "Supuesto"},
    },
    "dT": {
        "nombre": "Diferencia de temperatura entre ruedas del mismo eje", "corto": "ΔT ruedas", "unidad": "°C", "sentido": "sube",
        "metodo": "Pirómetro infrarrojo en los tambores al llegar a patio; ΔT = rueda más caliente − la del lado opuesto",
        "frecuencia": "Semanal (técnico)", "frec_km": 1_578, "ejecutor": "Técnico de frenos",
        "modo": 9, "modos_secundarios": [10],
        "nominal": 0.0, "vigilancia": 14.0, "alerta": 28.0, "alarma": 56.0, "F": 80.0,
        "tendencia": "exponencial",
        "justif_tendencia": "Un freno que arrastra se calienta, el forro se cristaliza y frena peor, lo que obliga a frenar más: el proceso se realimenta y se acelera.",
        "pf_km": (16_000, 24_000),
        "fuentes": {
            "alerta": "HVI (2026), guía de diagnóstico de rueda caliente: más de 50 °F (≈ 28 °C) de lado a lado = investigar",
            "alarma": "Supuesto del proyecto: el doble del criterio de investigación (100 °F ≈ 56 °C)",
            "F": "Supuesto: diferencia a la que el fading ya compromete el frenado",
            "vigilancia": "HVI (2026): ruedas del mismo eje normalmente dentro de 20–30 °F (≈ 11–17 °C)",
        },
        "origen_umbral": {"alerta": "Literatura", "alarma": "Supuesto", "F": "Supuesto", "vigilancia": "Literatura"},
    },
    "fuga": {
        "nombre": "Caída de presión con el freno aplicado", "corto": "Fuga", "unidad": "bar/min", "sentido": "sube",
        "metodo": "Motor apagado, freno de servicio aplicado a fondo durante 1 minuto; se lee la caída en el manómetro",
        "frecuencia": "Diaria (conductor, inspección pre-operacional)", "frec_km": 263, "ejecutor": "Conductor / técnico",
        "modo": 8, "modos_secundarios": [3],
        "nominal": 0.0, "vigilancia": 0.05, "alerta": 0.10, "alarma": 0.20, "F": 0.40,
        "tendencia": "exponencial",
        "justif_tendencia": "Una grieta en manguera o un racor flojo se agranda con la vibración: entre más escapa el aire, más rápido crece la fuga.",
        "pf_km": (8_000, 16_000),
        "fuentes": {
            "alerta": "Documento RCM del proyecto: mitad del límite reglamentario, para tener margen de planeación",
            "alarma": "Manual CDL, sección 5 (frenos de aire): un vehículo sencillo no debe perder más de 3 psi (≈ 0,2 bar) en 1 minuto con el freno aplicado",
            "F": "Supuesto: pérdida de circuito",
            "vigilancia": "Supuesto: un cuarto del límite reglamentario",
        },
        "origen_umbral": {"alerta": "Supuesto", "alarma": "Norma", "F": "Supuesto", "vigilancia": "Supuesto"},
    },
    "agua": {
        "nombre": "Agua o aceite en la purga de tanques", "corto": "Purga", "unidad": "ml", "sentido": "sube",
        "metodo": "Purga del tanque de suministro en recipiente graduado; se registra el volumen de agua/aceite",
        "frecuencia": "Diaria (conductor, con registro)", "frec_km": 263, "ejecutor": "Conductor",
        "modo": 7, "modos_secundarios": [10],
        "nominal": 0.0, "vigilancia": 5.0, "alerta": 10.0, "alarma": 30.0, "F": 60.0,
        "tendencia": "exponencial",
        "justif_tendencia": "Cuando el desecante empieza a saturarse retiene cada vez menos humedad; el agua que pasa crece de forma acelerada.",
        "pf_km": (8_000, 16_000),
        "fuentes": {
            "alerta": "Bendix (tech tips de secadores): humedad excesiva o aceite en el tanque indica cambiar el cartucho. Cuantificación en ml: supuesto del proyecto",
            "alarma": "Supuesto del proyecto (cantidad que ya implica agua en líneas y válvulas)",
            "F": "Supuesto",
            "vigilancia": "Supuesto",
        },
        "origen_umbral": {"alerta": "Literatura + supuesto", "alarma": "Supuesto", "F": "Supuesto", "vigilancia": "Supuesto"},
    },
    "recarga": {
        "nombre": "Tiempo de recarga de 5,9 a 6,9 bar", "corto": "Recarga", "unidad": "s", "sentido": "sube",
        "metodo": "Motor en ralentí rápido; se cronometra la subida de 85 a 100 psi (5,9 a 6,9 bar) en el manómetro",
        "frecuencia": "Cada 5.000 km (taller)", "frec_km": 5_000, "ejecutor": "Técnico de frenos",
        "modo": 2, "modos_secundarios": [8],
        "nominal": 25.0, "vigilancia": 30.0, "alerta": 35.0, "alarma": 45.0, "F": 60.0,
        "tendencia": "lineal",
        "justif_tendencia": "El desgaste de anillos y válvulas del compresor es gradual: el tiempo de recarga sube poco a poco.",
        "pf_km": (16_000, 32_000),
        "fuentes": {
            "alerta": "Documento RCM del proyecto: margen antes del límite reglamentario",
            "alarma": "Manual CDL, sección 5: la presión debe subir de 85 a 100 psi en 45 s o menos (sistemas duales)",
            "F": "Supuesto: el compresor ya no recupera presión entre paradas urbanas",
            "vigilancia": "Supuesto",
        },
        "origen_umbral": {"alerta": "Supuesto", "alarma": "Norma", "F": "Supuesto", "vigilancia": "Supuesto"},
    },
}

ORDEN_VARIABLES = ["espesor", "dT", "fuga", "agua", "recarga"]

# Pesos del índice de salud: proporcionales al NPR del modo de falla que anticipa cada variable
NPR_TOTAL = sum(MODOS[VARIABLES[v]["modo"]]["NPR"] for v in ORDEN_VARIABLES)
PESOS = {v: MODOS[VARIABLES[v]["modo"]]["NPR"] / NPR_TOTAL for v in ORDEN_VARIABLES}

NIVELES = ["Normal", "Vigilancia", "Alerta", "Alarma"]
COLOR_NIVEL = {"Normal": "#1f9d55", "Vigilancia": "#8bbf3f", "Alerta": "#f0a202", "Alarma": "#d03b3b", "Sin dato": "#9a9a95"}
SUBINDICE_NIVEL = {"nominal": 100, "vigilancia": 80, "alerta": 60, "alarma": 20, "F": 0}
# Bandas del índice de salud coherentes con los sub-índices
BANDAS_IS = [(80, "Normal"), (60, "Vigilancia"), (20, "Alerta"), (-1, "Alarma")]

# ------------------------------------------------------------------
# PRUEBAS FUNCIONALES PASA / NO PASA (modos sin variable progresiva)
# ------------------------------------------------------------------
PRUEBAS = {
    "alarma": {"nombre": "Prueba de la alarma de baja presión", "modo": 6, "frecuencia": "Diaria",
               "criterio": "La alarma se activa antes de que la presión baje de 60 psi (≈ 4,1 bar)",
               "fuente": "Manual CDL, sección 5"},
    "resorte": {"nombre": "Prueba de tirón del freno de estacionamiento", "modo": 5, "frecuencia": "Diaria",
                "criterio": "Con el freno de estacionamiento aplicado, el bus no se mueve en primera marcha a bajas rpm",
                "fuente": "Curva P-F del grupo; manual CDL, sección 5"},
    "abs": {"nombre": "Testigo ABS apagado al arrancar", "modo": 4, "frecuencia": "Diaria",
            "criterio": "El testigo se enciende y se apaga en la prueba de bombillos; no se despacha un bus con el testigo encendido",
            "fuente": "Curva P-F del grupo"},
}

# ------------------------------------------------------------------
# RCM (construido con base en SAE JA1011, Moubray y la curva P-F del grupo)
#   consecuencia: categoría SAE JA1011
#   tarea: tipo de tarea según RCM
# ------------------------------------------------------------------
RCM = {
    1: {"consecuencia": "Seguridad (evidente)", "tipo": "A condición",
        "tarea": "Medir el espesor de forros en las 6 ruedas; cambiar forros del eje y medir el diámetro del tambor",
        "intervalo": "Cada 5.000 km (≤ ½ P-F más corto = 6.650 km)", "recurso": "Técnico de frenos + kit de forros por eje",
        "horas": 4.0, "costo": 1_400_000},
    2: {"consecuencia": "Operacional", "tipo": "A condición",
        "tarea": "Prueba de recarga 85→100 psi; revisar filtro de admisión, gobernador y válvulas; reparar o cambiar el compresor",
        "intervalo": "Cada 5.000 km", "recurso": "Técnico de frenos + kit de reparación del compresor",
        "horas": 6.0, "costo": 2_800_000},
    3: {"consecuencia": "Seguridad (evidente)", "tipo": "A condición",
        "tarea": "Prueba de fuga con freno aplicado y escucha en cada cámara; cambiar la cámara de servicio afectada",
        "intervalo": "Diaria", "recurso": "Técnico de frenos + cámara de servicio",
        "horas": 2.0, "costo": 550_000},
    4: {"consecuencia": "Seguridad (evidente por testigo)", "tipo": "A condición",
        "tarea": "Leer códigos de diagnóstico; limpiar y ajustar holgura sensor–anillo dentado; cambiar sensor o cable",
        "intervalo": "Cada 10.000 km + testigo diario", "recurso": "Técnico electricista + escáner",
        "horas": 1.5, "costo": 380_000},
    5: {"consecuencia": "Seguridad (oculta hasta que se exige)", "tipo": "Búsqueda de falla + a condición",
        "tarea": "Prueba de tirón diaria; inspección de corrosión de la cámara; cambiar la cámara de resorte con herramienta de enjaule",
        "intervalo": "Diaria + cada 10.000 km", "recurso": "Técnico de frenos + cámara de resorte",
        "horas": 2.5, "costo": 900_000},
    6: {"consecuencia": "Falla oculta", "tipo": "Búsqueda de falla",
        "tarea": "Probar la alarma bajando la presión con pedaleo; reparar interruptor, conector o testigo",
        "intervalo": "Diaria (FFI = 2(1−A)·MTBF ≈ 15 días; se hace a diario porque toma 2 min)", "recurso": "Conductor / técnico electricista",
        "horas": 1.0, "costo": 200_000},
    7: {"consecuencia": "Operacional / no operacional", "tipo": "A condición + reemplazo programado",
        "tarea": "Purga diaria con registro; cambiar el cartucho desecante y la válvula de purga",
        "intervalo": "Purga diaria; cartucho cada 6–12 meses en servicio urbano (Bendix)", "recurso": "Técnico + cartucho desecante",
        "horas": 1.0, "costo": 450_000},
    8: {"consecuencia": "Seguridad (evidente)", "tipo": "A condición",
        "tarea": "Prueba de fuga diaria; localizar con agua jabonosa; cambiar manguera o apretar/cambiar racor; proteger roces",
        "intervalo": "Diaria + inspección semanal bajo el chasis", "recurso": "Técnico de frenos + mangueras y racores",
        "horas": 1.5, "costo": 250_000},
    9: {"consecuencia": "Seguridad (oculta en operación)", "tipo": "A condición + rediseño",
        "tarea": "Pirometría semanal; revisar arrastre (ajustador, retorno de la válvula, resorte de zapata); capacitación en freno de motor; evaluar retardador",
        "intervalo": "Semanal", "recurso": "Técnico de frenos + pirómetro",
        "horas": 3.0, "costo": 650_000},
    10: {"consecuencia": "Seguridad (evidente)", "tipo": "A condición",
         "tarea": "Medir tiempos de aplicación y liberación; cambiar la válvula de pedal o relé",
         "intervalo": "Cada 5.000 km", "recurso": "Técnico de frenos + válvula",
         "horas": 2.0, "costo": 1_100_000},
}

# Reglas de prioridad (AMFEC del grupo: S ≥ 9 se atiende con prioridad sin importar el NPR)
PRIORIDADES = {
    "P1": {"nombre": "P1 · Inmediata", "regla": "Modo con S ≥ 9 en alarma", "plazo": "No despachar el bus; corregir antes de la próxima salida", "dias": 0},
    "P2": {"nombre": "P2 · Urgente", "regla": "Modo con S ≥ 9 en alerta, o S < 9 en alarma", "plazo": "Dentro del tiempo de reacción (≤ 3 días / 800 km) o antes de llegar a la alarma", "dias": 3},
    "P3": {"nombre": "P3 · Programada", "regla": "Modo con S < 9 en alerta", "plazo": "En la próxima revisión de taller (≤ 5.000 km ≈ 19 días)", "dias": 19},
}

# Costos de una falla en ruta (correctivo de emergencia): supuestos
CORRECTIVO_EN_RUTA = {"horas_extra": 6.0, "costo_extra": 900_000}  # grúa + atención en vía

# ------------------------------------------------------------------
# METAS DEL PROCESO
# ------------------------------------------------------------------
METAS = {
    "disponibilidad": {"valor": 92.0, "unidad": "%", "fuente": "Documento Altos de la Sabana y AMFEC: disponibilidad no inferior al 92 %", "origen": "Documento del grupo"},
    "mtbf_km": {"valor": 40_000, "unidad": "km", "fuente": "Supuesto: no más de una falla en ruta del sistema de frenos cada 5 meses por bus", "origen": "Supuesto"},
    "mttr_h": {"valor": 4.0, "unidad": "h", "fuente": "Supuesto: la mayoría de tareas de frenos se resuelve en un turno de taller", "origen": "Supuesto"},
    "costo_anual_bus": {"valor": 6_400_000, "unidad": "COP/bus/año", "fuente": "Supuesto: 12 % del rubro anual de mantenimiento y llantas ($53 millones, documento Altos de la Sabana)", "origen": "Supuesto"},
}

# ------------------------------------------------------------------
# SUPUESTOS (se muestran en la pestaña Datos y supuestos)
# ------------------------------------------------------------------
SUPUESTOS = [
    ("Datos de condición de los 5 buses", "Simulado", "No hay acceso a una flota real; el simulador genera datos con ruido e inyecta fallas progresivas. Se declaran como simulados."),
    ("Recorrido 263 km/día y 96.000 km/año", "Medido (documento del grupo)", "Curva P-F y AMFEC del grupo."),
    ("Desgaste de forros 0,30 mm cada 1.000 km", "Supuesto", "Curva P-F del grupo; usado como ritmo base del simulador."),
    ("Tiempo de reacción 800 km (3 días)", "Supuesto", "Curva P-F del grupo: tiempo para programar y ejecutar la corrección."),
    ("Nivel de vigilancia en cada variable", "Supuesto", "Se agrega un cuarto nivel (la rúbrica pide cuatro) en la mitad del camino entre condición nominal y alerta."),
    ("Alarma de forros en 7 mm", "Supuesto", "Deja 0,6 mm sobre el mínimo legal de 6,4 mm ≈ 2.000 km de margen, más que el tiempo de reacción."),
    ("Alerta de fuga en 0,10 bar/min y de recarga en 35 s", "Supuesto", "La curva P-F original ponía P en el límite legal; se adelanta para dejar margen de planeación."),
    ("Umbrales de agua en la purga (5 / 10 / 30 ml)", "Supuesto", "Bendix solo da un criterio cualitativo (humedad excesiva o aceite)."),
    ("Alarma de ΔT en 56 °C", "Supuesto", "Doble del criterio de investigación de la literatura (28 °C)."),
    ("Pesos del índice de salud = NPR / suma de NPR", "Inferido", "Calculado del AMFEC del grupo."),
    ("Costos y duración de cada tarea", "Supuesto", "Estimaciones de mercado en pesos de 2026; deben reemplazarse por cotizaciones."),
    ("Costo adicional de una falla en ruta: 6 h y $900.000", "Supuesto", "Grúa y atención en vía."),
    ("Metas de MTBF, MTTR y costo anual", "Supuesto", "Ver pestaña Indicadores; solo la meta de disponibilidad viene de los documentos del grupo."),
    ("Modelo de tendencia lineal o exponencial por variable", "Supuesto", "Se justifica por el mecanismo físico de cada modo; la plataforma muestra también el R² del otro modelo."),
]

LIMITACIONES = [
    "Los datos son simulados: los resultados muestran cómo funcionaría la plataforma, no el estado real de una flota.",
    "Las tendencias se calculan con pocos puntos por tramo; la proyección es indicativa y se recalcula con cada medición nueva.",
    "Una tendencia exponencial ajustada sobre pocos datos puede sobreestimar la velocidad de deterioro.",
    "Los modos 4, 5 y 6 no tienen una variable que cambie gradualmente; se controlan con pruebas pasa / no pasa, fuera del índice de salud.",
    "Los costos y tiempos de reparación son supuestos y afectan directamente MTTR, disponibilidad y costos.",
    "La alarma de ΔT y las cantidades de agua en la purga no tienen un valor normativo; deben validarse en campo.",
]

REFERENCIAS = [
    "SAE International. (2009). JA1011: Evaluation criteria for reliability-centered maintenance (RCM) processes.",
    "SAE International. (2011). JA1012: A guide to the reliability-centered maintenance (RCM) standard.",
    "Moubray, J. (1997). Reliability-centred maintenance (2.ª ed.). Industrial Press.",
    "U.S. Department of Defense. (1980). MIL-STD-1629A: Procedures for performing a FMECA.",
    "49 CFR § 393.47 — Brake actuators, slack adjusters, linings/pads and drums/rotors. https://www.law.cornell.edu/cfr/text/49/393.47",
    "Georgia Department of Driver Services. Commercial Driver's Manual, sección 5: Air brakes. https://dds.georgia.gov/node/34456",
    "Bendix Commercial Vehicle Systems. (2014). Manual de frenos de aire (Air Brake Handbook, edición en español).",
    "Bendix Tech Tips: Air dryer system inspection and upkeep. Fleet Maintenance. https://www.fleetmaintenance.com/in-the-bay/diagnostic-and-repair/article/55092097/",
    "Heavy Vehicle Inspection (HVI). (2026). Brake drag and hot wheel diagnosis. https://heavyvehicleinspection.com/blog/post/brake-drag-hot-wheel-diagnosis-truck",
    "ICONTEC. (2012). NTC 5375: Revisión técnico-mecánica y de emisiones contaminantes.",
    "Mahecha, J. A., Lozano, P. y Gonzales, L. A. (2026). AMFEC y curva P-F del sistema de frenos de aire, Altos de la Sabana S.A.S.",
]
