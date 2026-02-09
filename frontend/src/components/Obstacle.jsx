import PropTypes from "prop-types";
import { Line } from "react-konva";

function Obstacle({ obstacle, scale, stroke = "orange", onClick }) {

    const { x1, y1, x2, y2 } = obstacle;

    return (
        <Line
            points={[x1 * scale, y1 * scale, x2 * scale, y2 * scale]}
            stroke={stroke}
            strokeWidth={3}
            onClick={onClick}
        />
    );
}

Obstacle.propTypes = {
    obstacle: PropTypes.shape({
        x1: PropTypes.number.isRequired,
        y1: PropTypes.number.isRequired,
        x2: PropTypes.number.isRequired,
        y2: PropTypes.number.isRequired,
        floor_id: PropTypes.number,
        warehouse_id: PropTypes.number,
    }),
    scale: PropTypes.number,
    stroke: PropTypes.string,
    onClick: PropTypes.func,
};

export default Obstacle;
