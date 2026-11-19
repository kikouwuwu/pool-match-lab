-- Resumen por sesión: cómo rindió el jugador en cada video
select
    session,
    count(*) as n_shots,
    count(*) filter (where not is_break) as n_regular_shots,
    sum(n_pocketed) as balls_pocketed,
    avg(is_successful::int) filter (where not is_break) as success_rate,
    avg(scratch::int) as scratch_rate,
    max(n_pocketed) filter (where is_break) as pocketed_on_break,
    avg(cue_speed_ms) filter (where not is_break) as avg_speed_ms,
    min(balls_left) as balls_left_at_end
from {{ ref('fct_shots') }}
group by session
