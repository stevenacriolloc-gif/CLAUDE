"""Lee los Excel de CUMA y arma los datos que consume el tablero.

Fuentes (en la carpeta de datos):
  *Datos_Cuma*.xlsx           hojas Ventas, Compras y Productos (POS)
  *Apuntes_Cuma*.xlsx         apuntes contables de las cuentas 4, 5 y 6
  transferencias_CUMA_AAAA_MM.xlsx   envíos del centro de acopio (hoja «Resumen por producto»)

El resultado solo contiene cifras agregadas: ningún dato de clientes sale de aquí.
"""
import glob
import json
import os
import re
import sys

import pandas as pd

from .config import (COBERTURA, DESINTERMEDIACION_MAX, FALTAN, INICIO_COSTO_REAL,
                     NOMBRE_ACOPIO, PROVEEDORES_TOP, RUBROS_GASTO)


def _buscar(carpeta, patron):
    archivos = sorted(glob.glob(os.path.join(carpeta, patron)))
    return archivos[-1] if archivos else None


def _cod(serie):
    return serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def _mes(fechas):
    return pd.to_datetime(fechas).dt.strftime("%Y-%m")


def archivos(carpeta):
    return {
        "datos": _buscar(carpeta, "*Datos_Cuma*.xlsx"),
        "apuntes": _buscar(carpeta, "*Apuntes_Cuma*.xlsx"),
        "transferencias": sorted(glob.glob(os.path.join(carpeta, "*transferencias_CUMA_*.xlsx"))),
    }


def _apuntes(ruta):
    a = pd.read_excel(ruta, sheet_name=0)
    a["mes"] = _mes(a["Fecha"])
    a["cod"] = a["Cuenta"].astype(str).str.split(" ").str[0]
    a["Debe"] = pd.to_numeric(a["Debe"], errors="coerce").fillna(0)
    a["Haber"] = pd.to_numeric(a["Haber"], errors="coerce").fillna(0)
    return a


def _transferencias(rutas):
    """Neto en USD por mes y por producto (ingresos menos devoluciones)."""
    por_mes, por_producto = {}, []
    for ruta in rutas:
        m = re.search(r"(\d{4})_(\d{2})", os.path.basename(ruta))
        if not m:
            continue
        mes = f"{m.group(1)}-{m.group(2)}"
        r = pd.read_excel(ruta, sheet_name="Resumen por producto")
        por_mes[mes] = float(pd.to_numeric(r["Neto ($)"], errors="coerce").fillna(0).sum())
        r = r.assign(mes=mes, cod=_cod(r["Código"]))
        por_producto.append(r[["mes", "cod", "Ingresos (cant.)", "Neto ($)"]])
    prod = pd.concat(por_producto) if por_producto else pd.DataFrame(columns=["mes", "cod", "Ingresos (cant.)", "Neto ($)"])
    return por_mes, prod


def _rubro(cuenta):
    for nombre, regla in RUBROS_GASTO:
        if regla(cuenta):
            return nombre
    return "Otros"


