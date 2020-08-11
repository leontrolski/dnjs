export const a = `foo`
const name = "oli"
const age = 29
export const b = `hello ${name},
you are ${age}`
export const c = {
    "foo": dedent(`
        "hullo"
        cat foo.txt > bar
        tail /dev/null
    `),
    "bar": "\"baz\"",
}
