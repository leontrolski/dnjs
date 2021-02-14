from . import builtins


def to_css(value: builtins.Value) -> str:
    assert isinstance(value, dict)
    lines = []
    for k, v in value.items():
        assert isinstance(v, dict)
        values = "\n".join(f"    {attr}: {value};" for attr, value in v.items())
        line = f"{k} {{\n{values}\n}}"
        lines.append(line)
    return "\n".join(lines)
