import * as XLSX from "xlsx";

function normalizeHeader(h) {
    // "Floor Level" -> "floor_level", "width_m" stays "width_m"
    return String(h ?? "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "_");
}

function sheetToObjects(workbook, sheetName) {
    const ws = workbook.Sheets[sheetName];
    if (!ws) return [];

    // Read raw rows (first row = headers)
    const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: null });
    if (!rows.length) return [];

    const headers = (rows[0] ?? []).map(normalizeHeader);
    const dataRows = rows.slice(1);

    const objects = [];
    for (const row of dataRows) {
        // skip fully empty rows
        const allEmpty = !row || row.every((v) => v === null || v === "");
        if (allEmpty) continue;

        const obj = {};
        for (let i = 0; i < headers.length; i++) {
            const key = headers[i];
            if (!key) continue;
            obj[key] = row[i] ?? null;
        }
        objects.push(obj);
    }
    return objects;
}

/**
 * Expected sheet names (case-insensitive):
 * - nodes
 * - shelves
 * - edges
 * - obstacles
 *
 * If your XLSX uses other names, update the mapping here once.
 */
export async function parseWarehouseConfigXlsx(file) {
    const buf = await file.arrayBuffer();
    const workbook = XLSX.read(buf, { type: "array" });

    // Create a case-insensitive map for sheet lookup
    const sheetNameByLower = new Map(
        workbook.SheetNames.map((n) => [n.toLowerCase().trim(), n])
    );

    const nodesSheet = sheetNameByLower.get("nodes");
    const shelvesSheet = sheetNameByLower.get("shelves");
    const edgesSheet = sheetNameByLower.get("edges");
    const obstaclesSheet = sheetNameByLower.get("obstacles");

    const nodes = nodesSheet ? sheetToObjects(workbook, nodesSheet) : [];
    const shelves = shelvesSheet ? sheetToObjects(workbook, shelvesSheet) : [];
    const edges = edgesSheet ? sheetToObjects(workbook, edgesSheet) : [];
    const obstacles = obstaclesSheet ? sheetToObjects(workbook, obstaclesSheet) : [];

    // IMPORTANT:
    // Ensure keys match your backend DTO fields exactly (snake_case).
    // This parser normalizes headers to snake_case automatically.
    return { nodes, shelves, edges, obstacles };
}
