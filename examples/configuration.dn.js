import { environments } from "./global.dn.js"

// names of the services to deploy
const serviceNames = ["signup", "account"]

const makeService = (environment, serviceName) => ({
    name: serviceName,
    ip: environment === environments.PROD ? "189.34.0.4" : "127.0.0.1"
})

export default (environment) => serviceNames.map(
    (v, i) => makeService(environment, v)
)
