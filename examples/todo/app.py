from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import dnjs


app = FastAPI()
templates = Path(__file__).parent / "templates"
static = Path(__file__).parent / "static"


class Todo(BaseModel):
    message: str
    done: bool


class TodoList(BaseModel):
    todos: List[Todo]


@dataclass
class PageData:
    username: str


_todos = TodoList(todos=[
    Todo(message="hullo", done=False),
])

@app.get("/todos", response_model=TodoList)
def todos() -> TodoList:
    return _todos


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return dnjs.render(
        templates / "page.dn.js",
        PageData(username="leontrolski")
    )


app.mount("/static", StaticFiles(directory=static), name="static")
