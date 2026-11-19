-- Un quiebre por fila, con el resultado clasificado y su celda en la grilla de parámetros
select
    *,
    n_pocketed > 0 and not scratch as is_successful,
    case
        when scratch then 'falta'
        when nine_on_break then 'gana con la 9'
        when n_pocketed > 0 then 'sigue jugando'
        else 'no emboca'
    end as outcome,
    floor(v0 / {{ var('v0_bin_size') }}) * {{ var('v0_bin_size') }} as v0_bin,
    floor(cut / {{ var('cut_bin_size') }}) * {{ var('cut_bin_size') }} as cut_bin
from {{ ref('stg_breaks') }}
