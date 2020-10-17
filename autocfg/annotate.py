"""Anatated types for individual hyper-parameters"""
from dataclasses import dataclass
import typing

@dataclass
class AnnotateField:
    type : typing.Any
    added : typing.Union[str, None] = None
    deprecated : typing.Union[str, None] = None
    deleted : typing.Union[str, None] = None
