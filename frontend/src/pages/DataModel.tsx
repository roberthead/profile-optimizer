import React, { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Database,
  RefreshCw,
  Users,
  GitBranch,
  Heart,
  Layers,
  HelpCircle,
  Send,
  Zap,
  MessageSquare,
  X,
  ArrowRight,
  Activity,
} from 'lucide-react';

interface TableInfo {
  name: string;
  count: number;
  sample: Record<string, unknown> | null;
}

interface Relationship {
  from_table: string;
  to_table: string;
  type: string;
}

interface ModelStatsResponse {
  tables: TableInfo[];
  relationships: Relationship[];
}

interface ActivityItem {
  type: string;
  description: string;
  timestamp: string;
}

interface ActivityFeedResponse {
  activities: ActivityItem[];
}

const API_BASE = 'http://localhost:8000/api/v1';

async function fetchModelStats(): Promise<ModelStatsResponse> {
  const response = await fetch(`${API_BASE}/stats/model`);
  if (!response.ok) throw new Error('Failed to fetch model stats');
  return response.json();
}

async function fetchActivityFeed(): Promise<ActivityFeedResponse> {
  const response = await fetch(`${API_BASE}/stats/activity?limit=20`);
  if (!response.ok) throw new Error('Failed to fetch activity feed');
  return response.json();
}

// Table metadata for visualization
const tableConfig: Record<string, {
  icon: React.FC<{ className?: string }>;
  color: string;
  bgColor: string;
  borderColor: string;
  displayName: string;
  position: { row: number; col: number };
}> = {
  members: {
    icon: Users,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    displayName: 'Members',
    position: { row: 0, col: 0 },
  },
  member_edges: {
    icon: GitBranch,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    displayName: 'Edges',
    position: { row: 0, col: 1 },
  },
  patterns: {
    icon: Layers,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    displayName: 'Patterns',
    position: { row: 0, col: 2 },
  },
  taste_profiles: {
    icon: Heart,
    color: 'text-pink-600',
    bgColor: 'bg-pink-50',
    borderColor: 'border-pink-200',
    displayName: 'Taste Profiles',
    position: { row: 1, col: 0 },
  },
  questions: {
    icon: HelpCircle,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    displayName: 'Questions',
    position: { row: 1, col: 1 },
  },
  question_deliveries: {
    icon: Send,
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    borderColor: 'border-cyan-200',
    displayName: 'Deliveries',
    position: { row: 1, col: 2 },
  },
  event_signals: {
    icon: Zap,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    displayName: 'Event Signals',
    position: { row: 2, col: 0 },
  },
  question_responses: {
    icon: MessageSquare,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    borderColor: 'border-indigo-200',
    displayName: 'Responses',
    position: { row: 2, col: 2 },
  },
};

// Activity type icons and colors
const activityTypeConfig: Record<string, {
  icon: React.FC<{ className?: string }>;
  color: string;
  bgColor: string;
}> = {
  edge_discovered: {
    icon: GitBranch,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
  },
  question_answered: {
    icon: MessageSquare,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100',
  },
  pattern_updated: {
    icon: Layers,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
  },
  taste_evolved: {
    icon: Heart,
    color: 'text-pink-600',
    bgColor: 'bg-pink-100',
  },
};

interface TableCardProps {
  table: TableInfo;
  onClick: () => void;
}

const TableCard: React.FC<TableCardProps> = ({ table, onClick }) => {
  const config = tableConfig[table.name] || {
    icon: Database,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    displayName: table.name,
    position: { row: 0, col: 0 },
  };

  const Icon = config.icon;

  const formatCount = (count: number): string => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`;
    }
    return count.toLocaleString();
  };

  return (
    <button
      onClick={onClick}
      className={`
        group relative p-4 rounded-xl border-2 ${config.borderColor} ${config.bgColor}
        hover:shadow-lg hover:scale-105 transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500
        min-w-[140px]
      `}
    >
      <div className="flex flex-col items-center gap-2">
        <div className={`p-2 rounded-lg bg-white shadow-sm ${config.color}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div className="text-center">
          <div className="font-semibold text-gray-900 text-sm">
            {config.displayName}
          </div>
          <div className={`text-2xl font-bold ${config.color}`}>
            {formatCount(table.count)}
          </div>
        </div>
      </div>
      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity bg-white/50 flex items-center justify-center">
        <span className="text-sm font-medium text-gray-700">View Sample</span>
      </div>
    </button>
  );
};

interface SampleModalProps {
  table: TableInfo;
  onClose: () => void;
}

