# pool-match-lab

Analista de partidas de pool: a partir del **video de una partida** detecta cada
tiro y genera estadísticas (bolas embocadas, faltas, velocidad y recorrido de la
blanca) para entender cómo juegas y cómo evolucionas.

> 🚧 Proyecto en construcción. Hoy funciona el análisis tiro a tiro, validado
> con partidas simuladas. Falta probarlo con grabaciones reales.

## Cómo funciona

```
data/videos/<sesión>.mp4 + <sesión>.json (esquinas del paño)
   │  sensor de Dagster: cada video nuevo es una partición
   ▼
Detección por cuadro (OpenCV)
   │  calibración: 4 esquinas → vista cenital en metros
   │  bolas = lo que no es paño · blanca = mancha clara del tamaño de una bola
   ▼
Segmentación en tiros
   │  un tiro = tramo con bolas en movimiento entre dos momentos de reposo
   ▼
data/shots/<sesión>.parquet (una fila por tiro)
   │
   ▼
DuckDB + dbt: stg_shots → fct_shots → agg_sessions, agg_strength
   │
   ▼
Dashboard (Streamlit)
```

Al dejar un video calibrado en `data/videos/`, Dagster lo analiza y recalcula
los modelos sin intervención. Los tests de dbt quedan como checks de calidad.

| Modelo | Qué contiene |
|---|---|
| `fct_shots` | Cada tiro con su resultado (quiebre, falta, emboca, falla) y su fuerza (suave, media, fuerte) |
| `agg_sessions` | Por sesión: tiros, bolas embocadas, % de acierto, % de faltas, resultado del quiebre |
| `agg_strength` | % de acierto y de faltas según la fuerza del tiro: ¿con qué fuerza juegas mejor? |

Cada tiro registra:

| Campo | Qué es |
|---|---|
| `is_break` | Si el tiro partió desde un rack armado |
| `n_pocketed` | Bolas de color embocadas (mesa antes vs. después del tiro) |
| `scratch` | Si la blanca terminó embocada |
| `cue_speed_ms` | Velocidad inicial de la blanca (m/s) |
| `cue_travel_m` | Distancia que recorrió la blanca |
| `cue_start_*`, `cue_end_*` | Dónde estaba y dónde quedó la blanca: base para analizar el control de posición |

## Validación con partidas simuladas

Antes de grabar partidas reales, el analizador se prueba con **partidas
simuladas**: se juegan con un motor de física de billar
([pooltool](https://github.com/ekiefl/pooltool)) y se dibujan como video con
ruido y compresión, así que se sabe exactamente qué pasó en cada tiro.

En 6 partidas de 8 tiros (48 tiros):

| Métrica | Resultado |
|---|---|
| Tiros detectados correctamente | 48 / 48 |
| Bolas embocadas correctas | 46 / 48 (96%) |
| Faltas correctas | 47 / 48 (98%) |

**Limitaciones conocidas:**

- El video simulado es más limpio que uno real: no hay jugador ni taco
  tapando la mesa, ni reflejos o sombras.
- Una bola de color parecido al paño (la 6, verde) o detenida junto a una
  tronera a veces no se cuenta.
- En el rack las bolas se tocan y no se pueden contar una a una, así que un
  quiebre asume las 9 bolas de la bola 9.
- Todavía no identifica el número de cada bola.

Las decisiones de diseño están en [`docs/decisions/`](docs/decisions/).

## Cómo correrlo

Requiere Python 3.12.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
make install

make demo SEED=2     # simula una partida, genera el video y lo analiza
make transform       # modelos dbt de tiros + tests de calidad
make check           # lint + tests + demo + dbt build

make orchestrate     # Dagster en http://localhost:3000, con el sensor de videos activo
make dashboard       # dashboard en http://localhost:8501
```

El dashboard muestra, para las sesiones elegidas: tiros, % de acierto, % de
faltas y bolas embocadas; la evolución del acierto y las faltas sesión a sesión;
el acierto según la fuerza del tiro (con el n° de tiros detrás de cada barra) y
un mapa de la mesa con dónde quedó la blanca después de cada tiro.

Para un video propio, se miden una vez las esquinas del paño en píxeles
(superior izquierda, superior derecha, inferior derecha, inferior izquierda):

```bash
pool-analyze mi_partida.mp4 --corners "120,80;1800,85;1795,940;118,935"
```

También se pueden guardar en `mi_partida.json` (`{"corners": "..."}`) junto al
video, para no repetirlas.

## Laboratorio de quiebres

El proyecto partió simulando quiebres masivamente, y esa parte sigue disponible:
una simulación reanudable y particionada por experimento (`experiments.yml`),
modelada con dbt sobre DuckDB (`make simulate` y `make transform-breaks`) y
orquestada con Dagster.
Más adelante servirá para comparar un tiro real con lo que predice la física.

## Hoja de ruta

- [x] Detección de bolas y blanca, con corrección de perspectiva
- [x] Segmentación en tiros, bolas embocadas y faltas
- [x] Validación contra partidas simuladas
- [ ] Probar con grabaciones reales y ajustar la detección
- [x] Modelos dbt y orquestación para los tiros
- [ ] Ignorar los cuadros donde el jugador tapa la mesa
- [ ] Identificar el número de cada bola
- [x] Dashboard por sesión y evolución en el tiempo
