from dataclasses import dataclass
from enum import IntEnum, auto
from typing import List
import sqlite3


class ToDoItemStatus(IntEnum):
    UNKNOWN = 0
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()


@dataclass
class ToDoItem:
    id: int
    task: str
    status: ToDoItemStatus


@dataclass
class UserEvent:
    id: int
    date: str
    description: str
