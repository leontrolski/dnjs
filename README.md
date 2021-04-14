# `dnjs`

```
╔══════════════════════════════╗
║ ╔═══════════════╗            ║
║ ║ ╔══════╗      ║            ║
║ ║ ║ JSON ║ dnjs ║ JavaScript ║
║ ║ ╚══════╝      ║            ║
║ ╚═══════════════╝            ║
╚══════════════════════════════╝
```

`dnjs` is a pure subset of `JavaScript` that wants to replace (across many host languages - currently `go` and `Python`):
- `yaml` - Overly limiting/baroque [**configuration languages**](#for-configuration)
- `handlebars` - Mucky string based `html`/`xml` [**templating**](#for-html-templating) - _see [blog post](https://leontrolski.github.io/semi-isomorphic.html)_
- `jq` - Unfamiliar `JSON` [**processing languages**](#as-a-jq-replacement)

It is powerful yet familiar, and the reduced syntax makes it easy to implement. _Currently the state is very alpha - see the `TODO` at the end._


Feature | Syntax
---------|----------
Comments | `//`
Unquoted `Object` keys | `{a: 42}`
Trailing commas | `{a: 42, }`
Imports _(Non-local imports are simply ignored)_ | `import { c } from "./b.dn.js"`
 | `import b from "./b.dn.js"`
Exports | `export default a`
 | `export const b = c`
Rest syntax | `{...a}`, `[...a]`
Arrow Functions | `const f = (a, b) => c`
Ternary expressions | `a === b ? c : d`
Map | `a.map((v, i) => b)`
Filter | `a.filter((v, i) => b)`
Reduce | `a.reduce((x, y) => [...x, ...y], [])`
Entries | `Object.entries(a).map(([k, v], i) => b)`
From entries | `Object.fromEntries(a)`
Hyperscript, somewhat compatible with [mithril](https://mithril.js.org/) | `m("sometag#some-id.some-class.other-class", {"href": "foo.js", "class": ["another-class"]}, children)`
_Evaluates to_ | `{"tag": "sometag", "attrs": {"id": "some-id", className: "some-class other-class another-class", "href": "foo.js", "children": children}`
_For trusted html_ | `m.trust(a)`
Templates | `` `foo ${a}` ``
Dedent | `` dedent(`foo ${a}`) ``
List functions | `.length`, `.includes(a)`

## Installing the standalone binary

[Downloads](dnjs-go/dist)

## Installing the Python interpreter/API

```bash
pip install dnjs
dnjs --help
```

## Examples

_Some of these examples reference other files in [the examples folder](examples)._

### For configuration:

```js
import { environments } from "./global.dn.js"

// names of the services to deploy
const serviceNames = ["signup", "account"]

const makeService = (environment, serviceName) => ({
    name: serviceName,
    ip: environment === environments.PROD ? "189.34.0.4" : "127.0.0.1"
})

export default (environment) => serviceNames.map(
    (v, i) => makeService(environment, v)
)
```

Running:

```bash
dnjs --pretty examples/configuration.dn.js examples/environment.json
```

Gives us:

```js
[
  {
    "name": "signup",
    "ip": "127.0.0.1"
  },
  {
    "name": "account",
    "ip": "127.0.0.1"
  }
]
```

### For `html` templating

`dnjs` prescribes functions for making `html`, that handily are a subset of [mithril](https://mithril.js.org/) (this makes it possible to write powerful, reusable cross-language `html` components).

Given the file `commentsPage.dn.js`:

```js
import m from "mithril"

import { page } from "./basePage.dn.js"

const commentList = (comments) => m("ul",
    comments.map((comment, i) => m("li", `Comment ${i} says: ${comment.text}`))
)

export default (comments) => page(commentList(comments))
```

Then in a python webserver we can render the file as `html`:

```python
from dnjs import render

@app.route("/some-route"):
def some_route():
    ...
    return render("commentsPage.dn.js", comments)
```

And the endpoint will return:

```html
<html>
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
```

Or we can use the same components on the frontend with [mithril](https://mithril.js.org/):

```js
import page from "../commentsPage.dn.js"
...
m.mount(document.body, page)
```

Or we can render the `html` on the command line similar to before:

```bash
dnjs --html examples/commentsPage.dn.js examples/comments.json
```

Note, that without the `--html` flag, we still make the following `JSON`, the conversion to `html` is a post-processing stage:

```js
{
  "tag": "html",
  "attrs": {
    "className": ""
  },
  "children": [
    {
      "tag": "head",
      "attrs": {
...
```

### For `css` templating

Using `--css` will post-process eg:

```js
export default {
  ".bold": {"font-weight": "bold"},
  ".red": {"color": "red"},
}
```

to:

```css
.bold {
    font-weight: bold;
}
.red {
    color: red;
}
```

### As a `jq` replacement

```bash
JSON='[{foo: 1, bar: "one"}, {foo: 2, bar: "two"}]'
echo $JSON | dnjs -p 'a=>a.map(b=>[b.bar, b.foo])' -
```

```js
[["one", 1], ["two", 2]]
```

#### csv

```bash
echo $JSON | dnjs -p 'a=>a.map(b=>[b.bar, b.foo])' --csv -
```

```
"one",1
"two",2
```

#### csv, raw

```bash
echo $JSON | dnjs -p 'a=>a.map(b=>[b.bar, b.foo])' --csv --raw -
```

```
one,1
two,2
```

#### jsonl

```bash
JSON='{foo: 1, bar: "one"}\n{foo: 2, bar: "two"}'
echo $JSON | while read l; do echo $l | dnjs -p 'a=>a.bar' --raw -; done
```

```
one
two
```

#### Flattening

Remember, you can flatten arrays with:

```js
.reduce((a, b)=>[...a, ...b], [])
```

## Name

Originally the name stood for DOM Notation JavaScript.

## Python

### API

These functions return `JSON`-able data:

```python
from dnjs import get_default_export, get_named_export

get_default_export(path)
get_named_export(path, name)
```

This function returns html as a `str`:

```python
from dnjs import render

render(path, *values)
```

The types used throughout `dnjs` are fairly simple `dataclass`s , there's not much funny stuff going on in the code - check it out!

### Development

Install dev requirements with:

```bash
pip install -r requirements-dev.txt
```

Run tests with:

```bash
pytest
```

Pin requirements with:

```bash
pip-compile -q; cat requirements.in requirements-dev.in | pip-compile -q --output-file=requirements-dev.txt -
```

Rebuild and publish (after upversioning) with:

```bash
# up version setup.py
rm dist/*; python setup.py sdist bdist_wheel; twine upload dist/*
```

## JS

_Javascript validation library to follow - see `TODO` section below._

Run tests with:

```bash
npm install
npm test
```

# TODO

- Use on something real to iron out bugs.
- Spec out weird behaviour + make the same as js:
  - numbers
  - `===`
- Nicer docs:
  - Write up why we don't need filters like | to_human.
- Consider `onclick`, `onkeydown`, `on...` functions... and how we want to handle them / attach them on reaching the browser in a isomophic setup.
- Decide what else should be added:
  - Common string functions like upper case, replace etc?
  - `parseInt` etc..
- Write JS library that simply wraps mithril render and has a `dnjs.isValid(path)` function that uses the grammar (doing this may involve removing some `lark`-specific bits in the grammar.
- Typescript support?
- Consider what prevents `dnjs` from becoming a data interchange format - eg. infinite recursion. `--safe` mode? Specify PATHs that it's permitted to import from.
- Allow importing JSON using Experimental JSON modules](https://nodejs.org/api/esm.html#esm_experimental_json_modules).
- Remove accidental non-js compatability - eg. template grammar is a bit wacky.
