create table file (
    id uuid primary key,
    path text not null,
    type integer not null,
    default_open integer not null
);

create table file_link (
    file_id uuid not null,
    entry_id uuid not null
);
