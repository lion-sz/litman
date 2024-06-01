import enum

from alexandria.entries.article import Article
from alexandria.entries.entry import Entry


class EntryTypes(enum.Enum):
    Article = 1


entry_dispatch = {
    EntryTypes.Article: Article,
}
entry_dispatch_int = {
    EntryTypes.Article.value: Article,
}
bibtex_mapping = {
    "article": EntryTypes.Article,
}
rev_bibtex_mapping = {
    EntryTypes.Article.value: "article",
}
