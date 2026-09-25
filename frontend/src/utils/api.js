import axios from "axios";

export default axios.create({
    // A relative URL lets the development or Docker proxy serve the API.
    baseURL: "/api",
});
