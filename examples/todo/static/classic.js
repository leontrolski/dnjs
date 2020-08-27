import { Todo } from "../shared/components.dn.js"

const todoListFormEl = document.getElementById("todoListForm")
const todoListUlEl = document.getElementById("todoListUl")
const newMessageEl = document.getElementById("newMessage")
const doneCheckboxEls = document.getElementsByClassName("doneCheckbox")

const addToggleOnclicks = () => {
    for (const [i, el] of Object.entries(doneCheckboxEls)){
        el.onclick = () => fetch(`/classic/todos/${i}/toggle`, {method: 'PUT'})
    }
}
todoListFormEl.onsubmit = async e => {
    e.preventDefault()
    if (!newMessageEl.value) return
    const data = {message: newMessageEl.value, done: false}
    await fetch("/classic/todos", {method: 'POST', body: JSON.stringify(data)})
    const newTodo = Todo(data, null)
    todoListUlEl.appendChild(m.makeEl(newTodo))
    newMessageEl.value = ""
    addToggleOnclicks()
}
addToggleOnclicks()
