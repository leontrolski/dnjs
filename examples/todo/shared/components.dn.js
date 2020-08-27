// normally, here we would do one of:
// import m from "https://unpkg.com/dnjs2dom@0.0.1/index.js"
// import m from "https://unpkg.com/mithril@2.0.4/mithril.min.js"
// but we do it in `page.dn.js` so we can support either way
// for demonstration purposes

import { classes } from "./style.dn.js"

export const Todo = (todo, toggle) => m("li",
    {class: [classes.todo]},
    todo.message,
    // name, value, type, checked are used by `backend`
    // type, checked, onclick are used by `declarative`
    m("input.doneCheckbox", {name: "doneCheckbox", value: todo.i, type: "checkbox", checked: todo.done, onclick: () => toggle(todo.i)}),
)

export const TodoList = (state, actions) => m("form#todoListForm",
    // method, id are used by `backend`
    // onsubmit is used by `declarative`
    {onsubmit: actions.add, method: "POST"},
    m("ul#todoListUl", state.todos.map((todo, i) =>Todo({...todo, i: i}, actions.toggle))),
    m("input#newMessage", {name: "newMessage", value: state.new, oninput: actions.updateNew, placeholder: "message", autocomplete: "off"}),
    m("button", "add todo"),
)
