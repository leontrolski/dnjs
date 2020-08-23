// rebuild .css file with
// dnjs examples/todo/style.dn.js --css > examples/todo/static/style.css

const _classes = {
    "bold": {
        "font-weight": "bold",
    },
    "red": {
        "color": "red",
    },
}

const namespace = "todo"
// export classes = {"bold": "todo-bold", ...}
// export default = {".todo-bold": {...}, ...}
export const classes = Object.fromEntries(
    Object.entries(_classes)
    .map(([k, v], _) => [k, `${namespace}-${k}`])
)
export default Object.fromEntries(
    Object.entries(_classes)
    .map(([k, v], _) => [`.${namespace}-${k}`, v])
)
