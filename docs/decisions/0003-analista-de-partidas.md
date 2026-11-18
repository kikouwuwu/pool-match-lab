# 0003 · Cambiar el foco a analizar partidas grabadas

**Estado:** aceptada

## Contexto

El proyecto partió como un laboratorio de quiebres simulados. El objetivo
cambió: analizar partidas reales grabadas en video y obtener estadísticas de
cada tiro.

## Decisión

- La fuente principal pasa a ser **video**, procesado con OpenCV, sin modelos
  entrenados por ahora: con cámara fija, distinguir bolas del paño por color
  es suficiente para una primera versión.
- La simulación ya construida se reutiliza para **generar partidas sintéticas
  con respuesta conocida** y validar el analizador sin depender de grabaciones.
- La infraestructura existente (dbt, DuckDB, Dagster, Makefile) se mantiene y
  se extenderá a los tiros.
- El repositorio se renombró de `pool-break-lab` a `pool-match-lab`.

## Consecuencias

- La calidad del análisis depende de la grabación: cámara fija y mirando la
  mesa desde arriba o en ángulo, con las 4 esquinas del paño visibles.
- Las métricas de validación con datos sintéticos son un techo, no lo que se
  logrará con video real: falta ruido como el jugador tapando la mesa.
- Identificar el número de cada bola queda fuera de la primera versión.
