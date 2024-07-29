from enum import Enum


class EntryTypes(Enum):
    Article = 1
    Book = 2


class FileType(Enum):
    PDF = 1
    Appendix = 2
    Supplemental = 3
    Other = 100
