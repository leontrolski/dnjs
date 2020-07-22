from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any, List

from dnjs import render

data_dir = Path(__file__).parent / "data"

ctx = {
    "route_args": [],
    "members": [{"name": "Oli"}],
    "onClickF": None,
}


@dataclass
class Member:
    name: str


@dataclass
class Ctx:
    route_args: List[Any]
    members: List[Member]
    onClickF: None


dataclass_ctx = Ctx(
    route_args=[],
    members=[Member(name="Oli")],
    onClickF=None,
)

expected = dedent("""\
    <div id="account-filters">
        <h3>
            <button class="fold-button" title="expand">
                ⇕
            </button>
            Filters  🔍
        </h3>
        <div class="to-fold hidden">
        </div>
        <h3>
            <a href="#foo">
                You &amp; I
            </a>
        </h3>
        <form class="members_by_member_ids" id="my-form">
            <input class="my-input" name="member_ids" placeholder="hello: M-00-0000-0001"/>
        </form>
    </div>""")


def test_interperet():
    actual = render(data_dir / "account.dn.js", ctx)
    assert actual == expected

def test_interperet_dataclass():
    actual = render(data_dir / "account.dn.js", dataclass_ctx)
    assert actual == expected
