export const a = [1, 2, 100, 200].map((v, i) => ({"myV": v, "myI": i})).filter((v, i) => (v.myI === 2 ? false : true))
const foo = {"bar": {"3": 4}}
export const b = Object.entries(foo.bar).map(([k, v], i) => ({"k": k, "v": v, "i": i}))
export const c = Object.fromEntries([["5", 6], ["7", 8]])
export const d = [1, 2, 3].includes(3)
export const e = [1, 2, 3].includes(5)