def construir(carpeta):
    f = archivos(carpeta)
    if not f["datos"] or not f["apuntes"]:
        raise FileNotFoundError("Faltan los Excel de ventas (Datos_Cuma) o de apuntes contables en " + carpeta)

    ventas = pd.read_excel(f["datos"], sheet_name="Ventas")
    compras = pd.read_excel(f["datos"], sheet_name="Compras")
    ventas["mes"] = _mes(ventas["Fecha de la factura"])
    compras["mes"] = _mes(compras["Fecha de la factura"])
    ventas["cod"] = _cod(ventas["Referencia Interna"])
    compras["cod"] = _cod(compras["Referencia Interna"])
    ap = _apuntes(f["apuntes"])
    transf_mes, transf_prod = _transferencias(f["transferencias"])

    meses = sorted(ventas["mes"].unique())
    haber_menos_debe = lambda d: float((d["Haber"] - d["Debe"]).sum())
    debe_menos_haber = lambda d: float((d["Debe"] - d["Haber"]).sum())

    def por_mes(df, fn):
        g = {m: fn(d) for m, d in df.groupby("mes")}
        return [round(g.get(m, 0.0), 2) for m in meses]

    gastos6 = ap[ap["cod"].str.startswith("6")]
    pos = ventas.groupby("mes").agg(importe=("Importe", "sum"), n=("Documento SRI", "nunique"))
    mensual = {
        "ventas": por_mes(ap[ap["cod"].str.startswith("4.1.1")], haber_menos_debe),
        "costo_ventas": por_mes(ap[ap["cod"].str.startswith("5.3.1")], debe_menos_haber),
        "gastos": por_mes(gastos6, debe_menos_haber),
        "comisiones": por_mes(gastos6[gastos6["Cuenta"].str.contains("COMISION TARJETA", case=False)], debe_menos_haber),
        "ventas_pos": [round(float(pos["importe"].get(m, 0)), 2) for m in meses],
        "transacciones": [int(pos["n"].get(m, 0)) for m in meses],
        "compras": [round(float(compras.loc[compras["mes"] == m, "Importe"].sum()), 2) for m in meses],
        "transferencias": [round(transf_mes[m], 2) if m in transf_mes else None for m in meses],
    }

    # I4 · estructura del gasto operativo (todo el periodo contable)
    g = gastos6.assign(rubro=gastos6["Cuenta"].map(_rubro)).groupby("rubro").apply(debe_menos_haber, include_groups=False)
    g = g[g > 0].sort_values(ascending=False)
    estructura = [{"rubro": k, "pct": round(v / g.sum() * 100, 1)} for k, v in g.items()]

    # Origen de la mercadería vendida: cruce de cada producto vendido con sus entradas
    con_compra = set(compras["cod"])
    con_transf = set(transf_prod["cod"])   # todo producto que aparece en los movimientos con el acopio
    vprod = ventas.groupby("cod")["Importe"].sum()
    def origen(c):
        a, b = c in con_compra, c in con_transf
        return "Compras directas y transferencias" if a and b else "Solo compras directas" if a else "Solo transferencias del acopio" if b else "Sin entrada registrada"
    o = vprod.groupby(vprod.index.map(origen)).sum()
    orden = ["Solo compras directas", "Compras directas y transferencias", "Solo transferencias del acopio", "Sin entrada registrada"]
    origen_l = [{"origen": k, "usd": round(float(o.get(k, 0))), "pct": round(float(o.get(k, 0)) / vprod.sum() * 100, 1)} for k in orden]

    # I12 · Pareto ABC
    p = vprod.sort_values(ascending=False)
    acum = p.cumsum() / p.sum()
    n = len(p)
    xs = [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    ys = [0.0] + [round(float(acum.iloc[max(0, int(n * x / 100) - 1)]) * 100, 1) for x in xs[1:]]
    abc = {"A": int((acum <= .8).sum()), "B": int(((acum > .8) & (acum <= .95)).sum()), "C": int((acum > .95).sum())}

    # I18 / I20 · proveedores y concentración (desde el inicio del costo real)
    desde = INICIO_COSTO_REAL
    pr = compras[compras["mes"] >= desde].groupby("Proveedor")["Importe"].sum()
    pr[NOMBRE_ACOPIO] = sum(v for m, v in transf_mes.items() if m >= desde)
    cuota = pr / pr.sum() * 100
    hhi = round(float((cuota ** 2).sum()))
    top = cuota.sort_values(ascending=False).head(PROVEEDORES_TOP)
    proveedores = [{"nombre": str(k).title() if k != NOMBRE_ACOPIO else k, "pct": round(float(v), 1)} for k, v in top.items()]

    return {
        "actualizado": str(pd.to_datetime(ventas["Fecha de la factura"]).max().date()),
        "meses": meses,
        "inicio_costo_real": desde,
        "mensual": mensual,
        "estructura_gastos": estructura,
        "origen": origen_l,
        "pareto": {"x": xs, "y": ys, "productos": n, "abc": abc},
        "proveedores": proveedores,
        "abastecimiento": {"hhi": hhi, "desintermediacion_max": DESINTERMEDIACION_MAX},
        "cobertura": COBERTURA,
        "faltan": FALTAN,
    }


if __name__ == "__main__":   # python -m cuma.calculo <carpeta_excel> [salida.json]
    datos = construir(sys.argv[1])
    texto = json.dumps(datos, ensure_ascii=False, indent=1)
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(texto)
    else:
        print(texto)
