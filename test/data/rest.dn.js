// a comment
const foo = [42, 43]  // another comment
const bar = {"bar": foo}

export default {
    bar: "this-will-be-overridden",
    "key": ["item0", "item1", 3.14, ...foo, true, bar],
    ...bar,
}
