create table collection (
    id uuid primary key,
    name text not null,
    description text
);

create table collection_link (
    entry_id uuid not null,
    collection_id uuid not null
);
