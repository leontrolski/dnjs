import { classes } from "./style.dn.js"

const state = {
    todos: [],
    new: "",
}
const put = async () => {
    m.request({url: "/todos", method: "PUT", body: {todos: state.todos}})
}
const get = async () => {
    const resp = await m.request({url: "/todos"})
    state.todos = resp.todos
}


const todoList = () => m("",
    m("ul", state.todos.map((todo, i) =>
        m("li",
            todo.message,
            m("input", {type: "checkbox", checked: todo.done, onclick: () => toggle(i)}))
    )),
    m("form", {onsubmit: add},
        m("input", {value: state.new, oninput: updateNew, placeholder: "message"}),
        m("button", "add todo"),
    )
)


const toggle = async (i) => {
    state.todos[i].done = !state.todos[i].done
    put()
}

const updateNew = (e) => {
    state.new = e.target.value
}

const add = async (e) => {
    e.preventDefault()
    state.todos.push({message: state.new, done: false})
    state.new = ""
    put()
}

window.onload = async () => {
    get()
    const todoListEl = document.getElementById("todo-list")
    m.mount(todoListEl, {view: todoList})
}
