create table author (
    id uuid primary key,
    first_name text,
    suffix text,
    last_name text not null
);

create table author_link (
    author_id uuid not null,
    entry_id uuid not null
)
