create table entries (
    id integer primary key,
    type integer not null,
    key text not null,
    doi text,
    title text not null,
    author text,
    year integer,
    created_ts integer not null,
    modified_ts integer not null
);

-- Create a fts table to search the titles.
CREATE VIRTUAL TABLE entries_fts USING fts5(title, author, content='entries', content_rowid='id');

-- Triggers to keep the FTS index up to date.
CREATE TRIGGER tbl_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid, title, author) VALUES (new.id, new.title, new.author);
END;
CREATE TRIGGER tbl_ad AFTER DELETE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, title, author) VALUES('delete', old.id, old.title, old.author);
END;
CREATE TRIGGER tbl_au AFTER UPDATE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, title, author) VALUES('delete', old.id, old.title, old.author);
  INSERT INTO entries_fts(rowid, title, author) VALUES (new.id, new.title, old.author);
END;
