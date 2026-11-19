select
    experiment || '-' || seed as break_id,
    experiment,
    seed,
    v0,
    cut,
    a as spin_side,
    b as spin_top,
    pocketed,
    n_pocketed,
    scratch,
    nine_on_break,
    n_events,
    sim_time_s
from {{ source('raw', 'breaks') }}
