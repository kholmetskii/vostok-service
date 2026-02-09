import { useState, useEffect, useMemo, useCallback } from "react";
import { getWarehouseConfig } from "../services/warehouseConfigService.js";

export function useWarehouseData(warehouseId) {
    const [warehouse, setWarehouse] = useState(null);
    const [shelves, setShelves] = useState([]);
    const [nodes, setNodes] = useState([]);
    const [edges, setEdges] = useState([]);
    const [obstacles, setObstacles] = useState([]);

    // 1-based level (Level 1..N)
    const [selectedLevel, setSelectedLevel] = useState(1);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const floors = useMemo(() => {
        const count = warehouse?.floor_count ?? 0;
        return Array.from({ length: count }, (_, i) => i + 1);
    }, [warehouse?.floor_count]);

    const clampLevel = useCallback((lvl, count) => {
        if (!count || count <= 0) return 1;
        if (lvl < 1) return 1;
        if (lvl > count) return count;
        return lvl;
    }, []);

    const loadAllData = useCallback(async () => {
        if (!warehouseId) return;

        setLoading(true);
        setError(null);

        try {
            const cfg = await getWarehouseConfig(warehouseId);

            setWarehouse(cfg.warehouse);
            setShelves(cfg.shelves);
            setNodes(cfg.nodes);
            setEdges(cfg.edges);
            setObstacles(cfg.obstacles);

            const count = cfg.warehouse?.floors_count ?? 0;
            setSelectedLevel((prev) => clampLevel(prev, count));
        } catch (err) {
            setError(err);
        } finally {
            setLoading(false);
        }
    }, [warehouseId, clampLevel]);

    useEffect(() => {
        loadAllData();
    }, [loadAllData]);

    return {
        warehouse,
        floors, // [1,2,3,...]
        shelves,
        nodes,
        edges,
        obstacles,
        selectedLevel,
        setSelectedLevel,
        loading,
        error,
        refresh: loadAllData,
    };
}
