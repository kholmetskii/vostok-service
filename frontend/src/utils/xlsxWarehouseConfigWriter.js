import * as XLSX from "xlsx";

function ensureArray(v) {
    return Array.isArray(v) ? v : [];
}

/**
 * Builds an XLSX workbook with 4 sheets:
 * - nodes
 * - shelves
 * - edges
 * - obstacles
 *
 * Each sheet is created from JSON array of objects.
 */
export function buildWarehouseConfigWorkbook(config) {
    const wb = XLSX.utils.book_new();

    const nodes = ensureArray(config?.nodes);
    const shelves = ensureArray(config?.shelves);
    const edges = ensureArray(config?.edges);
    const obstacles = ensureArray(config?.obstacles);

    // For empty arrays, json_to_sheet([]) makes an empty sheet (fine).
    const wsNodes = XLSX.utils.json_to_sheet(nodes);
    const wsShelves = XLSX.utils.json_to_sheet(shelves);
    const wsEdges = XLSX.utils.json_to_sheet(edges);
    const wsObstacles = XLSX.utils.json_to_sheet(obstacles);

    XLSX.utils.book_append_sheet(wb, wsNodes, "nodes");
    XLSX.utils.book_append_sheet(wb, wsShelves, "shelves");
    XLSX.utils.book_append_sheet(wb, wsEdges, "edges");
    XLSX.utils.book_append_sheet(wb, wsObstacles, "obstacles");

    return wb;
}

/**
 * Converts workbook -> Blob (xlsx)
 */
export function workbookToXlsxBlob(workbook) {
    const arrayBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
    return new Blob([arrayBuffer], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
}

/**
 * Triggers a browser download for the blob.
 */
export function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}
