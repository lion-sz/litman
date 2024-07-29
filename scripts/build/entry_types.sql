create table articles (
    entry_id integer primary key,
    journal text,
    volume text,
    pages text
);

create table books (
    entry_id integer primary key,
    publisher text,
    version text
)
