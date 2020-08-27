const todoListFormEl = document.getElementById("todoListForm")
const doneCheckboxEls = document.getElementsByClassName("doneCheckbox")
for (const el of doneCheckboxEls){
    el.onclick = () => todoListFormEl.submit()
}
