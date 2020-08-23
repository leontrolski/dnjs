from pathlib import Path
from typing import Dict, Tuple, Union

from . import parser
from . import interpreter
from . import html

def get_default_export(path: Union[Path, str]) -> interpreter.Value:
    if not isinstance(path, Path):
        path = Path(path)
    module = interpreter.interpret(path)
    if module.default_export is interpreter.missing and module.value is interpreter.missing:
        raise RuntimeError(f"{path} has no default export")
    if module.value is interpreter.missing:
        return module.default_export
    if module.default_export is interpreter.missing:
        return module.value


def get_named_export(path: Union[Path, str], name: str) -> interpreter.Value:
    if not isinstance(path, Path):
        path = Path(path)
    module = interpreter.interpret(path)
    if name not in module.exports:
        raise RuntimeError(f"{name} not in {path} exports")
    return module.exports[name]


TEMPLATE_CACHE: Dict[Tuple[str, float], interpreter.Function] = {}

def render(path: Union[Path, str], *values: interpreter.Value, prettify: bool = True) -> str:
    if not isinstance(path, Path):
        path = Path(path)

    cache_key = str(path), path.stat().st_mtime
    values = html.make_value_js_friendly(values)

    f = TEMPLATE_CACHE.get(cache_key)
    if f is None:
        f = get_default_export(path)
        assert isinstance(f, interpreter.Function)
        TEMPLATE_CACHE[cache_key] = f

    return html.to_html(f(*values), prettify=prettify)
