create table files (
    file_id integer primary key,
    path text not null,
    type integer not null,
    default_open integer not null,
    created_ts integer not null,
    modified_ts integer not null
);

create table file_cw (
                         id integer primary key,
                         entry_id integer not null,
                         file_id integer not null
);
