create table collections (
    id integer primary key,
    name text not null,
    description text,
    created_ts integer not null,
    modified_ts integer not null
);

create table collection_cw (
    id integer primary key,
    entry_id integer not null,
    collection_id integer not null
);
