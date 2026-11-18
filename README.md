# pool-break-lab

Pipeline de datos que simula millones de quiebres de pool (bola 9) con física
realista para responder una pregunta simple: **¿cuál es el mejor quiebre?**

> 🚧 Proyecto en construcción. Hoy está lista la capa de generación de datos.

## Preguntas

- ¿Qué combinación de velocidad, ángulo y efecto maximiza las bolas embocadas
  sin meter la blanca?
- ¿Qué tan tolerante al error es cada quiebre? Si fallas el ángulo por 1°, ¿qué pasa?
- ¿Con qué frecuencia entra la 9 en el quiebre, y bajo qué condiciones?

## Arquitectura

```
pooltool (simulación física)
   │  barrido de parámetros en paralelo, semillas fijas
   ▼
data/raw/experiment=<nombre>/part-*.parquet   + manifest.json
   │
   ▼
DuckDB + dbt (staging → marts, tests de calidad)        [próximo]
   │
   ▼
Orquestación con Dagster                                 [próximo]
   │
   ▼
Dashboard con los hallazgos                              [próximo]
```

Las decisiones de diseño están en [`docs/decisions/`](docs/decisions/).

## Cómo correrlo

Requiere Python 3.12.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 1.000 quiebres en bloques de 500, con 4 procesos
pool-break --experiment piloto --n 1000 --workers 4

pytest
```

El comando es **reanudable**: si se interrumpe, al volver a correrlo solo
genera los bloques que faltan. Cada experimento guarda su semilla y la versión
de pooltool en `manifest.json`, así que cualquier resultado se puede reproducir.

## Hoja de ruta

- [x] Simulación reproducible de un quiebre
- [x] Generación en paralelo, por bloques y reanudable
- [ ] Modelado con dbt sobre DuckDB y tests de calidad
- [ ] Orquestación con Dagster (experimentos y backfills)
- [ ] Validación contra estadísticas de quiebres reales
- [ ] Dashboard con mapas de calor y tolerancia al error
