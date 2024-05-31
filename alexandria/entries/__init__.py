import enum

from alexandria.entries.article import Article
from alexandria.entries.entry import Entry


class EntryTypes(enum.Enum):
    Article = 1


entry_dispatch = {
    EntryTypes.Article: Article,
}
