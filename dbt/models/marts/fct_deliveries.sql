select
    cast(d.match_id as varchar(20)) || '-' || cast(d.innings as varchar(2)) || '-'
        || cast(d.over_number as varchar(3)) || '-' || cast(d.ball_seq as varchar(3)) as delivery_id,
    d.*,
    m.season_year,
    m.match_date,
    m.venue,
    m.is_playoff
from {{ ref('stg_deliveries') }} d
join {{ ref('stg_matches') }} m on m.match_id = d.match_id
