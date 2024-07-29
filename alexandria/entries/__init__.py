from alexandria.entries.article import Article
from alexandria.entries.book import Book
from alexandria.entries.entry import Entry
from alexandria.enums import EntryTypes

entry_dispatch = {
    EntryTypes.Article: Article,
    EntryTypes.Book: Book,
}
entry_dispatch_int = {
    EntryTypes.Article.value: Article,
    EntryTypes.Book.value: Book,
}
bibtex_mapping = {
    "article": EntryTypes.Article,
    "book": EntryTypes.Book,
}
rev_bibtex_mapping = {v: k for k, v in bibtex_mapping.items()}
