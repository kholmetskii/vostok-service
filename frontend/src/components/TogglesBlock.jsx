import PropTypes from "prop-types";

function TogglesBlock({ showNodes, showEdges, setShowNodes, setShowEdges }) {
    const containerStyle = {
        marginTop: "0.5rem",
        padding: "1rem",
        border: "1px solid #ccc",
        borderRadius: "6px",
        backgroundColor: "#f9f9f9",
        display: "flex",
        gap: "1rem",
        alignItems: "center",
        fontSize: "0.9rem"
    };

    return (
        <div style={containerStyle}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                <input
                    type="checkbox"
                    checked={showNodes}
                    onChange={() => setShowNodes(!showNodes)}
                />
                Nodes
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                <input
                    type="checkbox"
                    checked={showEdges}
                    onChange={() => setShowEdges(!showEdges)}
                />
                Edges
            </label>
        </div>
    );
}

TogglesBlock.propTypes = {
    showNodes: PropTypes.bool,
    showEdges: PropTypes.bool,
    setShowNodes: PropTypes.func.isRequired,
    setShowEdges: PropTypes.func.isRequired,
};

export default TogglesBlock;
