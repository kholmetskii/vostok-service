import PropTypes from "prop-types";

function FloorSelector({ floors, selectedLevel, setSelectedLevel }) {
    const styles = {
        container: {
            marginBottom: "0.5rem",
            padding: "1rem",
            border: "1px solid #ccc",
            borderRadius: "6px",
            backgroundColor: "#f9f9f9",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.9rem",
        },
        label: {
            fontWeight: "bold",
            whiteSpace: "nowrap",
        },
        select: {
            flex: 1,
            padding: "0.25rem 0.5rem",
            borderRadius: "4px",
            border: "1px solid #ccc",
        },
    };

    return (
        <div style={styles.container}>
            <label htmlFor="floor-select" style={styles.label}>
                Floor:
            </label>

            <select
                id="floor-select"
                value={Number.isInteger(selectedLevel) ? selectedLevel : 0}
                onChange={(e) => setSelectedLevel(Number(e.target.value))}
                style={styles.select}
                disabled={floors.length === 0}
            >
                {floors.map((level) => (
                    <option key={level} value={level}>
                        Level {level}
                    </option>
                ))}
            </select>
        </div>
    );
}

FloorSelector.propTypes = {
    floors: PropTypes.arrayOf(PropTypes.number).isRequired,
    selectedLevel: PropTypes.number.isRequired,
    setSelectedLevel: PropTypes.func.isRequired,
};

export default FloorSelector;
