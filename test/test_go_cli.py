from functools import partial
from io import StringIO
from pathlib import Path
from subprocess import run

call = partial(run, capture_output=True, shell=True)

class Cmd(str):
    def __add__(self, other):
        return Cmd(" ".join([self, str(other)]))

DATA = Path(__file__).parent / "data"
EXAMPLES = Path(__file__).parent.parent / "examples"
BUILD = f"docker run -v {Path(__file__).parent.parent}:/src -t go ./build"
CMD = Cmd("dnjs-go/dist/darwin/amd64/dnjs")

def test_build():
    call(BUILD)


def test_basic():
    out = call(CMD + DATA / "functionCall.dn.js")
    assert out.returncode == 0
    assert out.stdout == b'{"hello":42}\n'

    out = call(CMD + "--pretty" + DATA / "functionCall.dn.js")
    assert out.returncode == 0
    assert out.stdout == b'{\n    "hello": 42\n}\n'


def test_file_missing():
    out = call(CMD + DATA / "fooooooo.dn.js")
    assert out.returncode == 1
    assert b'no such file' in out.stderr


def test_name():
    out = call(CMD + DATA / "thisExports.dn.js")
    assert out.returncode == 0
    assert out.stdout == b'"DEFAULT"\n'

    out = call(CMD + DATA / "thisExports.dn.js" + "--name a")
    assert out.returncode == 1
    assert out.stderr == b'too many arguments provided, try put them before the filename, or dnjs --help\n'

    out = call(CMD + "--name a" + DATA / "thisExports.dn.js")
    assert out.returncode == 0
    assert out.stdout == b'[{"A":1}]\n'

    out = call(CMD + "--name fooooo" + DATA / "thisExports.dn.js")
    assert out.returncode == 1
    assert b'does not export fooooo' in out.stderr


def test_argument():
    out = call(CMD + EXAMPLES / "configuration.dn.js")
    assert out.returncode == 1
    assert b'function needs calling with 1 argument(s)' in out.stderr

    out = call(CMD + EXAMPLES / "configuration.dn.js" + EXAMPLES / "environment.json")
    assert out.returncode == 0
    assert out.stdout == b'[{"ip":"127.0.0.1","name":"signup"},{"ip":"127.0.0.1","name":"account"}]\n'

    out = call(CMD + EXAMPLES / "configuration.dn.js" + EXAMPLES / "environment.json" + "dfgdfg")
    assert out.returncode == 1
    assert b'function needs calling with 1 argument(s)' in out.stderr

    out = call(CMD + EXAMPLES / "configuration.dn.js" + "foooo.json")
    assert out.returncode == 1
    assert b'no such file or directory' in out.stderr


def test_html():
    out = call(CMD + "--html" + EXAMPLES / "commentsPage.dn.js" + EXAMPLES / "comments.json")
    assert out.returncode == 0
    assert out.stdout == b'''<html>
    <head>
        <script src="someScript.js">

        </script>

    </head>
    <body>
        <ul>
            <li>
                Comment 0 says: hiya!
            </li>
            <li>
                Comment 1 says: oioi
            </li>

        </ul>

    </body>

</html>
'''

def test_css():
    out = call(CMD + "--css" + EXAMPLES / "css.dn.js")
    assert out.returncode == 0
    assert out.stdout == b'''.bold {
    font-weight: bold;
}
.red {
    color: red;
}
'''


def test_as_jq():
    JSON = b'[{foo: 1, bar: "one"}, {foo: 2, bar: "two"}]'

    out = call(CMD + "-p 'a=>a.map(b=>[b.bar, b.foo])' -", input=JSON)
    assert out.returncode == 0
    assert out.stdout == b'[["one",1],["two",2]]\n'

    out = call(CMD + "-p 'a=>a.map(b=>[b.bar, b.foo])' --csv -", input=JSON)
    assert out.returncode == 0
    assert out.stdout == b'"one",1\n"two",2\n'

    out = call(CMD + "-p 'a=>a.map(b=>[b.bar, b.foo, true])' --csv --raw -", input=JSON)
    assert out.returncode == 0
    assert out.stdout == b'one,1,true\ntwo,2,true\n'

    out = call(CMD + "-p 'a=>a.map(b=>[b.bar, b.foo, trueee])' --csv -", input=JSON)
    assert out.returncode == 1
    assert out.stderr == b'''<ParserError line:1>
variable trueee is not in scope
a=>a.map(b=>[b.bar, b.foo, trueee])
___________________________^
'''

    out = call(CMD + "-p 'a=>a.map(b=>[b.bar, b.foo, ()=>4])' --csv --raw -", input=JSON)
    assert out.returncode == 1
    assert out.stderr == b"Unsupported type: <function: (=> (d*) '4)>\n"

    JSON = b'[{foo: 1, bar: "one"}, {foo: 2, bar: "two"}]'

