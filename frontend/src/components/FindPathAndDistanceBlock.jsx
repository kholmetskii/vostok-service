import { useMemo, useState } from "react";
import PropTypes from "prop-types";
import { getPathAndDistance, downloadAllShelfDistancesJsonl } from "../services/graphService.js";


function FindPathAndDistanceBlock({ warehouseId, shelves, setPath }) {
    const styles = {
        container: {
            padding: "1rem",
            border: "1px solid #ccc",
            borderRadius: "8px",
            backgroundColor: "#f9f9f9",
            fontSize: "0.9rem",
        },
        inlineRow: {
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "0.5rem",
        },
        inlineLabel: {
            fontWeight: "bold",
        },
        select: {
            flex: 1,
            padding: "0.25rem",
            borderRadius: "4px",
            border: "1px solid #ccc",
        },
        button: {
            padding: "0.4rem 0.75rem",
            border: "1px solid #ccc",
            borderRadius: "4px",
            cursor: "pointer",
        },
        distanceField: {
            flex: 1,
            padding: "0.4rem",
            borderRadius: "4px",
            border: "1px solid #ccc",
            backgroundColor: "#eee",
        },
    };

    const [fromShelfExtId, setFromShelfExtId] = useState("");
    const [toShelfExtId, setToShelfExtId] = useState("");
    const [distance, setDistance] = useState("");
    const [loading, setLoading] = useState(false);

    const options = useMemo(() => {
        return (shelves || []).map((s) => ({
            value: String(s.ext_id),
            label: `${s.shelving_code ?? "S"}:${s.section_code ?? s.ext_id} (ext ${s.ext_id})`,
        }));
    }, [shelves]);

    const canSubmit =
        !loading &&
        warehouseId != null &&
        fromShelfExtId !== "" &&
        toShelfExtId !== "" &&
        fromShelfExtId !== toShelfExtId;

    const handleFind = async () => {
        if (!canSubmit) return;

        setLoading(true);
        try {
            const data = await getPathAndDistance(
                warehouseId,
                Number(fromShelfExtId),
                Number(toShelfExtId)
            );

            // Новый формат ответа:
            // { distance_m: float, path_edges: EdgeOut[] }
            setPath(data.path_edges || []);
            setDistance(
                typeof data.distance_m === "number" ? data.distance_m.toFixed(3) : ""
            );
        } catch (e) {
            // минимально: чистим путь и дистанцию
            setPath([]);
            setDistance("");
            // при желании можно вывести alert или текст ошибки
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    async function handleDownloadJsonl() {
        try {
            const blob = await downloadAllShelfDistancesJsonl(warehouseId);
            const url = window.URL.createObjectURL(blob);

            const a = document.createElement("a");
            a.href = url;
            a.download = `warehouse_${warehouseId}_shelf_distances.jsonl`;
            document.body.appendChild(a);
            a.click();
            a.remove();

            window.URL.revokeObjectURL(url);
        } catch (e) {
            console.error(e);
        }
    }

    return (
        <div style={styles.container}>
            <div style={styles.inlineRow}>
                <span style={styles.inlineLabel}>From:</span>
                <select
                    style={styles.select}
                    value={fromShelfExtId}
                    onChange={(e) => setFromShelfExtId(e.target.value)}
                >
                    <option value="">Select shelf</option>
                    {options.map((o) => (
                        <option key={o.value} value={o.value}>
                            {o.label}
                        </option>
                    ))}
                </select>
            </div>

            <div style={styles.inlineRow}>
                <span style={styles.inlineLabel}>To:</span>
                <select
                    style={styles.select}
                    value={toShelfExtId}
                    onChange={(e) => setToShelfExtId(e.target.value)}
                >
                    <option value="">Select shelf</option>
                    {options.map((o) => (
                        <option key={o.value} value={o.value}>
                            {o.label}
                        </option>
                    ))}
                </select>
            </div>

            <div style={styles.inlineRow}>
                <button style={styles.button} onClick={handleFind} disabled={!canSubmit}>
                    {loading ? "..." : "Find"}
                </button>

                <input
                    style={styles.distanceField}
                    readOnly
                    value={distance}
                    placeholder="Distance (m)"
                />
            </div>
            <button style={styles.button} onClick={handleDownloadJsonl}>
                Download JSONL
            </button>
        </div>
    );
}

FindPathAndDistanceBlock.propTypes = {
    warehouseId: PropTypes.number.isRequired,
    shelves: PropTypes.arrayOf(
        PropTypes.shape({
            ext_id: PropTypes.number.isRequired,
            shelving_code: PropTypes.string,
            section_code: PropTypes.string,
        })
    ).isRequired,
    setPath: PropTypes.func.isRequired,
};

export default FindPathAndDistanceBlock;