import { useParams } from "react-router-dom";
import { useWarehouseData } from "../hooks/useWarehouseData";
import WarehouseMap from "../components/WarehouseMap.jsx";
import Sidebar from "../components/Sidebar.jsx";
import { useState } from "react";
import TopbarComponent from "../components/Topbar.jsx";

function WarehousePage() {
    const { id } = useParams();
    const warehouseId = parseInt(id, 10);

    const {
        warehouse,
        floors,
        shelves,
        nodes,
        edges,
        obstacles,
        selectedLevel,
        setSelectedLevel,
        loading,
        error,
        refresh,
    } = useWarehouseData(warehouseId);

    const [path, setPath] = useState([]);
    const [showNodes, setShowNodes] = useState(false);
    const [showEdges, setShowEdges] = useState(false);
    const [selectedItem, setSelectedItem] = useState(null);

    if (loading) return <p>Loading warehouse data...</p>;
    if (error) return <p>Error loading data: {error.message}</p>;
    if (!warehouse) return <p>Warehouse not found.</p>;

    return (
        <div>
            <TopbarComponent warehouse={warehouse} />
            <div style={{ display: "flex" }}>
                <div style={{ flex: 1 }}>
                    <Sidebar
                        warehouse={warehouse}
                        floors={floors}
                        shelves={shelves}
                        selectedLevel={selectedLevel}
                        setSelectedLevel={setSelectedLevel}
                        setPath={setPath}
                        showNodes={showNodes}
                        showEdges={showEdges}
                        setShowNodes={setShowNodes}
                        setShowEdges={setShowEdges}
                        selectedItem={selectedItem}
                        setSelectedItem={setSelectedItem}
                        refreshData={refresh}
                    />
                </div>

                <div
                    style={{
                        flex: 5,
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                    }}
                >
                    <WarehouseMap
                        warehouse={warehouse}
                        shelves={shelves}
                        selectedLevel={selectedLevel}
                        path={path}
                        nodes={nodes}
                        edges={edges}
                        obstacles={obstacles}
                        showNodes={showNodes}
                        showEdges={showEdges}
                        setSelectedItem={setSelectedItem}
                    />
                </div>
            </div>
        </div>
    );
}

export default WarehousePage;
