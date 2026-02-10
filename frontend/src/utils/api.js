import axios from "axios";

export default axios.create({
    // Важно: относительный URL => уйдёт на тот же хост/порт, где открыт фронт.
    // Пример: http://192.168.171.154:8080/api
    baseURL: "/api",
});