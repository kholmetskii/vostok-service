import { useState } from "react";
import PropTypes from "prop-types";
import { parseWarehouseConfigXlsx } from "../utils/xlsxWarehouseConfigParser.js";
import { getWarehouseConfig, putWarehouseConfig } from "../services/warehouseConfigService.js";
import {
    buildWarehouseConfigWorkbook,
    workbookToXlsxBlob,
    downloadBlob,
} from "../utils/xlsxWarehouseConfigWriter.js";

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

    try {
        return JSON.stringify(detail);
    } catch {
        return "Request failed";
    }
}

export default function WarehouseConfigUploadBlock({ warehouseId, onSuccess }) {
    const [file, setFile] = useState(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");

    const onPick = (e) => {
        setError("");
        setFile(e.target.files?.[0] ?? null);
    };

    const onUpload = async () => {
        if (!warehouseId) return;
        if (!file) return setError("Please choose an .xlsx file");

        setBusy(true);
        setError("");

        try {
            const cfg = await parseWarehouseConfigXlsx(file);
            await putWarehouseConfig(warehouseId, cfg);
            onSuccess?.();
            setFile(null);
        } catch (err) {
            setError(formatFastApiDetail(err?.response?.data?.detail) || err.message || "Upload failed");
        } finally {
            setBusy(false);
        }
    };

    const onDownload = async () => {
        if (!warehouseId) return;

        setBusy(true);
        setError("");

        try {
            const cfg = await getWarehouseConfig(warehouseId);
            const wb = buildWarehouseConfigWorkbook(cfg);
            const blob = workbookToXlsxBlob(wb);
            downloadBlob(blob, `warehouse_${warehouseId}_config.xlsx`);
        } catch (err) {
            setError(formatFastApiDetail(err?.response?.data?.detail) || err.message || "Download failed");
        } finally {
            setBusy(false);
        }
    };

    return (
        <div style={{ marginTop: 16, padding: 12, border: "1px solid #ccc", borderRadius: 8 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Warehouse Config (.xlsx)</div>

            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <input type="file" accept=".xlsx" onChange={onPick} />

                <button type="button" onClick={onUpload} disabled={busy || !file}>
                    {busy ? "Working..." : "Upload & Apply"}
                </button>

                <button type="button" onClick={onDownload} disabled={busy}>
                    {busy ? "Working..." : "Download XLSX"}
                </button>
            </div>

            {error && (
                <pre style={{ color: "red", marginTop: 8, whiteSpace: "pre-wrap" }}>
          {error}
        </pre>
            )}
        </div>
    );
}

WarehouseConfigUploadBlock.propTypes = {
    warehouseId: PropTypes.number.isRequired,
    onSuccess: PropTypes.func,
};
