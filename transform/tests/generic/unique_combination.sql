{% test unique_combination(model, columns) %}
-- Unicidad de una combinación de columnas, sin depender del paquete dbt_utils
select {{ columns | join(', ') }}
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
