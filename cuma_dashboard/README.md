# Tablero de indicadores · ProDesarrollo

Flask + Pandas. Lee los Excel de la tienda, calcula los indicadores y los inyecta en `templates/index.html`.

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

- La instantánea `datos_publicados/indicadores.json` sale de la base corregida del trabajo de titulación: cifras mensuales, umbrales del semáforo tomados de los cuartiles de nueve supermercados del sector (Superintendencia de Compañías, 2025), proveedores, productos, rotación, merma y granel.
- El botón de base de datos de la barra superior abre el análisis en seis grupos: resultados, ventas y clientes, inventario, abastecimiento, sector y datos. Cada tarjeta muestra cifras clave, las figuras 1 a 19 del informe dibujadas en el tablero (se amplían con el botón de la esquina) y tablas que se ordenan por columna, se buscan, se filtran, muestran todas las filas y se descargan en CSV.
- `static/fig/mapa.png` es la Figura 2 (mapa de conexiones de la base corregida).
