"""Tablero de indicadores de CUMA (Flask).

Al arrancar busca los Excel en DATA_DIR y recalcula los indicadores; si no hay Excel, usa la
última instantánea publicada (datos_publicados/indicadores.json), que solo tiene cifras agregadas.

Variables de entorno opcionales:
  DATA_DIR             carpeta con los Excel (por defecto ./datos)
  DASHBOARD_PASSWORD   si se define, el tablero pide usuario «cuma» y esta contraseña
  ADMIN_TOKEN          si se define, habilita /actualizar para subir Excel nuevos desde el navegador
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
            if firma:
                _estado.update(datos=calculo.construir(DATA_DIR), firma=firma, origen="excel")
            elif _estado["datos"] is None:
                with open(SNAPSHOT, encoding="utf-8") as fh:
                    _estado.update(datos=json.load(fh), firma=None, origen="instantanea")
        return _estado["datos"]


@app.before_request
def _clave():
    clave = os.environ.get("DASHBOARD_PASSWORD")
    if not clave or request.path == "/salud":
        return None
    auth = request.authorization
    if auth and hmac.compare_digest(auth.password or "", clave):
        return None
    return Response("Acceso restringido", 401, {"WWW-Authenticate": 'Basic realm="CUMA"'})


@app.get("/")
def tablero():
    with open(PLANTILLA, encoding="utf-8") as fh:
        html = fh.read()
    i = html.index(INICIO) + len(INICIO)
    j = html.index(FIN, i)
    carga = json.dumps(datos(), ensure_ascii=False).replace("</", "<\\/")
    return Response(html[:i] + "\n" + carga + "\n" + html[j:], mimetype="text/html")


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
