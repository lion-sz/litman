from alexandria.entries.entry import Entry as Entry
from alexandria.entries.types import Article, Book, InProceedings
from alexandria.enums import EntryTypes

entry_dispatch = {
    EntryTypes.Article: Article,
    EntryTypes.Book: Book,
    EntryTypes.InProceedings: InProceedings,
}
entry_dispatch_int = {
    EntryTypes.Article.value: Article,
    EntryTypes.Book.value: Book,
    EntryTypes.InProceedings.value: InProceedings,
}
bibtex_mapping = {
    "article": EntryTypes.Article,
    "book": EntryTypes.Book,
    "inproceedings": EntryTypes.InProceedings,
}
rev_bibtex_mapping = {v: k for k, v in bibtex_mapping.items()}
crossref_mapping = {
    "journal-article": EntryTypes.Article,
}
