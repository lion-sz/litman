create table files (
    file_id integer primary key,
    path text not null,
    type text not null,
    default_open integer not null,
    created_ts integer not null,
    modified_ts integer not null
);
