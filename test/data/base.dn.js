import m from "mithril"

export const base = 42
export const form = (routeArgs, name, map) => m("form#my-form",
    {"class": [name]},
    Object.entries(map).map(([k, v], i) =>
        m("input.my-input", {"name": k, "placeholder": `hello: ${v}`}))
)
