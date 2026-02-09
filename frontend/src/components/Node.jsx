import { Circle } from "react-konva";
import PropTypes from "prop-types";

function Node({ node, scale, padding, onClick }) {
    const posX = padding + node.x * scale;
    const posY = padding + node.y * scale;

    return (
        <Circle
            x={posX}
            y={posY}
            radius={2}
            fill="blue"
            stroke="black"
            strokeWidth={1}
            onClick={onClick}
        />
    );
}

Node.propTypes = {
    node: PropTypes.shape({
        id: PropTypes.number.isRequired,
        x: PropTypes.number.isRequired,
        y: PropTypes.number.isRequired,
        floor_id: PropTypes.number,
        warehouse_id: PropTypes.number,
    }).isRequired,
    scale: PropTypes.number,
    padding: PropTypes.number,
    onClick: PropTypes.func,
};

export default Node;
