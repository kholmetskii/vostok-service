import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createWarehouse } from "../services/warehouseService.js";

function formatFastApiDetail(detail) {
    if (!detail) return "Request failed";

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
        return detail
            .map((e) => {
                const loc = Array.isArray(e.loc) ? e.loc.join(".") : "body";
                const msg = e.msg ?? "Invalid value";
                return `${loc}: ${msg}`;
            })
            .join("\n");
    }

    // fallback
    try {
        return JSON.stringify(detail);
    } catch {
        return "Request failed";
    }
}

function CreateWarehousePage() {
    const [name, setName] = useState("");
    const [width_m, setWidth] = useState("");
    const [length_m, setLength] = useState("");
    const [floor_count, setFloorsCount] = useState(1);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();

        const w = Number(width_m);
        const l = Number(length_m);
        const fc = Number(floor_count);

        if (!name.trim()) return setError("Name is required");
        if (!Number.isFinite(w) || w <= 0) return setError("Width must be > 0");
        if (!Number.isFinite(l) || l <= 0) return setError("Length must be > 0");
        if (!Number.isInteger(fc) || fc <= 0) return setError("Floors count must be an integer >= 1");

        setLoading(true);
        setError(null);

        try {
            const created = await createWarehouse({
                name,
                width_m: w,
                length_m: l,
                floor_count: fc,
            });

            navigate(`/warehouse/${created.id}`);
        } catch (err) {
            console.error(err);
            const detail = err?.response?.data?.detail;
            setError(formatFastApiDetail(detail));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h1>Create Warehouse</h1>

            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    placeholder="Warehouse name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                />

                <input
                    type="number"
                    placeholder="Width"
                    value={width_m}
                    min="0"
                    step="any"
                    onChange={(e) => setWidth(e.target.value)}
                />

                <input
                    type="number"
                    placeholder="Length"
                    value={length_m}
                    min="0"
                    step="any"
                    onChange={(e) => setLength(e.target.value)}
                />

                <input
                    type="number"
                    placeholder="Floors count"
                    value={floor_count}
                    min="1"
                    step="1"
                    onChange={(e) => setFloorsCount(e.target.value)}
                />

                <button type="submit" disabled={loading}>
                    {loading ? "Creating..." : "Create"}
                </button>
            </form>

            {error && (
                <pre style={{ color: "red", whiteSpace: "pre-wrap" }}>
          {error}
        </pre>
            )}
        </div>
    );
}

export default CreateWarehousePage;
