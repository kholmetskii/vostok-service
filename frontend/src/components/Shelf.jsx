import { Rect, Text } from "react-konva";
import PropTypes from "prop-types";

function Shelf({ shelf, scale, padding, onClick }) {
    const scaledX = padding + shelf.x * scale;
    const scaledY = padding + shelf.y * scale;
    const scaledWidth = shelf.width * scale;
    const scaledHeight = shelf.length * scale;
    const label = `${shelf.shelving_code}:${shelf.section_code}`;

    return (
        <>
            <Rect
                x={scaledX}
                y={scaledY}
                width={scaledWidth}
                height={scaledHeight}
                fill="orange"
                stroke="black"
                strokeWidth={1}
                onClick={onClick}
            />
            <Text
                x={scaledX}
                y={scaledY + scaledHeight / 2}
                width={scaledWidth}
                height={16}
                offsetY={8}
                text={label}
                align="center"
                verticalAlign="middle"
                fontSize={8}
                fill="black"
                onClick={onClick}
            />
        </>
    );
}

Shelf.propTypes = {
    shelf: PropTypes.shape({
        x: PropTypes.number.isRequired,
        y: PropTypes.number.isRequired,
        width: PropTypes.number.isRequired,
        length: PropTypes.number.isRequired,
        shelving_code: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
        section_code: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    }).isRequired,
    scale: PropTypes.number.isRequired,
    padding: PropTypes.number.isRequired,
    onClick: PropTypes.func,
};

export default Shelf;
