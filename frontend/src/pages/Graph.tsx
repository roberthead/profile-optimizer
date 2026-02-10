import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import ForceGraph2D from 'react-force-graph-2d';
import {
  Network,
  Filter,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Info,
} from 'lucide-react';
import { GraphDetailPanel } from '../components/GraphDetailPanel';

// Types
interface GraphNode {
  id: number;
  name: string;
  photo_url: string | null;
  pattern_ids: number[];
  connection_count: number;
  skills: string[];
  interests: string[];
  role: string | null;
  company: string | null;
  bio: string | null;
  membership_status: string;
  // Force graph internal properties
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface GraphEdge {
  id: number;
  source: number | GraphNode;
  target: number | GraphNode;
  type: string;
  strength: number;
  evidence: Record<string, unknown> | null;
  discovered_via: string;
}

interface GraphPattern {
  id: number;
  name: string;
  description: string;
  color: string;
  member_ids: number[];
  category: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  patterns: GraphPattern[];
}

const API_BASE = 'http://localhost:8000/api/v1';

// Edge type styling configuration
const EDGE_TYPE_COLORS: Record<string, string> = {
  shared_skill: '#3b82f6',      // blue
  shared_interest: '#22c55e',    // green
  collaboration_potential: '#f97316', // orange
  event_co_attendance: '#06b6d4', // cyan
  introduced_by_agent: '#ec4899', // pink
  pattern_connection: '#a855f7',  // purple
};

const EDGE_TYPE_LABELS: Record<string, string> = {
  shared_skill: 'Shared Skill',
  shared_interest: 'Shared Interest',
  collaboration_potential: 'Collaboration Potential',
  event_co_attendance: 'Event Co-attendance',
  introduced_by_agent: 'Introduced by Agent',
  pattern_connection: 'Pattern Connection',
};

// Pattern category colors for node coloring
const PATTERN_CATEGORY_COLORS: Record<string, string> = {
  skill_cluster: '#3b82f6',
  interest_theme: '#a855f7',
  collaboration_opportunity: '#22c55e',
  community_strength: '#f97316',
  cross_domain: '#ec4899',
};

async function fetchGraphData(
  patternId: number | null,
  edgeTypes: string[]
): Promise<GraphData> {
  const params = new URLSearchParams();
  if (patternId) {
    params.set('pattern_id', patternId.toString());
  }
  edgeTypes.forEach((et) => params.append('edge_types', et));

  const response = await fetch(`${API_BASE}/graph/data?${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch graph data');
  }
  return response.json();
}

export const Graph: React.FC = () => {
  const graphRef = useRef<any>();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Filter state
  const [selectedPattern, setSelectedPattern] = useState<number | null>(null);
  const [enabledEdgeTypes, setEnabledEdgeTypes] = useState<string[]>(
    Object.keys(EDGE_TYPE_COLORS)
  );

  // Selection state
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);

  // Fetch graph data - cache for 10 minutes since it's expensive
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['graph', selectedPattern, enabledEdgeTypes],
    queryFn: () => fetchGraphData(selectedPattern, enabledEdgeTypes),
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });

  // Handle container resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        // Account for panel width when open
        const panelWidth = selectedNode || selectedEdge ? 384 : 0;
        setDimensions({
          width: rect.width - panelWidth,
          height: rect.height,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, [selectedNode, selectedEdge]);

  // Toggle edge type filter
  const toggleEdgeType = (type: string) => {
    setEnabledEdgeTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  // Get node color based on primary pattern
  const getNodeColor = useCallback(
    (node: GraphNode) => {
      if (!data?.patterns || node.pattern_ids.length === 0) {
        return '#6b7280'; // gray for no pattern
      }
      const primaryPattern = data.patterns.find(
        (p) => p.id === node.pattern_ids[0]
      );
      if (primaryPattern) {
        return (
          PATTERN_CATEGORY_COLORS[primaryPattern.category] || primaryPattern.color
        );
      }
      return '#6b7280';
    },
    [data?.patterns]
  );

  // Get node size based on connection count
  const getNodeSize = useCallback((node: GraphNode) => {
    const baseSize = 6;
    const scaleFactor = Math.sqrt(node.connection_count + 1);
    return baseSize + scaleFactor * 2;
  }, []);

  // Handle node click
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
    setSelectedEdge(null);
  }, []);

  // Handle edge click
  const handleLinkClick = useCallback((link: GraphEdge) => {
    setSelectedEdge(link);
    setSelectedNode(null);
  }, []);

  // Close detail panel
  const handleClosePanel = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  // Zoom controls
  const handleZoomIn = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom * 1.5, 400);
    }
  };

  const handleZoomOut = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom / 1.5, 400);
    }
  };

  const handleZoomToFit = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 50);
    }
  };

  // Transform data for force-graph (links need source/target references)
  const graphData = data
    ? {
        nodes: data.nodes,
        links: data.edges.map((e) => ({
          ...e,
          source: e.source,
          target: e.target,
        })),
      }
    : { nodes: [], links: [] };

  // Custom node canvas drawing
  const drawNode = useCallback(
    (
      node: GraphNode,
      ctx: CanvasRenderingContext2D,
      globalScale: number
    ) => {
      const size = getNodeSize(node);
      const color = getNodeColor(node);
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;

      // Draw node circle
      ctx.beginPath();
      ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Draw border for selected/hovered
      if (isSelected || isHovered) {
        ctx.strokeStyle = isSelected ? '#ffffff' : 'rgba(255,255,255,0.6)';
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.stroke();
      }

      // Draw label at higher zoom
      if (globalScale > 1 || isHovered || isSelected) {
        const label = node.name;
        const fontSize = Math.max(10 / globalScale, 3);
        ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.fillText(label, node.x!, node.y! + size + 2);
      }
    },
    [getNodeColor, getNodeSize, selectedNode, hoveredNode]
  );

  // Custom link drawing
  const drawLink = useCallback(
    (
      link: GraphEdge,
      ctx: CanvasRenderingContext2D,
      _globalScale: number
    ) => {
      const source = link.source as GraphNode;
      const target = link.target as GraphNode;

      if (!source.x || !source.y || !target.x || !target.y) return;

      const color = EDGE_TYPE_COLORS[link.type] || '#6b7280';
      const isWeak = link.strength < 50;
      const isSelectedEdge =
        selectedEdge?.source === link.source &&
        selectedEdge?.target === link.target;

      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);

      // Style based on strength and selection
      ctx.strokeStyle = isSelectedEdge
        ? '#ffffff'
        : isWeak
        ? `${color}80`
        : color;
      ctx.lineWidth = isSelectedEdge
        ? 3
        : Math.max(1, (link.strength / 100) * 3);

      // Dashed for weak connections
      if (isWeak && !isSelectedEdge) {
        ctx.setLineDash([5, 5]);
      } else {
        ctx.setLineDash([]);
      }

      ctx.stroke();
      ctx.setLineDash([]);
    },
    [selectedEdge]
  );

  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-12rem)] bg-slate-900 rounded-xl">
        <div className="text-center text-red-400">
          <p className="text-lg font-medium">Failed to load graph data</p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Network className="w-7 h-7 text-indigo-600" />
            Community Graph
          </h1>
          <p className="text-gray-600">
            {data
              ? `${data.nodes.length} members, ${data.edges.length} connections`
              : 'Loading...'}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw
            className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
          />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Pattern Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <select
              value={selectedPattern || ''}
              onChange={(e) =>
                setSelectedPattern(e.target.value ? Number(e.target.value) : null)
              }
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            >
              <option value="">All Patterns</option>
              {data?.patterns.map((pattern) => (
                <option key={pattern.id} value={pattern.id}>
                  {pattern.name} ({pattern.member_ids.length} members)
                </option>
              ))}
            </select>
          </div>

          {/* Edge Type Filters */}
          <div className="flex-1 flex flex-wrap items-center gap-2">
            <span className="text-sm text-gray-500">Edge Types:</span>
            {Object.entries(EDGE_TYPE_LABELS).map(([type, label]) => (
              <button
                key={type}
                onClick={() => toggleEdgeType(type)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                  enabledEdgeTypes.includes(type)
                    ? 'bg-opacity-100 text-white'
                    : 'bg-gray-100 text-gray-400'
                }`}
                style={{
                  backgroundColor: enabledEdgeTypes.includes(type)
                    ? EDGE_TYPE_COLORS[type]
                    : undefined,
                }}
              >
                <div
                  className="w-2 h-2 rounded-full"
                  style={{
                    backgroundColor: EDGE_TYPE_COLORS[type],
                    opacity: enabledEdgeTypes.includes(type) ? 1 : 0.5,
                  }}
                />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Graph Container */}
      <div
        ref={containerRef}
        className="relative bg-slate-900 rounded-xl overflow-hidden"
        style={{ height: 'calc(100vh - 20rem)' }}
      >
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-4" />
              <p className="text-slate-400">Loading graph...</p>
            </div>
          </div>
        ) : data && data.nodes.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <Network className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 text-lg">No connections found</p>
              <p className="text-slate-500 text-sm mt-2">
                Discover patterns to build the community graph
              </p>
            </div>
          </div>
        ) : (
          <ForceGraph2D
            ref={graphRef}
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            nodeId="id"
            nodeCanvasObject={drawNode}
            nodePointerAreaPaint={(node, color, ctx) => {
              const size = getNodeSize(node as GraphNode);
              ctx.beginPath();
              ctx.arc(node.x!, node.y!, size + 2, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();
            }}
            linkCanvasObject={drawLink}
            linkPointerAreaPaint={(link, _color, ctx) => {
              const source = link.source as GraphNode;
              const target = link.target as GraphNode;
              if (!source.x || !target.x) return;
              ctx.beginPath();
              ctx.moveTo(source.x, source.y!);
              ctx.lineTo(target.x, target.y!);
              ctx.lineWidth = 10;
              ctx.stroke();
            }}
            onNodeClick={handleNodeClick}
            onLinkClick={handleLinkClick}
            onNodeHover={(node) => setHoveredNode(node as GraphNode | null)}
            backgroundColor="#0f172a"
            linkDirectionalParticles={0}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            warmupTicks={100}
            cooldownTicks={100}
            enableZoomInteraction={true}
            enablePanInteraction={true}
          />
        )}

        {/* Zoom Controls */}
        <div className="absolute bottom-4 left-4 flex flex-col gap-2">
          <button
            onClick={handleZoomIn}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-5 h-5" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-5 h-5" />
          </button>
          <button
            onClick={handleZoomToFit}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
            title="Fit to View"
          >
            <Maximize2 className="w-5 h-5" />
          </button>
        </div>

        {/* Legend */}
        <div className="absolute top-4 left-4 bg-slate-800/90 backdrop-blur rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2 text-slate-300 text-sm">
            <Info className="w-4 h-4" />
            <span className="font-medium">Legend</span>
          </div>
          <div className="space-y-1 text-xs text-slate-400">
            <p>Node size = connection count</p>
            <p>Node color = primary pattern</p>
            <p>Dashed line = weak connection (&lt;50)</p>
          </div>
        </div>

        {/* Detail Panel */}
        <GraphDetailPanel
          selectedNode={selectedNode}
          selectedEdge={
            selectedEdge
              ? {
                  ...selectedEdge,
                  source:
                    typeof selectedEdge.source === 'object'
                      ? selectedEdge.source.id
                      : selectedEdge.source,
                  target:
                    typeof selectedEdge.target === 'object'
                      ? selectedEdge.target.id
                      : selectedEdge.target,
                }
              : null
          }
          nodes={data?.nodes || []}
          patterns={data?.patterns || []}
          onClose={handleClosePanel}
        />
      </div>

      {/* Stats Footer */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-2xl font-bold text-indigo-600">
              {data.nodes.length}
            </p>
            <p className="text-sm text-gray-500">Members</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-2xl font-bold text-green-600">
              {data.edges.length}
            </p>
            <p className="text-sm text-gray-500">Connections</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-2xl font-bold text-purple-600">
              {data.patterns.length}
            </p>
            <p className="text-sm text-gray-500">Patterns</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-2xl font-bold text-orange-600">
              {data.edges.length > 0
                ? Math.round(
                    data.edges.reduce((sum, e) => sum + e.strength, 0) /
                      data.edges.length
                  )
                : 0}
              %
            </p>
            <p className="text-sm text-gray-500">Avg Strength</p>
          </div>
        </div>
      )}
    </div>
  );
};
