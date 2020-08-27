const namespace = "todo"

const _global = {
    "body": {
        "font-family": "sans-serif",
    },
    "ul": {
        "padding-inline-start": "0",
    },
}
const _classes = {
    bold: {
        "font-weight": "bold",
    },
    red: {
        "color": "red",
    },
    todo: {
        "display": "block",
        "width": "15em",
        "border": "solid 2px darkorange",
        "margin": "1em",
        "padding": "1em",
        "box-shadow": "5px 5px 0 0 black",
    }
}

// {"bold": "todo-bold", ...}
const namespaceMap = Object.fromEntries(
    Object.entries(_classes)
    .map(([k, v], _) => [k, `${namespace}-${k}`])
)
// {".todo-bold": {...}, ...}
const namespaced = Object.fromEntries(
    Object.entries(_classes)
    .map(([k, v], _) => [`.${namespace}-${k}`, v])
)
export const classes = namespaceMap
export default {..._global, ...namespaced}
