select
    video || '-' || shot as shot_id,
    video as session,
    shot as shot_number,
    is_break,
    start_s,
    duration_s,
    n_pocketed,
    scratch,
    cue_speed_ms,
    cue_travel_m,
    cue_start_x,
    cue_start_y,
    cue_end_x,
    cue_end_y,
    balls_left
from {{ source('shots', 'raw_shots') }}
