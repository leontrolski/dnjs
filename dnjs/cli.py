import json
from typing import Any, Callable

import click

from dnjs import (
    builtins,
    css as dnjs_css,
    parser,
    interpreter,
    html as dnjs_html,
)


@click.command(help="""
FILENAME is the djns file to be evaluated.
Remaining ARGS are files passed in as arguments
to the evaluated dnjs if it is a function.
""")
@click.argument('filename', type=click.Path(exists=True, allow_dash=True))
@click.option('--html', is_flag=True, help='Post process m(...) nodes to <html>.')
@click.option('--css', is_flag=True, help='Post process css')
@click.option('--name', help='Pick an exported variable to return as opposed to the default.')
@click.option('-p', '--process', help="Post-process the output with another dnjs function, eg: 'd=>d.value'.")
@click.argument('args', nargs=-1, type=click.File('r'))
@click.option('--raw', is_flag=True, help='Print value as literal.')
@click.option('--csv', is_flag=True, help='Print value as csv.')
@click.option('--pdb', is_flag=True, help='Drop into the debugger on failure.')
def main(filename, html, css, name, process, args, raw, csv, pdb):
    tmp = None
    try:
        if filename == "-":
            module = interpreter.interpret(source=click.get_text_stream('stdin').read())
        else:
            module = interpreter.interpret(path=path)
        if name:
            if name not in module.exports:
                raise RuntimeError(f"{name} not in {path} exports")
            value = module.exports[name]
        else:
            if module.default_export is interpreter.missing and module.value is interpreter.missing:
                raise RuntimeError(f"{path} has no default export")
            if module.default_export is not interpreter.missing:
                value = module.default_export
            else:
                value = module.value

        if isinstance(value, Callable):
            arg_names = ', '.join(f'"{n}"' for n in value.arg_names)
            if len(args) != len(value.arg_names):
                raise click.UsageError(
                    f"Expected input argument{'s' if len(arg_names) > 1 else ''}: "
                    f"{arg_names}, see --help"
                )

        for arg in args:
            json_args = [json.load(arg) for arg in args]
            value = value(*json_args)

        if len([n for n in [html, css, process] if n]) > 1:
            raise RuntimeError('can only do 1 post-process at a time')
        if html:
            return print(dnjs_html.to_html(value))
        if css:
            return print(dnjs_css.to_css(value))
        if process:
            f = interpreter.interpret(source=process).value
            assert isinstance(f, Callable)
            value = builtins.undefineds_to_none(f(value))
        if csv:
            assert isinstance(value, list)
            for row in value:
                assert isinstance(row, list)
                if raw:
                    print(",".join(rawify(n) for n in row))
                else:
                    print(",".join(json.dumps(n) for n in row))
            return
        if raw:
            return print(rawify(value))

        print(json.dumps(value))
    except:
        if pdb:
            import pdb
            pdb.post_mortem()
        raise

    if tmp is not None:
        tmp.close()


def rawify(v: Any):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return v.lower()
    if isinstance(v, (str, int, float)):
        return str(v)
    if isinstance(v, list):
        return json.dumps(v)
    if isinstance(v, dict):
        return json.dumps(v)
    raise RuntimeError("Unsupported type")

if __name__ == '__main__':
    main()
