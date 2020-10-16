"""Anatated types for individual hyper-parameters"""
from dataclasses import dataclass
import typing

@dataclass
class Annotate:
    type : typing.Any
    added : typing.Union[str, None] = None
    deprecated : typing.Union[str, None] = None
    deleted : typing.Union[str, None] = None
