-- Sync Table Triggers
CREATE TRIGGER {table}_ti AFTER INSERT ON {table} BEGIN
    INSERT INTO transaction_log(id, source, date, type) VALUES(new.id, '{table}', unixepoch(), 1);
END;

CREATE TRIGGER {table}_tu AFTER UPDATE ON {table} BEGIN
    INSERT INTO transaction_log(id, source, date, type) VALUES(new.id, '{table}', unixepoch(), 2);
END;

CREATE TRIGGER {table}_td AFTER DELETE ON {table} BEGIN
    INSERT INTO transaction_log(id, source, date, type) VALUES(old.id, '{table}', unixepoch(), 3);
END;
