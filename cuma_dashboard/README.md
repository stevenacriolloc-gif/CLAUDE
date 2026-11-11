# Tablero de indicadores · CUMA

Flask + Pandas. Lee los Excel de CUMA, calcula los indicadores y los inyecta en `templates/index.html`.

```bash
pip install -r requirements.txt
mkdir datos   # copia aquí Datos_Cuma…xlsx, Apuntes_Cuma…xlsx y transferencias_CUMA_AAAA_MM.xlsx
python app.py # http://localhost:8000
```

- La base es la instantánea agregada `datos_publicados/indicadores.json` (inventario, horas y supuestos del informe incluidos).
- Con Excel en `datos/`, se recalculan sobre ella las ventas, costos, gastos, compras, transferencias, transacciones y el Pareto.
- `python -m cuma.calculo datos` imprime todo lo que se calcula desde los Excel.
- Los Excel nunca se suben al repositorio (`.gitignore`): contienen datos de clientes.
- En Render (`render.yaml` en la raíz): `DASHBOARD_PASSWORD` protege el tablero (usuario `cuma`) y `ADMIN_TOKEN` habilita `/actualizar` para subir Excel desde el navegador (el disco del plan gratuito se borra al reiniciar; la instantánea queda como respaldo).
