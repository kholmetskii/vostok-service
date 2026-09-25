import { Link, useNavigate } from "react-router-dom";
import api from "../utils/api";

function Topbar({ warehouse }) {
    const navigate = useNavigate();

    if (!warehouse) return null;

    const handleDelete = async () => {
        const ok = window.confirm(
            `Delete warehouse "${warehouse.name}" (id=${warehouse.id})? This action cannot be undone.`
        );
        if (!ok) return;

        try {
            await api.delete(`/warehouses/${warehouse.id}`);
            navigate("/warehouse");
        } catch (e) {
            console.error(e);
            const msg = e?.response?.data?.detail || "Failed to delete warehouse";
            alert(msg);
        }
    };

    return (
        <div style={styles.topbar}>
            <div>
                <h1 style={styles.title}>
                    {warehouse.name}
                </h1>
            </div>

            <div style={styles.actions}>
                <button style={styles.deleteButton} onClick={handleDelete}>
                    Delete
                </button>
                <Link to="/warehouse" style={styles.link}>
                    ← Back to Warehouse List
                </Link>
            </div>
        </div>
    );
}

const styles = {
    topbar: {
        backgroundColor: "#f5f5f5",
        padding: "10px 20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        border: "1px solid #ccc",
    },
    title: {
        margin: 0,
        fontSize: "1.5rem",
    },
    sub: {
        fontSize: "1rem",
        fontWeight: "normal",
    },
    actions: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
    },
    link: {
        color: "orange",
        textDecoration: "none",
        fontSize: "1rem",
    },
    deleteButton: {
        padding: "0.4rem 0.75rem",
        border: "1px solid #ccc",
        borderRadius: "4px",
        cursor: "pointer",
        backgroundColor: "#ffdddd",
        color: "#a40000",
        fontSize: "1rem",
    },
};

export default Topbar;
