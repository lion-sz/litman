create table keyword (
    id uuid primary key,
    name text not null
);

create table keyword_link (
    keyword_id uuid not null,
    entry_id uuid not null
);
