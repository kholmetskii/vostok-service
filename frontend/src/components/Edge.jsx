import { Line } from "react-konva";
import PropTypes from "prop-types";

function Edge({ edge, scale, padding, stroke = "gray", dash, onClick }) {
    const points = [
        padding + edge.fromX * scale,
        padding + edge.fromY * scale,
        padding + edge.toX * scale,
        padding + edge.toY * scale,
    ];

    return (
        <Line
            points={points}
            stroke={stroke}
            strokeWidth={2}
            dash={dash}
            onClick={onClick}
        />
    );
}

Edge.propTypes = {
    edge: PropTypes.shape({
        fromX: PropTypes.number.isRequired,
        fromY: PropTypes.number.isRequired,
        toX: PropTypes.number.isRequired,
        toY: PropTypes.number.isRequired,
        id: PropTypes.number,
    }).isRequired,
    scale: PropTypes.number,
    padding: PropTypes.number,
    stroke: PropTypes.string,
    dash: PropTypes.arrayOf(PropTypes.number),
    onClick: PropTypes.func,
};

export default Edge;
