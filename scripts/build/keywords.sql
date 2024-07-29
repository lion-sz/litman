create table keywords (
    id integer primary key,
    name text not null
);

create table keywords_cw (
    keyword_id integer not null,
    entry_id integer not null
);
