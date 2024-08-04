import re
import uuid
import typing

from litman.db_connector import DB


class Author:
    id: uuid.UUID | None
    first_name: str | None
    suffix: str | None
    last_name: str

    names = ["id", "first_name", "suffix", "last_name"]
    _load_id_q = "SELECT {names} FROM author WHERE id = ?"
    _save_q = "INSERT INTO author ({names}) VALUES (?, ?, ?, ?)"
    _count_links_q = "SELECT COUNT(*) FROM author_link WHERE author_id = ?"
    _delete_q = "DELETE FROM author WHERE id = ?"
    _delete_all_links_q = "DELETE FROM author_link WHERE author_id = ?"

    def __init__(
        self,
        id: uuid.UUID | None,
        first_name: str | None,
        suffix: str | None,
        last_name: str,
    ):
        self.id = id
        self.first_name = first_name.strip() if first_name else None
        self.suffix = suffix.strip() if suffix else None
        self.last_name = last_name.strip()

    def data(self) -> tuple:
        """Return the data as a tuple"""
        return (self.id, self.first_name, self.suffix, self.last_name)

    @classmethod
    def load_id(cls, db: DB, id: int) -> typing.Self:
        data = db.cursor.execute(
            cls._load_id_q.format(names=", ".join(cls.names)),
            (id,),
        ).fetchone()
        if len(data) == 0:
            raise ValueError(f"No author found for id '{id}'")
        return cls(*data)

    def _check_id(self, db: DB) -> uuid.UUID | None:
        q = "SELECT id FROM author WHERE last_name = ?"
        args = [self.last_name]
        if self.first_name:
            q += " AND first_name = ?"
            args.append(self.first_name)
        else:
            q += " AND first_name IS NULL"
        if self.suffix:
            q += " AND suffix = ?"
            args.append(self.suffix)
        else:
            q += " AND suffix IS NULL"
        author_id = db.cursor.execute(q, args).fetchone()
        if author_id is not None:
            return author_id[0]
        else:
            return None

    def save(self, db: DB) -> None:
        # Check if an entry already exists.
        if self.id is not None:
            return
        existing_id = self._check_id(db)
        if existing_id is not None:
            self.id = existing_id
            return
        save_q = self._save_q.format(names=", ".join(self.names))
        self.id = uuid.uuid4()
        db.cursor.execute(save_q, self.data())
        return

    def delete(self, db: DB, force: bool = False) -> None:
        """Delete the author.

        The author will be deleted if no entry links ot this author,
        or if the 'force' keyword argument is set.
        """
        if force:
            delete = True
        else:
            delete = (
                db.cursor.execute(self._count_links_q, (self.id,)).fetchone()[0] == 0
            )
        if delete:
            db.cursor.execute(self._delete_q, (self.id,))
            if force:
                db.cursor.execute(self._delete_all_links_q, (self.id,))
        return

    def __str__(self) -> str:
        if self.suffix is not None:
            return f"{self.last_name}, {self.suffix}, {self.first_name}"
        elif self.first_name is not None:
            return f"{self.last_name}, {self.first_name}"
        else:
            return self.last_name

    def __eq__(self, other: typing.Self) -> bool:
        if self.id is not None and other.id is not None:
            return self.id == other.id
        else:
            return (
                (self.last_name == other.last_name)
                and (self.first_name == other.first_name)
                and (self.suffix == other.suffix)
            )

    @property
    def printable_name(self) -> str:
        return str(self)

    @classmethod
    def parse_authors(cls, author_str: str, db: DB | None = None) -> list[typing.Self]:
        """Parse the Authors from a bibtex author string.

        If the database is passed, automatically try to load the id.
        """
        authors = re.split(" and ", author_str, flags=re.IGNORECASE)
        if len(authors) == 1:
            author = authors[0]
            # There are three allowed formats (see https://bibtex.eu/fields/author/)
            #   1. Firstname Lastname
            #   2. Lastname, Firstname
            #   3. Lastname, Suffix, Firstname
            if author.count(",") > 2:
                raise ValueError("Parsing of the Author failed, too many ','.")
            if "," in author:
                last_name, right = author.split(",", maxsplit=1)
                if "," in right:
                    suffix, first_name = right.split(",")
                else:
                    suffix, first_name = None, right
            else:
                if " " not in author:
                    first_name, last_name = None, author
                else:
                    first_name, last_name = author.rsplit(" ", maxsplit=1)
                suffix = None
            author = cls(None, first_name, suffix, last_name)
            if db is not None:
                author.id = author._check_id(db)
            return [author]
        else:
            return [cls.parse_authors(author)[0] for author in authors]
