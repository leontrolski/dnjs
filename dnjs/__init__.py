from pathlib import Path
from typing import Callable, Dict, Tuple, Union

from dnjs import builtins, interpreter, html


def get_default_export(path: Union[Path, str]) -> builtins.Value:
    if not isinstance(path, Path):
        path = Path(path)
    module = interpreter.interpret(path)
    if module.default_export is interpreter.missing and module.value is interpreter.missing:
        raise RuntimeError(f"{path} has no default export")
    if module.default_export is not interpreter.missing:
        return module.default_export
    return module.value


def get_named_export(path: Union[Path, str], name: str) -> builtins.Value:
    if not isinstance(path, Path):
        path = Path(path)
    module = interpreter.interpret(path)
    if name not in module.exports:
        raise RuntimeError(f"{name} not in {path} exports")
    return module.exports[name]


def render(path: Union[Path, str], *values: builtins.Value) -> str:
    if not isinstance(path, Path):
        path = Path(path)

    values = tuple(html.make_value_js_friendly(v) for v in values)
    f = get_default_export(path)
    assert isinstance(f, Callable)
    html_tree = f(*values)
    return html.to_html(html.make_value_js_friendly(html_tree))
