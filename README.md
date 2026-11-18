# pool-match-lab

Pipeline de datos que simula millones de quiebres de pool (bola 9) con física
realista para responder una pregunta simple: **¿cuál es el mejor quiebre?**

> 🚧 Proyecto en construcción. Hoy están listas la generación de datos, el modelado y la orquestación.

## Preguntas

- ¿Qué combinación de velocidad, ángulo y efecto maximiza las bolas embocadas
  sin meter la blanca?
- ¿Qué tan tolerante al error es cada quiebre? Si fallas el ángulo por 1°, ¿qué pasa?
- ¿Con qué frecuencia entra la 9 en el quiebre, y bajo qué condiciones?

## Arquitectura

```
experiments.yml  →  una partición por experimento
   │
   ▼
pooltool (simulación física)
   │  barrido de parámetros en paralelo, semillas fijas
   ▼
data/raw/experiment=<nombre>/part-*.parquet   + manifest.json
   │
   ▼
DuckDB + dbt (tests de calidad en cada capa)
   │  stg_breaks → fct_breaks → agg_break_grid
   ▼
data/warehouse.duckdb
   │
   ▼
Dashboard con los hallazgos                              [próximo]
```

| Modelo | Qué contiene |
|---|---|
| `stg_breaks` | Un quiebre por fila, con columnas normalizadas |
| `fct_breaks` | Resultado según las reglas de bola 9 (falta, gana con la 9, sigue jugando, no emboca) y su celda en la grilla de parámetros |
| `agg_break_grid` | Tasas de éxito, falta y bola 9 por combinación de velocidad × ángulo |

Todo corre orquestado en **Dagster**: la simulación es un asset particionado por
experimento, los modelos dbt se recalculan solos cuando llega un experimento
nuevo y sus tests aparecen como checks de calidad.

Las decisiones de diseño están en [`docs/decisions/`](docs/decisions/).

## Cómo correrlo

Requiere Python 3.12.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
make install

make simulate EXPERIMENT=piloto N=2000   # genera los quiebres
make transform                          # dbt build: modelos + tests de calidad
make check                              # lint + tests de Python + dbt build

make orchestrate                        # interfaz de Dagster en http://localhost:3000
```

Para agregar un experimento, se suma una entrada en `experiments.yml` y se
materializa su partición desde Dagster.

La simulación es **reanudable**: si se interrumpe, al volver a correrla solo
genera los bloques que faltan. Cada experimento guarda su semilla y la versión
de pooltool en `manifest.json`, y no se puede reanudar con una configuración
distinta, así que no se mezclan datos de corridas diferentes.

## Hoja de ruta

- [x] Simulación reproducible de un quiebre
- [x] Generación en paralelo, por bloques y reanudable
- [x] Modelado con dbt sobre DuckDB y tests de calidad
- [x] Orquestación con Dagster (experimentos y backfills)
- [ ] Validación contra estadísticas de quiebres reales
- [ ] Dashboard con mapas de calor y tolerancia al error
