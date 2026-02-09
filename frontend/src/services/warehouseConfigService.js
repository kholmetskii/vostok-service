import api from "../utils/api.js";

export async function getWarehouseConfig(warehouseId) {
  const res = await api.get(`/warehouses/${warehouseId}/config`);
  return res.data;
}

export async function putWarehouseConfig(warehouseId, configJson) {
  const res = await api.put(`/warehouses/${warehouseId}/config`, configJson);
  return res.data;
}
