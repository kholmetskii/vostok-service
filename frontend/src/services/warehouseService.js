import api from "../utils/api.js";

export async function getWarehouses() {
    const res = await api.get("/warehouses");
    return res.data;
}

export async function createWarehouse({ name, width_m, length_m, floor_count }) {
    const res = await api.post("/warehouses", {
        name: String(name).trim(),
        width_m: Number(width_m),
        length_m: Number(length_m),
        floor_count: Number(floor_count),
    });
    return res.data;
}
