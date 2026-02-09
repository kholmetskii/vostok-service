import { Stage, Layer, Rect } from "react-konva";
import PropTypes from "prop-types";
import Shelf from "./Shelf.jsx";
import Edge from "./Edge.jsx";
import Node from "./Node.jsx";
import Obstacle from "./Obstacle.jsx";

function WarehouseMap({
                          warehouse,
                          shelves,
                          selectedLevel,
                          path,
                          nodes,
                          edges,
                          obstacles,
                          showNodes,
                          showEdges,
                          setSelectedItem,
                      }) {
    const SCALE = 30;
    const PADDING = 0;

    if (!warehouse) return <p>Loading warehouse...</p>;

    // Support both: {width,length} and {width_m,length_m}
    const whWidth = Number(warehouse.width_m ?? warehouse.width ?? 0);
    const whLength = Number(warehouse.length_m ?? warehouse.length ?? 0);

    const stageWidth = whWidth * SCALE + PADDING * 2;
    const stageHeight = whLength * SCALE + PADDING * 2;

    // ---------- Normalizers ----------
    const nodeKey = (n) => n?.ext_id ?? n?.id;
    const nodeX = (n) => Number(n?.x_m ?? n?.x ?? 0);
    const nodeY = (n) => Number(n?.y_m ?? n?.y ?? 0);

    const edgeKey = (e) => e?.ext_id ?? e?.id;
    const edgeFrom = (e) => e?.from_node_ext_id ?? e?.from_node_id;
    const edgeTo = (e) => e?.to_node_ext_id ?? e?.to_node_id;

    const shelfKey = (s) => s?.ext_id ?? s?.id;
    const shelfX = (s) => Number(s?.x_m ?? s?.x ?? 0);
    const shelfY = (s) => Number(s?.y_m ?? s?.y ?? 0);
    const shelfW = (s) => Number(s?.width_m ?? s?.width ?? 0);
    const shelfL = (s) => Number(s?.length_m ?? s?.length ?? 0);

    const obstacleKey = (o) => o?.ext_id ?? o?.id;
    const obstacleFrom = (o) => o?.from_node_ext_id ?? o?.from_node_id;
    const obstacleTo = (o) => o?.to_node_ext_id ?? o?.to_node_id;


    // Build nodesById using ext_id (new) or id (old)
    const nodesById = new Map((nodes ?? []).map((n) => [nodeKey(n), n]));


    const isEdgeVisibleOnLevel = (edge, level) => {
        const from = nodesById.get(edgeFrom(edge));
        const to = nodesById.get(edgeTo(edge));
        return !!from && !!to && (from.floor_level === level || to.floor_level === level);
    };

    const isCrossFloor = (edge) => {
        const from = nodesById.get(edgeFrom(edge));
        const to = nodesById.get(edgeTo(edge));
        return !!from && !!to && from.floor_level !== to.floor_level;
    };

    return (
        <div>
            <Stage width={stageWidth} height={stageHeight}>
                <Layer>
                    {/* Warehouse outline */}
                    <Rect
                        x={0}
                        y={0}
                        width={whWidth * SCALE}
                        height={whLength * SCALE}
                        fill="#f0f0f0"
                        stroke="#999"
                        strokeWidth={2}
                    />

                    {/* Shelves */}
                    {(shelves ?? [])
                        .filter((s) => s.floor_level === selectedLevel)
                        .map((s) => {
                            // normalize shelf shape for whatever Shelf.jsx expects
                            const shelfForRender = {
                                ...s,
                                id: shelfKey(s),
                                x: shelfX(s),
                                y: shelfY(s),
                                width: shelfW(s),
                                length: shelfL(s),
                            };

                            return (
                                <Shelf
                                    key={`shelf-${shelfForRender.id}`}
                                    shelf={shelfForRender}
                                    scale={SCALE}
                                    padding={PADDING}
                                    onClick={() => setSelectedItem({ type: "shelf", data: s })}
                                />
                            );
                        })}

                    {/* Edges */}
                    {showEdges &&
                        (edges ?? [])
                            .filter((e) => isEdgeVisibleOnLevel(e, selectedLevel))
                            .map((e) => {
                                const from = nodesById.get(edgeFrom(e));
                                const to = nodesById.get(edgeTo(e));
                                if (!from || !to) return null;

                                const edgeForRender = {
                                    ...e,
                                    id: edgeKey(e),
                                    fromX: nodeX(from),
                                    fromY: nodeY(from),
                                    toX: nodeX(to),
                                    toY: nodeY(to),
                                };

                                return (
                                    <Edge
                                        key={`edge-${edgeForRender.id}`}
                                        edge={edgeForRender}
                                        scale={SCALE}
                                        padding={PADDING}
                                        dash={isCrossFloor(e) ? [8, 4] : undefined}
                                        onClick={() => setSelectedItem({ type: "edge", data: e })}
                                    />
                                );
                            })}

                    {/* Path edges (optional) */}
                    {(path ?? [])
                        .filter((e) => isEdgeVisibleOnLevel(e, selectedLevel))
                        .map((e) => {
                            const from = nodesById.get(edgeFrom(e));
                            const to = nodesById.get(edgeTo(e));
                            if (!from || !to) return null;

                            const pathEdgeForRender = {
                                ...e,
                                id: edgeKey(e),
                                fromX: nodeX(from),
                                fromY: nodeY(from),
                                toX: nodeX(to),
                                toY: nodeY(to),
                            };

                            return (
                                <Edge
                                    key={`path-${pathEdgeForRender.id}`}
                                    edge={pathEdgeForRender}
                                    scale={SCALE}
                                    padding={PADDING}
                                    stroke="red"
                                    dash={isCrossFloor(e) ? [8, 4] : undefined}
                                />
                            );
                        })}

                    {/* Obstacles */}
                    {(obstacles ?? [])
                        .filter((o) => {
                            // If obstacle has floor_level -> use it; else infer from its endpoint nodes
                            if (o.floor_level != null) return o.floor_level === selectedLevel;

                            const a = nodesById.get(obstacleFrom(o));
                            const b = nodesById.get(obstacleTo(o));
                            const floor = a?.floor_level ?? b?.floor_level;
                            return floor === selectedLevel;
                        })
                        .map((o) => {
                            const a = nodesById.get(obstacleFrom(o));
                            const b = nodesById.get(obstacleTo(o));

                            // normalize obstacle shape for whatever Obstacle.jsx expects
                            // supports both:
                            //  - explicit (x1,y1,x2,y2) or (x1_m,y1_m,x2_m,y2_m)
                            //  - node endpoints (from/to) => we compute coordinates
                            const obstacleForRender = {
                                ...o,
                                id: obstacleKey(o),
                                floor_level:
                                    o.floor_level ??
                                    a?.floor_level ??
                                    b?.floor_level ??
                                    selectedLevel,
                                x1: Number(o.x1_m ?? o.x1 ?? (a ? nodeX(a) : 0)),
                                y1: Number(o.y1_m ?? o.y1 ?? (a ? nodeY(a) : 0)),
                                x2: Number(o.x2_m ?? o.x2 ?? (b ? nodeX(b) : 0)),
                                y2: Number(o.y2_m ?? o.y2 ?? (b ? nodeY(b) : 0)),
                            };

                            return (
                                <Obstacle
                                    key={`obstacle-${obstacleForRender.id}`}
                                    obstacle={obstacleForRender}
                                    scale={SCALE}
                                    onClick={() => setSelectedItem({ type: "obstacle", data: o })}
                                />
                            );
                        })}

                    {/* Nodes */}
                    {showNodes &&
                        (nodes ?? [])
                            .filter((n) => n.floor_level === selectedLevel)
                            .map((n) => {
                                const nodeForRender = {
                                    ...n,
                                    id: nodeKey(n),
                                    x: nodeX(n),
                                    y: nodeY(n),
                                };

                                return (
                                    <Node
                                        key={`node-${nodeForRender.id}`}
                                        node={nodeForRender}
                                        scale={SCALE}
                                        padding={PADDING}
                                        onClick={() => setSelectedItem({ type: "node", data: n })}
                                    />
                                );
                            })}
                </Layer>
            </Stage>
        </div>
    );
}

WarehouseMap.propTypes = {
    warehouse: PropTypes.object,
    shelves: PropTypes.array.isRequired,
    selectedLevel: PropTypes.number.isRequired,
    path: PropTypes.array,
    nodes: PropTypes.array.isRequired,
    edges: PropTypes.array.isRequired,
    obstacles: PropTypes.array.isRequired,
    showNodes: PropTypes.bool.isRequired,
    showEdges: PropTypes.bool.isRequired,
    setSelectedItem: PropTypes.func.isRequired,
};

export default WarehouseMap;
