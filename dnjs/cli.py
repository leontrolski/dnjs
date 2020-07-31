import json

import click

from . import get_default_export, get_named_export
from . import parser, interpreter, html as dnjs_html


@click.command(help="""
FILENAME is the djns file to be evaluated.
Remaining ARGS are files passed in as arguments
to the evaluated dnjs if it is a function.
""")
@click.argument('filename', type=click.Path(exists=True))
@click.option('--html', is_flag=True, help='Post process m(...) nodes to <html>.')
@click.option('--name', help='Pick an exported variable to return as opposed to the default.')
@click.argument('args', nargs=-1, type=click.File('r'))
@click.option('--pdb', is_flag=True, help='Drop into the debugger on failure.')
def main(filename, html, name, args, pdb):
    try:
        if name:
            value = get_named_export(filename, name)
        else:
            value = get_default_export(filename)

        if isinstance(value, interpreter.Function):
            arg_names = ', '.join(f'"{n}"' for n in value.arg_names)
            if len(args) != len(value.arg_names):
                raise click.UsageError(
                    f"Expected input argument{'s' if len(arg_names) > 1 else ''}: "
                    f"{arg_names}, see --help"
                )

        for arg in args:
            json_args = [json.load(arg) for arg in args]
            value = value(*json_args)

        if html:
            print(dnjs_html.to_html(value))
        else:
            print(json.dumps(value))
    except:
        if pdb:
            import pdb
            pdb.post_mortem()
        raise


if __name__ == '__main__':
    main()