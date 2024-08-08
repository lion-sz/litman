--Type Mapping:
--  1: Insert
--  2: Update
--  3: Delete
create table transaction_log (
    id uuid,
    source text,
    date integer,
    type integer
);

create table transaction_log_link (
    id_left uuid,
    id_right uuid,
    source text,
    date integer,
    type integer
);

create table sync_log (
    date integer
)
