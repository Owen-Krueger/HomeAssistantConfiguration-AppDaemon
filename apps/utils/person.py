from enum import Enum


class Person(Enum):
    """
    People that can be notified.
    """

    All = 'all'
    Owen = 'owen'
    Allison = 'allison'