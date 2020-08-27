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
    type: str  # backend|classic|decalarative


_todos = TodoList(todos=[
    Todo(message="hullo", done=False),
])


@app.get("/backend", response_class=HTMLResponse)
def get_backend() -> str:
    return dnjs.render(
        templates / "page.dn.js",
        PageData(username="leontrolski")
    )


@app.post("/backend", response_class=HTMLResponse)
def post_backend() -> str:
    return dnjs.render(
        templates / "page.dn.js",
        PageData(username="leontrolski")
    )


@app.get("/classic", response_class=HTMLResponse)
def get_classic() -> str:
    return dnjs.render(
        templates / "page.dn.js",
        PageData(username="leontrolski")
    )


@app.get("/declarative", response_class=HTMLResponse)
def declarative() -> str:
    return dnjs.render(
        templates / "page.dn.js",
        PageData(
            type="declarative",
            username="leontrolski",
        )
    )



@app.get("/todos", response_model=TodoList)
def get_todos() -> TodoList:
    return _todos


@app.put("/todos", response_model=TodoList)
def put_todos(todos: TodoList) -> TodoList:
    _todos.todos = todos.todos
    return _todos



app.mount("/static", StaticFiles(directory=static), name="static")
