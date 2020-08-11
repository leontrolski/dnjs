# `dnjs`

`dnjs` is a pure subset of `JavaScript` that wants to replace (across many host languages):
- overly limiting/baroque **configuration languages**
- mucky string based `html`/`xml` **templating**

It is powerful yet familiar, and the reduced syntax makes it easy to implement (the reference implementation in `Python` took a couple of days to write) and easy to reason about. Currently the state is very alpha - see the `TODO` at the end.

```
╔══════════════════════════════╗
║ ╔═══════════════╗            ║
║ ║ ╔══════╗      ║            ║
║ ║ ║ JSON ║ dnjs ║ JavaScript ║
║ ║ ╚══════╝      ║            ║
║ ╚═══════════════╝            ║
╚══════════════════════════════╝
```

## Installing the reference interpreter

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
    "name": serviceName,
    "ip": environment === environments.PROD ? "189.34.0.4" : "127.0.0.1"
})

export default (environment) => serviceNames.map(
    (v, i) => makeService(environment, v)
)
```

Let's use the reference implementation written in `Python` to run these (this also has a `Python` API documented below):

```bash
dnjs examples/configuration.dn.js examples/environment.json | jq
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
dnjs examples/commentsPage.dn.js examples/comments.json --html
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

## How exactly does `dnjs` extend `JSON`?

Remember `dnjs` is a **restriction** of `JavaScript`, the aim is not to implement all of it, any more than `JSON` is.

Here are all the extensions to `JSON`, the grammar can be found [here](dnjs/grammar.lark).

- Comments with `//`.
- Optional trailing commas.
- `import { c } from "./b.dn.js"`, `import b from "./b.dn.js"`. Non-local imports are simply ignored (so as to allow importing `m` as anything).
- `export default a`, `export const b = c`.
- `dict`s and `list`s can be splatted with rest syntax: `{...a}`/`[...a]`.
- Functions can be defined with `const f = (a, b) => c` syntax.
- Ternary expressions, _only_ in the form `a === b ? c : d`. Equality should be implemented however `JavaScript` does.
- Map, filter, map over dict, dict from entries, in the form `a.map((v, i) => b)`, `a.filter((v, i) => b)`, `Object.entries(a).map(([k, v], i) => b)`, `Object.fromEntries(a)`.
- Hyperscript, somewhat compatible with [mithril](https://mithril.js.org/) - `m("sometag#some-id.some-class.other-class", {"href": "foo.js", "class": ["another-class"]}, children)`, this evaluates to `dict`s like `{"tag": "sometag", "attrs": {"id": "some-id", className: "some-class other-class another-class", "href": "foo.js", "children": children}`.
- Multiline templates in the form `` `foo ${a}` ``, `` dedent(`foo ${a}`) ``. `dedent` should work the same as [this npm package](https://www.npmjs.com/package/dedent).
- Lists have `.length`, `.includes(a)` attributes.

## Name

Originally the name stood for DOM Notation JavaScript.

## Python

### API

These functions return `JSON`-able data:

```python
from djns import get_default_export, get_named_export

get_default_export(path)
get_named_export(path, name)
```

This function returns html as a `str`:

```python
from djns import render

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
  - Allow skipping escaping with `m.trust()`?
  - Common string functions like upper case, replace etc?
  - `parseInt` etc..
- Standalone (in `c`/`rust`/`go`? with `Python` bindings) to JSON program.
- Name things in the grammar, catch `lark` exceptions and make custom user ones.
- Write JS library that simply wraps mithril render and has a `dnjs.isValid(path)` function that uses the grammar (doing this may involve removing some `lark`-specific bits in the grammar.
- Typescript support?
- Consider what prevents `dnjs` from becoming a data interchange format - eg. infinite recursion. `--safe` mode should probably have no functions and no imports.
- Allow importing JSON using Experimental JSON modules](https://nodejs.org/api/esm.html#esm_experimental_json_modules).
- Remove accidental non-js compatability - eg. template grammar is a bit wacky.
- Handle _ambig
