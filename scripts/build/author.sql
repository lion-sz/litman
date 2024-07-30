create table author (
    id integer primary key,
    first_name text,
    suffix text,
    last_name text not null
);

create table author_link (
    author_id integer not null,
    entry_id integer not null
)
