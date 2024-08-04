create table entry (
    id uuid primary key,
    type integer not null,
    key text not null,
    doi text,
    title text not null,
    year integer,
    url text
);

create table abstract (
    entry_id uuid not null,
    abstract text not null
);

-- Create a fts table to search the titles.
CREATE VIRTUAL TABLE entry_fts USING fts5(title, content='entry');

-- Triggers to keep the FTS index up to date.
CREATE TRIGGER entry_ai AFTER INSERT ON entry BEGIN
  INSERT INTO entry_fts(rowid, title) VALUES (new.rowid, new.title);
END;
CREATE TRIGGER entry_ad AFTER DELETE ON entry BEGIN
  INSERT INTO entry_fts(entry_fts, rowid, title) VALUES('delete', old.rowid, old.title);
END;
CREATE TRIGGER entry_au AFTER UPDATE ON entry BEGIN
  INSERT INTO entry_fts(entry_fts, rowid, title) VALUES('delete', old.rowid, old.title);
  INSERT INTO entry_fts(rowid, title) VALUES (new.rowid, new.title);
END;


CREATE VIRTUAL TABLE abstract_fts USING fts5(abstract, content='abstract');

-- Triggers to keep the FTS index up to date.
CREATE TRIGGER abstract_ai AFTER INSERT ON abstract BEGIN
  INSERT INTO abstract_fts(rowid, abstract) VALUES (new.rowid, new.abstract);
END;
CREATE TRIGGER abstract_ad AFTER DELETE ON abstract BEGIN
  INSERT INTO abstract_fts(abstract_fts, rowid, abstract) VALUES('delete', old.rowid, old.abstract);
END;
CREATE TRIGGER abstract_au AFTER UPDATE ON abstract BEGIN
  INSERT INTO abstract_fts(abstract_fts, rowid, abstract) VALUES('delete', old.rowid, old.abstract);
  INSERT INTO abstract_fts(rowid, abstract) VALUES (new.rowid, new.abstract);
END;
