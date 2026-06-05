"use client";

import { useEffect, useState, useRef } from "react";
import { fetchAPI } from "@/lib/api";

interface GraphData {
  nodes: { id: string; name: string; type: string; mentions: number }[];
  edges: { source: string; target: string; relationship_type: string; weight: number }[];
  total_nodes: number;
  total_edges: number;
}

const TYPE_COLORS: Record<string, string> = {
  startup: "#3b82f6",
  investor: "#22c55e",
  technology: "#a855f7",
  person: "#f59e0b",
  region: "#06b6d4",
  market: "#ec4899",
  product: "#f97316",
  industry: "#8b5cf6",
};

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [entityName, setEntityName] = useState("Stripe");
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const updateSize = () => {
      if (svgRef.current?.parentElement) {
        const rect = svgRef.current.parentElement.getBoundingClientRect();
        setDimensions({ width: rect.width, height: Math.max(500, rect.height - 40) });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const d = await fetchAPI<GraphData>(
          `/api/entities/${encodeURIComponent(entityName)}/connections?depth=2&limit=50`
        );
        setData(d);
        setSelectedNode(null);
      } catch {
        // graceful degradation
      }
    }
    if (entityName) load();
  }, [entityName]);

  // Simple force-directed layout (no D3 server component — pure SVG)
  const nodePositions = useRef<Map<string, { x: number; y: number }>>(new Map());

  useEffect(() => {
    if (!data || data.nodes.length === 0) return;

    const cx = dimensions.width / 2;
    const cy = dimensions.height / 2;
    const radius = Math.min(cx, cy) * 0.7;

    // Simple circular layout with entity type clustering
    const typeGroups = new Map<string, number[]>();
    data.nodes.forEach((node, i) => {
      const type = node.type;
      if (!typeGroups.has(type)) typeGroups.set(type, []);
      typeGroups.get(type)!.push(i);
    });

    const groupAngleStep = (2 * Math.PI) / typeGroups.size;
    let groupAngle = 0;

    typeGroups.forEach((indices) => {
      const angleStart = groupAngle;
      const angleStep = indices.length > 1 ? (groupAngleStep / (indices.length + 1)) : 0;
      indices.forEach((nodeIdx, i) => {
        const angle = angleStart + angleStep * (i + 1);
        const r = indices[0] === 0 ? 0 : radius * (0.4 + 0.3 * Math.random());
        nodePositions.current.set(String(data.nodes[nodeIdx].id), {
          x: cx + r * Math.cos(angle),
          y: cy + r * Math.sin(angle),
        });
      });
      groupAngle += groupAngleStep;
    });
  }, [data, dimensions]);

  return (
    <div className="space-y-4 h-full">
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={entityName}
          onChange={(e) => setEntityName(e.target.value)}
          placeholder="Search entity (e.g., Stripe, OpenAI)"
          className="bg-surface-card border border-zinc-800 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-600 outline-none flex-1 max-w-sm"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              const d = fetchAPI<GraphData>(
                `/api/entities/${encodeURIComponent(e.currentTarget.value)}/connections?depth=2&limit=50`
              );
              d.then(setData);
            }
          }}
        />
      </div>

      {data && data.nodes.length > 0 ? (
        <div className="relative bg-surface-card border border-zinc-800 rounded-lg overflow-hidden">
          <svg
            ref={svgRef}
            width={dimensions.width}
            height={dimensions.height}
            viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
            className="w-full"
          >
            {/* Edges */}
            {data.edges.map((edge, i) => {
              const source = nodePositions.current.get(String(edge.source));
              const target = nodePositions.current.get(String(edge.target));
              if (!source || !target) return null;
              return (
                <line
                  key={i}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="#3f3f46"
                  strokeWidth={Math.max(1, (edge.weight || 1) * 2)}
                  strokeOpacity={0.6}
                />
              );
            })}

            {/* Nodes */}
            {data.nodes.map((node) => {
              const pos = nodePositions.current.get(String(node.id));
              if (!pos) return null;
              const isSelected = selectedNode === String(node.id);
              const color = TYPE_COLORS[node.type] || "#71717a";
              const radius = Math.max(6, Math.min(20, 6 + (node.mentions || 1) * 0.5));

              return (
                <g
                  key={node.id}
                  onClick={() => setSelectedNode(String(node.id))}
                  className="cursor-pointer"
                >
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={radius}
                    fill={color}
                    fillOpacity={isSelected ? 1 : 0.7}
                    stroke={isSelected ? "#fff" : color}
                    strokeWidth={isSelected ? 2 : 1}
                  />
                  <text
                    x={pos.x}
                    y={pos.y + radius + 12}
                    textAnchor="middle"
                    className="text-[9px] fill-zinc-400 select-none"
                  >
                    {node.name}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Legend */}
          <div className="absolute bottom-3 left-3 flex flex-wrap gap-2">
            {Object.entries(TYPE_COLORS).map(([type, color]) => (
              <span key={type} className="flex items-center gap-1 text-[10px] text-zinc-500">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                {type}
              </span>
            ))}
          </div>

          {/* Stats */}
          <div className="absolute top-3 right-3 text-[10px] text-zinc-600 font-mono">
            {data.total_nodes} nodes · {data.total_edges} edges
          </div>
        </div>
      ) : (
        <div className="bg-surface-card border border-zinc-800 rounded-lg flex items-center justify-center h-96 text-zinc-600 text-sm">
          Enter an entity name to explore its connections
        </div>
      )}
    </div>
  );
}
