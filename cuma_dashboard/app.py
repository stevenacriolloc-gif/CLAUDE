"""Tablero de indicadores de CUMA (Flask).

Parte de la última instantánea publicada (datos_publicados/indicadores.json, solo cifras agregadas).
Si hay Excel en DATA_DIR, recalcula sobre ella las series que salen directamente de esos archivos.

Variables de entorno opcionales:
  DATA_DIR             carpeta con los Excel (por defecto ./datos)
  DASHBOARD_PASSWORD   si se define, el tablero pide usuario «cuma» y esta contraseña
  ADMIN_TOKEN          si se define, habilita /actualizar para subir Excel nuevos desde el navegador
  NOMBRE               si se define, reemplaza el nombre «CUMA» en los textos del tablero (p. ej. «[NOMBRE]» para anonimizar)
"""
import hmac
import json
import os
import threading

from flask import Flask, Response, abort, jsonify, request

from cuma import calculo

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE, "datos"))
SNAPSHOT = os.path.join(BASE, "datos_publicados", "indicadores.json")
PLANTILLA = os.path.join(BASE, "templates", "index.html")
INICIO, FIN = '<script type="application/json" id="cuma-data">', "</script>"
# Lo que se recalcula desde los Excel; el resto (inventario, horas, supuestos del informe) viene de la instantánea.
RECALCULADAS = ("actualizado", "meses", "mensual", "pareto")
# Fuentes que solo vienen de la instantánea (no hay Excel para ellas): se conservan al recalcular.
FUENTES_FIJAS = ("Conteos de inventario", "Ventas por hora", "Productos agroecológicos")

app = Flask(__name__)
_lock = threading.Lock()
_estado = {"datos": None, "firma": None, "origen": None}


def _firma():
    f = calculo.archivos(DATA_DIR)
    rutas = [r for r in [f["datos"], f["apuntes"], *f["transferencias"]] if r]
    return tuple((r, os.path.getmtime(r)) for r in rutas) if f["datos"] and f["apuntes"] else None


def datos():
    """Indicadores vigentes: se recalculan solo si cambiaron los Excel."""
    firma = _firma()
    with _lock:
        if _estado["datos"] is None or firma != _estado["firma"]:
            with open(SNAPSHOT, encoding="utf-8") as fh:
                base = json.load(fh)
            if firma:
                nuevo = calculo.construir(DATA_DIR)
                base.update({k: nuevo[k] for k in RECALCULADAS})
                base["fuentes"] = nuevo["fuentes"] + [x for x in base.get("fuentes", []) if x["fuente"] in FUENTES_FIJAS]
            _estado.update(datos=base, firma=firma, origen="excel" if firma else "instantanea")
        return _estado["datos"]


@app.before_request
def _clave():
    clave = os.environ.get("DASHBOARD_PASSWORD")
    if not clave or request.path == "/salud" or request.path.startswith("/static/") or request.path.startswith("/apple-touch-icon"):
        return None
    auth = request.authorization
    if auth and hmac.compare_digest(auth.password or "", clave):
        return None
    return Response("Acceso restringido", 401, {"WWW-Authenticate": 'Basic realm="CUMA"'})


@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
def icono_ios():
    """Ícono de la pantalla de inicio del iPhone (Safari lo busca también en la raíz)."""
    return app.send_static_file("apple-touch-icon.png")


@app.get("/")
def tablero():
    with open(PLANTILLA, encoding="utf-8") as fh:
        html = fh.read()
    i = html.index(INICIO) + len(INICIO)
    j = html.index(FIN, i)
    carga = json.dumps(datos(), ensure_ascii=False).replace("</", "<\\/")
    html = html[:i] + "\n" + carga + "\n" + html[j:]
    nombre = os.environ.get("NOMBRE")
    if nombre:   # solo el texto visible: los identificadores internos van en minúsculas («cuma-data») y no cambian
        html = html.replace("CUMA", nombre)
    return Response(html, mimetype="text/html")


@app.get("/api/indicadores")
def api():
    return jsonify(datos())


@app.get("/salud")
def salud():
    return {"ok": True, "origen": _estado["origen"]}


FORM = """<!doctype html><meta charset=utf-8><title>Actualizar datos · CUMA</title>
<body style="font:14px system-ui;max-width:560px;margin:48px auto;padding:0 16px">
<h2>Actualizar los Excel de CUMA</h2>
<p>Sube el archivo de ventas (Datos_Cuma…xlsx), los apuntes contables (Apuntes_Cuma…xlsx) y los de transferencias (transferencias_CUMA_AAAA_MM.xlsx).</p>
<form method=post enctype=multipart/form-data>
<p><input type=password name=token placeholder="Clave de administración" required></p>
<p><input type=file name=archivos multiple accept=".xlsx" required></p>
<button>Subir y recalcular</button></form>"""


@app.route("/actualizar", methods=["GET", "POST"])
def actualizar():
    token = os.environ.get("ADMIN_TOKEN")
    if not token:
        abort(404)
    if request.method == "GET":
        return FORM
    if not hmac.compare_digest(request.form.get("token", ""), token):
        abort(403)
    os.makedirs(DATA_DIR, exist_ok=True)
    for f in request.files.getlist("archivos"):
        nombre = os.path.basename(f.filename or "")
        if nombre.lower().endswith(".xlsx"):
            f.save(os.path.join(DATA_DIR, nombre))
    d = datos()
    return f"<p style='font:14px system-ui'>Listo: datos al {d['actualizado']} ({_estado['origen']}). <a href='/'>Volver al tablero</a></p>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
