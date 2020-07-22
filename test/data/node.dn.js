export const a = m("br")
const l = [1, 2, 3]
export const b = m(".foo.bar",
    {"id": "rarr", "class": ["baz"]},
    m("ul#qux", l.map((v, i) => m("li", i))),
    ["apple", m("br")]
)
