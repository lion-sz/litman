create table article (
    id uuid primary key,
    journal text,
    volume text,
    number text,
    pages text,
    month int
);

create table book (
    id uuid primary key,
    publisher text,
    address text,
    edition text
);

create table inProceedings (
    id uuid primary key,
    booktitle text,
    editor text,
    volume text,
    number text,
    series text,
    pages text,
    address text,
    month int,
    organization text,
    publisher text
)
