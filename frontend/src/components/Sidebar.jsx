import PropTypes from "prop-types";
import FloorSelector from "./FloorSelector.jsx";
import FindPathAndDistanceBlock from "./FindPathAndDistanceBlock.jsx";
import TogglesBlock from "./TogglesBlock.jsx";
import WarehouseConfigUploadBlock from "./WarehouseConfigUploadBlock.jsx";


function Sidebar({
                     warehouse,
                     floors,
                     shelves,
                     selectedLevel,
                     setSelectedLevel,
                     setPath,
                     showNodes,
                     showEdges,
                     setShowNodes,
                     setShowEdges,
                     refreshData,
                 }) {
    const sidebarStyle = {
        display: "flex",
        flexDirection: "column",
        width: "300px",
        padding: "16px",
        backgroundColor: "#f5f5f5",
        border: "1px solid #ccc",
        overflowY: "auto",
        boxSizing: "border-box",
    };

    return (
        <div style={sidebarStyle}>
            <FloorSelector
                floors={floors}
                selectedLevel={selectedLevel}
                setSelectedLevel={setSelectedLevel}
            />

            <FindPathAndDistanceBlock
                warehouseId={warehouse.id}
                shelves={shelves}
                setPath={setPath}
            />

            <TogglesBlock
                showNodes={showNodes}
                showEdges={showEdges}
                setShowNodes={setShowNodes}
                setShowEdges={setShowEdges}
            />

            <WarehouseConfigUploadBlock
                warehouseId={warehouse.id}
                onSuccess={refreshData}
            />

        </div>
    );
}

Sidebar.propTypes = {
    warehouse: PropTypes.object.isRequired,
    floors: PropTypes.arrayOf(PropTypes.number).isRequired,
    shelves: PropTypes.array.isRequired,
    selectedLevel: PropTypes.number.isRequired,
    setSelectedLevel: PropTypes.func.isRequired,
    setPath: PropTypes.func.isRequired,
    showNodes: PropTypes.bool.isRequired,
    showEdges: PropTypes.bool.isRequired,
    setShowNodes: PropTypes.func.isRequired,
    setShowEdges: PropTypes.func.isRequired,
    selectedItem: PropTypes.object,
    setSelectedItem: PropTypes.func.isRequired,
    refreshData: PropTypes.func.isRequired,
};

export default Sidebar;
