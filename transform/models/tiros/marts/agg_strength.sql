-- ¿Con qué fuerza rinde mejor el jugador? Excluye quiebres, que siempre son fuertes
select
    strength,
    count(*) as n_shots,
    avg(is_successful::int) as success_rate,
    avg(scratch::int) as scratch_rate,
    avg(cue_travel_m) as avg_cue_travel_m
from {{ ref('fct_shots') }}
where not is_break
group by strength
