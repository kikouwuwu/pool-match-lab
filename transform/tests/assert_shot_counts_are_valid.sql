-- Una mesa de bola 9 nunca tiene más de 9 bolas de color
select shot_id, n_pocketed, balls_left
from {{ ref('stg_shots') }}
where n_pocketed not between 0 and 9
   or balls_left not between 0 and 9
