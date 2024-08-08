-- Sync Table Triggers
CREATE TRIGGER {table}_link_ti AFTER INSERT ON {table} BEGIN
INSERT INTO transaction_log_link(id_left, id_right, source, date, type) VALUES(new.{id_a}, new.{id_b}, '{table}', unixepoch(), 1);
END;

CREATE TRIGGER {table}_link_td AFTER DELETE ON {table} BEGIN
INSERT INTO transaction_log_link(id_left, id_right, source, date, type) VALUES(old.{id_a}, old.{id_b}, '{table}', unixepoch(), 3);
END;
