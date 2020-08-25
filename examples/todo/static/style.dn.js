const namespace = "todo"

const _classes = {
    bold: {
        "font-weight": "bold",
    },
    red: {
        "color": "red",
    },
}

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
