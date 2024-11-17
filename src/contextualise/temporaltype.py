"""
TemporalType enumeration. Part of the Contextualise (https://contextualise.dev) project.

November 17, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from enum import Enum


class TemporalType(Enum):
    EVENT = 1
    ERA = 2

    def __str__(self):
        return self.name.lower()
