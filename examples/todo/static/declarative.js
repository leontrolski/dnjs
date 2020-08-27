import { TodoList } from "../shared/components.dn.js"

const state = {
    todos: [],
    new: "",
}

// Server sync methods
const put = async () => {
    m.request({url: "/declarative/todos", method: "PUT", body: {todos: state.todos}})
}
const get = async () => {
    const resp = await m.request({url: "/declarative/todos"})
    state.todos = resp.todos
}

// Actions
const toggle = async (i) => {
    state.todos[i].done = !state.todos[i].done
    put()
}
const updateNew = (e) => {
    state.new = e.target.value
}
const add = async (e) => {
    e.preventDefault()
    if (!state.new) return
    state.todos.push({message: state.new, done: false})
    state.new = ""
    put()
}
const actions = {
    toggle,
    updateNew,
    add,
}

window.onload = async () => {
    get()
    const todoListEl = document.getElementById("todo-list")
    m.mount(todoListEl, {view: () => TodoList(state, actions)})
}
