-- Un tiro por fila, con su resultado y la fuerza con que se jugó
select
    *,
    case
        when is_break then 'quiebre'
        when scratch then 'falta'
        when n_pocketed > 0 then 'emboca'
        else 'falla'
    end as outcome,
    not is_break and not scratch and n_pocketed > 0 as is_successful,
    case
        when cue_speed_ms < {{ var('soft_max_speed') }} then 'suave'
        when cue_speed_ms < {{ var('medium_max_speed') }} then 'media'
        else 'fuerte'
    end as strength
from {{ ref('stg_shots') }}
