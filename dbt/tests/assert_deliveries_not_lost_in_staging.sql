-- Row-count reconciliation raw -> marts: joins in staging must not drop or fan out balls.
select 'mismatch' as issue
from (select count(*) as n from {{ ref('base_deliveries') }}) r
cross join (select count(*) as n from {{ ref('fct_deliveries') }}) f
where r.n <> f.n
