"""Supuestos y textos del sistema de indicadores que no salen de los Excel (informe de diagnóstico)."""

# Hasta marzo de 2026 las transferencias no tenían costo propio: los indicadores de margen se calculan desde aquí.
INICIO_COSTO_REAL = "2026-03"

NOMBRE_ACOPIO = "Centro de acopio EDEC"
PROVEEDORES_TOP = 6

# I18: cota superior mientras no se clasifiquen los proveedores (el acopio se trata como fuente propia).
DESINTERMEDIACION_MAX = 30.1

# Agrupación de la cuenta 6 para la estructura de gastos (I4), en orden de prioridad.
RUBROS_GASTO = [
    ("Personal", lambda c: c.startswith("6.1.1")),
    ("Energía", lambda c: "ENERGIA" in c.upper()),
    ("Servicios ocasionales", lambda c: "OCACIONALES" in c.upper() or "OCASIONALES" in c.upper()),
    ("Comisiones de tarjeta", lambda c: "COMISION" in c.upper()),
    ("Mantenimiento", lambda c: "MANT" in c.upper()),
]

COBERTURA = {"completos": 10, "parciales": 5, "sin_datos": 8, "tablero_pct": 80}

FALTAN = [
    ["Bajas y mermas con su motivo", "I15", "a", "Administración de CUMA"],
    ["Inventario mensual por producto", "I13, I14, I15", "a", "Administración de CUMA"],
    ["Confirmar desde qué mes el costo de transferencias es real", "I1, I6, I7", "a", "Administrador del sistema"],
    ["Registro de reempaques o tabla de códigos a granel y empacados", "I1, I15, I18", "m", "Administración de CUMA"],
    ["Transferencias de diciembre de 2025", "I1, I18, I20", "m", "Administrador del sistema"],
    ["Confirmar nómina pagada desde EDEC EP y número de empleados", "I2, I6, I7, I17", "m", "Administrador del sistema"],
    ["Categorías corregidas en el catálogo", "I8, I12, I15", "m", "Administrador del sistema"],
    ["Marca de canasta básica o precio regulado", "I8", "m", "Administración de CUMA"],
    ["Días sin existencia por producto", "I16", "b", "Administración de CUMA"],
    ["Hora de cada venta", "I11, I17", "b", "Administrador del sistema"],
    ["Parroquia de origen de proveedores directos", "I21", "b", "Administración de CUMA"],
    ["Fechas de pago a proveedores", "I19", "b", "Tesorería de EDEC EP"],
    ["Precios mayoristas y de una canasta de referencia", "I22, I23", "b", "Levantamiento propio"],
]
