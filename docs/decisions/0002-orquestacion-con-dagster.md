# 0002 · Orquestar con Dagster, particionando por experimento

**Estado:** aceptada

## Contexto

El pipeline tiene dos pasos con ritmos distintos: simular un experimento puede
tomar minutos u horas, mientras que recalcular los modelos dbt toma segundos.
Se necesita poder correr experimentos sueltos, rehacer uno si falla y que los
modelos se actualicen sin intervención.

## Decisión

Usar Dagster con un enfoque de assets:

- `raw/breaks` es un asset **particionado por experimento**. Las particiones se
  leen de `experiments.yml`, así que agregar un experimento es editar un archivo,
  no código.
- Los modelos dbt se cargan con `dagster-dbt`. Sus tests quedan como asset
  checks y los modelos usan `AutomationCondition.eager()`: se recalculan cuando
  se materializa un experimento nuevo.

Se eligió Dagster sobre Airflow porque el proyecto gira en torno a *datos*
(experimentos, tablas) más que a *tareas*, y Dagster modela eso directamente,
con linaje entre la simulación y cada modelo dbt.

## Consecuencias

- Un backfill es seleccionar varias particiones en la interfaz.
- Como la simulación ya es reanudable por bloques, rematerializar una partición
  interrumpida solo genera los bloques que faltan.
- dbt exige `protobuf<7` y Dagster instala la 7 por defecto, así que el límite
  queda fijado en `pyproject.toml`.
