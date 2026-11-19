-- Resultado promedio por combinación de velocidad y ángulo: base para el mapa de calor
select
    experiment,
    v0_bin,
    cut_bin,
    count(*) as n_breaks,
    avg(n_pocketed) as avg_pocketed,
    avg(scratch::int) as scratch_rate,
    avg(nine_on_break::int) as nine_on_break_rate,
    avg(is_successful::int) as success_rate
from {{ ref('fct_breaks') }}
group by all
