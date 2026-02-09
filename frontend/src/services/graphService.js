import api from '../utils/api';

export async function getPathAndDistance(warehouseId, fromShelfExtId, toShelfExtId) {
    const res = await api.post(`/warehouses/${warehouseId}/distance`, {
        from_shelf_ext_id: fromShelfExtId,
        to_shelf_ext_id: toShelfExtId,
    });
    return res.data;
}


export async function downloadAllShelfDistancesJsonl(warehouseId) {
    const res = await api.get(`/warehouses/${warehouseId}/shelves/distances.jsonl`, {
        responseType: "blob",
    });
    return res.data; // Blob
}

