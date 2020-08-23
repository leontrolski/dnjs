from dataclasses import dataclass
# install requirements with `pip install fastapi uvicorn aiofiles`
# run with `uvicorn examples.todo.app:app --reload`
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import dnjs


app = FastAPI()
templates = Path(__file__).parent
static = Path(__file__).parent / "static"


@dataclass
class Todo:
    message: str
    done: bool


@dataclass
class PageData:
    username: str


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return dnjs.render(
        templates / "page.dn.js",
        PageData(username="leontrolski")
    )

app.mount("/static", StaticFiles(directory=static), name="static")
