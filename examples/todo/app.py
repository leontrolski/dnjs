from dataclasses import dataclass
from functools import partial
import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import dnjs


app = FastAPI()
root = Path(__file__).parent
templates = root / "templates"
static = root / "static"
shared = root / "shared"
render = partial(dnjs.render, templates / "page.dn.js")


class Todo(BaseModel):
    message: str
    done: bool


class TodoList(BaseModel):
    todos: List[Todo]


@dataclass
class State:
    todos: List[Todo]
    new: str


@dataclass
class Actions:
    toggle: None = None
    updateNew: None = None
    add: None = None


@dataclass
class PageData:
    username: str
    type: str  # backend|classic|declarative
    state: State
    actions: Actions = Actions()


# This is a stand-in for a db
_todos = TodoList(todos=[
    Todo(message="hullo", done=False), Todo(message="goodbye", done=True),
])

def _make_page() -> str:
    return render(PageData(
        type="backend",
        username="Ms Backend",
        state=State(todos=_todos.todos, new=""),
    ))


@app.get("/backend", response_class=HTMLResponse)
def get_backend() -> str:
    return _make_page()


@app.post("/backend", response_class=HTMLResponse)
def post_backend(
    newMessage: str = Form(default=""),
    doneCheckbox: List[int] = Form(default=[]),
) -> str:
    if newMessage:
        _todos.todos.append(Todo(message=newMessage, done=False))
    for i, todo in enumerate(_todos.todos):
        todo.done = i in doneCheckbox
    return _make_page()


@app.get("/classic", response_class=HTMLResponse)
def classic() -> str:
    return render(PageData(
        type="classic",
        username="Ms Classic",
        state=State(todos=_todos.todos, new=""),
    ))

@app.put("/classic/todos/{i}/toggle")
def classic_toggle(i: int) -> None:
    _todos.todos[i].done = not _todos.todos[i].done

@app.post("/classic/todos")
def classic_toggle(todo: Todo) -> None:
    _todos.todos.append(todo)


@app.get("/declarative", response_class=HTMLResponse)
def declarative() -> str:
    return render(PageData(
        type="declarative",
        username="Ms Declarative",
        state=State(todos=[], new=""),
    ))


@app.get("/declarative/todos", response_model=TodoList)
def get_todos() -> TodoList:
    return _todos


@app.put("/declarative/todos", response_model=TodoList)
def put_todos(todos: TodoList) -> TodoList:
    _todos.todos = todos.todos
    return _todos


app.mount("/static", StaticFiles(directory=static), name="static")
app.mount("/shared", StaticFiles(directory=shared), name="shared")
