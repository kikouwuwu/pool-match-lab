-- La cantidad de bolas embocadas debe coincidir con la lista y estar entre 0 y 9
select break_id, n_pocketed, len(pocketed) as listed
from {{ ref('stg_breaks') }}
where n_pocketed != len(pocketed)
   or n_pocketed not between 0 and 9
