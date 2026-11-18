# 0001 · Generar los datos con simulación física

**Estado:** aceptada

## Contexto

No existe un dataset público y estructurado de quiebres de pool con sus
condiciones (velocidad, ángulo, efecto). Las fuentes disponibles son resultados
de partidos, sin el detalle de cada tiro.

## Decisión

Generar los datos con [pooltool](https://github.com/ekiefl/pooltool), un motor
de física de billar en Python, barriendo parámetros del quiebre.

## Consecuencias

- Se controla la fuente: volumen ilimitado y sin depender de scraping.
- Cada quiebre debe ser reproducible. pooltool no acepta una semilla propia,
  así que se fijan las de `random` y `numpy`, y cada experimento guarda su
  semilla base y la versión de pooltool en `manifest.json`.
- Los resultados valen tanto como el modelo físico. Hay que contrastarlos con
  datos reales conocidos antes de sacar conclusiones sobre mesas reales.
- Con ~36 ms por quiebre (medido en un Mac de 8 núcleos), un millón de quiebres
  toma alrededor de una hora en paralelo local. No se justifica un clúster.