const SampleModal: React.FC<SampleModalProps> = ({ table, onClose }) => {
  const config = tableConfig[table.name] || {
    icon: Database,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    displayName: table.name,
    position: { row: 0, col: 0 },
  };

  const Icon = config.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        <div className={`p-4 ${config.bgColor} border-b ${config.borderColor} flex items-center justify-between`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg bg-white shadow-sm ${config.color}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900">{config.displayName}</h2>
              <p className="text-sm text-gray-600">{table.count.toLocaleString()} records</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/50 transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        <div className="p-4 overflow-auto max-h-[60vh]">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Sample Record</h3>
          {table.sample ? (
            <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-sm overflow-auto">
              <code>{JSON.stringify(table.sample, null, 2)}</code>
            </pre>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Database className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p>No sample data available</p>
            </div>
          )}

          {table.sample && (
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Schema Fields</h3>
              <div className="flex flex-wrap gap-2">
                {Object.keys(table.sample).map((field) => (
                  <span
                    key={field}
                    className="px-2 py-1 bg-gray-100 rounded text-sm text-gray-700 font-mono"
                  >
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface RelationshipLineProps {
  from: string;
  to: string;
  type: string;
}

const RelationshipLine: React.FC<RelationshipLineProps> = ({ from, to, type }) => {
  const fromConfig = tableConfig[from];
  const toConfig = tableConfig[to];

  if (!fromConfig || !toConfig) return null;

  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <span className={`font-medium ${fromConfig.color}`}>
        {fromConfig.displayName}
      </span>
      <ArrowRight className="w-3 h-3" />
      <span className={`font-medium ${toConfig.color}`}>
        {toConfig.displayName}
      </span>
      <span className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600">
        {type}
      </span>
    </div>
  );
};

interface ActivityItemProps {
  activity: ActivityItem;
}

const ActivityItemCard: React.FC<ActivityItemProps> = ({ activity }) => {
  const config = activityTypeConfig[activity.type] || {
    icon: Activity,
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
  };

  const Icon = config.icon;

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
      <div className={`p-1.5 rounded-lg ${config.bgColor}`}>
        <Icon className={`w-4 h-4 ${config.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-700 truncate">{activity.description}</p>
        <p className="text-xs text-gray-400 mt-0.5">
          {formatTimestamp(activity.timestamp)}
        </p>
      </div>
    </div>
  );
};

export const DataModel: React.FC = () => {
  const [selectedTable, setSelectedTable] = useState<TableInfo | null>(null);

  const {
    data: modelStats,
    isLoading: isLoadingModel,
    refetch: refetchModel,
    isFetching: isFetchingModel,
  } = useQuery({
    queryKey: ['modelStats'],
    queryFn: fetchModelStats,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000,
  });

  const {
    data: activityFeed,
    isLoading: isLoadingActivity,
    refetch: refetchActivity,
  } = useQuery({
    queryKey: ['activityFeed'],
    queryFn: fetchActivityFeed,
    staleTime: 30 * 1000, // 30 seconds (activity updates frequently)
    refetchInterval: 30000, // Poll every 30 seconds
  });

  const handleRefresh = useCallback(() => {
    refetchModel();
    refetchActivity();
  }, [refetchModel, refetchActivity]);

  // Organize tables by position for the grid layout
  const tablesByPosition = modelStats?.tables.reduce((acc, table) => {
    const config = tableConfig[table.name];
    if (config) {
      const key = `${config.position.row}-${config.position.col}`;
      acc[key] = table;
    }
    return acc;
  }, {} as Record<string, TableInfo>) || {};

  const rows = [0, 1, 2];
  const cols = [0, 1, 2];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Database className="w-7 h-7 text-indigo-600" />
            Data Model Explorer
          </h1>
          <p className="text-gray-600 mt-1">
            Explore the community data structure and recent activity
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isFetchingModel}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isFetchingModel ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Entity Diagram */}
        <div className="lg:col-span-3 bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">
            Entity Relationship Diagram
          </h2>

          {isLoadingModel ? (
            <div className="flex items-center justify-center py-20">
              <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
            </div>
          ) : (
            <>
              {/* Table Grid */}
              <div className="space-y-6 mb-8">
                {rows.map((row) => (
                  <div key={row} className="flex justify-center gap-8">
                    {cols.map((col) => {
                      const table = tablesByPosition[`${row}-${col}`];
                      if (!table) {
                        return <div key={`${row}-${col}`} className="min-w-[140px]" />;
                      }
                      return (
                        <TableCard
                          key={table.name}
                          table={table}
                          onClick={() => setSelectedTable(table)}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>

              {/* Relationships */}
              <div className="border-t border-gray-100 pt-6">
                <h3 className="text-sm font-medium text-gray-700 mb-4">
                  Relationships
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {modelStats?.relationships.map((rel, idx) => (
                    <RelationshipLine
                      key={idx}
                      from={rel.from_table}
                      to={rel.to_table}
                      type={rel.type}
                    />
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Activity Feed */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-600" />
              Activity Feed
            </h2>
            <p className="text-xs text-gray-500 mt-1">Updates every 30s</p>
          </div>

          <div className="max-h-[600px] overflow-y-auto">
            {isLoadingActivity ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
              </div>
            ) : activityFeed?.activities && activityFeed.activities.length > 0 ? (
              <div className="divide-y divide-gray-50">
                {activityFeed.activities.map((activity, idx) => (
                  <ActivityItemCard key={idx} activity={activity} />
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <Activity className="w-12 h-12 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No recent activity</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      {modelStats && (
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-2xl p-6 border border-indigo-100">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">Data Summary</h3>
              <p className="text-sm text-gray-600 mt-1">
                Total of {modelStats.tables.reduce((sum, t) => sum + t.count, 0).toLocaleString()} records
                across {modelStats.tables.length} tables
              </p>
            </div>
            <div className="flex gap-6">
              {modelStats.tables.slice(0, 4).map((table) => {
                const config = tableConfig[table.name];
                if (!config) return null;
                const Icon = config.icon;
                return (
                  <div key={table.name} className="text-center">
                    <div className={`inline-flex p-2 rounded-lg bg-white shadow-sm ${config.color} mb-1`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="text-xs text-gray-600">{config.displayName}</div>
                    <div className={`text-lg font-bold ${config.color}`}>
                      {table.count.toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Sample Data Modal */}
      {selectedTable && (
        <SampleModal
          table={selectedTable}
          onClose={() => setSelectedTable(null)}
        />
      )}
    </div>
  );
};
