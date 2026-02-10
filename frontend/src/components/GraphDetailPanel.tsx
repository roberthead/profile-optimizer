import React from 'react';
import { Link } from 'react-router-dom';
import {
  X,
  User,
  Briefcase,
  Building,
  Tag,
  ArrowRight,
  Link as LinkIcon,
  Sparkles,
  Layers,
  Lightbulb,
  Network,
  Zap,
} from 'lucide-react';

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
}

interface GraphEdge {
  id: number;
  source: number;
  target: number;
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

interface GraphDetailPanelProps {
  selectedNode: GraphNode | null;
  selectedEdge: GraphEdge | null;
  nodes: GraphNode[];
  patterns: GraphPattern[];
  onClose: () => void;
}

const edgeTypeLabels: Record<string, string> = {
  shared_skill: 'Shared Skill',
  shared_interest: 'Shared Interest',
  collaboration_potential: 'Collaboration Potential',
  event_co_attendance: 'Event Co-attendance',
  introduced_by_agent: 'Introduced by Agent',
  pattern_connection: 'Pattern Connection',
};

const edgeTypeColors: Record<string, string> = {
  shared_skill: 'bg-blue-500',
  shared_interest: 'bg-green-500',
  collaboration_potential: 'bg-orange-500',
  event_co_attendance: 'bg-cyan-500',
  introduced_by_agent: 'bg-pink-500',
  pattern_connection: 'bg-purple-500',
};

const categoryIcons: Record<string, React.FC<{ className?: string }>> = {
  skill_cluster: Layers,
  interest_theme: Lightbulb,
  collaboration_opportunity: Network,
  community_strength: Zap,
  cross_domain: Sparkles,
};

function getMembershipBadgeColor(status: string): string {
  switch (status) {
    case 'active_create':
      return 'bg-green-500/20 text-green-300 border-green-500/30';
    case 'active_fellow':
      return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    case 'active_team_member':
      return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
    case 'free':
      return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
    default:
      return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
  }
}

function formatMembershipStatus(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export const GraphDetailPanel: React.FC<GraphDetailPanelProps> = ({
  selectedNode,
  selectedEdge,
  nodes,
  patterns,
  onClose,
}) => {
  const isOpen = selectedNode !== null || selectedEdge !== null;

  if (!isOpen) return null;

  // Get node by ID helper
  const getNodeById = (id: number) => nodes.find((n) => n.id === id);

  // Get patterns for a node
  const getNodePatterns = (patternIds: number[]) =>
    patterns.filter((p) => patternIds.includes(p.id));

  return (
    <div
      className={`fixed top-0 right-0 h-full w-96 bg-slate-900 border-l border-slate-700 shadow-2xl transform transition-transform duration-300 z-50 overflow-y-auto ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      {/* Header */}
      <div className="sticky top-0 bg-slate-900/95 backdrop-blur border-b border-slate-700 p-4 flex items-center justify-between z-10">
        <h2 className="text-lg font-semibold text-white">
          {selectedNode ? 'Member Details' : 'Connection Details'}
        </h2>
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {selectedNode && (
          <>
            {/* Member Header */}
            <div className="flex items-start gap-4">
              {selectedNode.photo_url ? (
                <img
                  src={selectedNode.photo_url}
                  alt={selectedNode.name}
                  className="w-16 h-16 rounded-full object-cover border-2 border-slate-600"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center border-2 border-slate-600">
                  <User className="w-8 h-8 text-white" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-bold text-white truncate">
                  {selectedNode.name}
                </h3>
                {selectedNode.role && (
                  <p className="text-slate-300 flex items-center gap-1 mt-1">
                    <Briefcase className="w-4 h-4 text-slate-400" />
                    {selectedNode.role}
                  </p>
                )}
                {selectedNode.company && (
                  <p className="text-slate-400 flex items-center gap-1 text-sm">
                    <Building className="w-4 h-4" />
                    {selectedNode.company}
                  </p>
                )}
              </div>
            </div>

            {/* Status Badge */}
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getMembershipBadgeColor(
                selectedNode.membership_status
              )}`}
            >
              {formatMembershipStatus(selectedNode.membership_status)}
            </span>

            {/* Bio */}
            {selectedNode.bio && (
              <div>
                <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">
                  Bio
                </h4>
                <p className="text-slate-300 text-sm leading-relaxed">
                  {selectedNode.bio.length > 200
                    ? `${selectedNode.bio.substring(0, 200)}...`
                    : selectedNode.bio}
                </p>
              </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-800 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-indigo-400">
                  {selectedNode.connection_count}
                </p>
                <p className="text-xs text-slate-400">Connections</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-purple-400">
                  {selectedNode.pattern_ids.length}
                </p>
                <p className="text-xs text-slate-400">Patterns</p>
              </div>
            </div>

            {/* Skills */}
            {selectedNode.skills.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Briefcase className="w-4 h-4" />
                  Skills
                </h4>
                <div className="flex flex-wrap gap-2">
                  {selectedNode.skills.slice(0, 8).map((skill, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30"
                    >
                      {skill}
                    </span>
                  ))}
                  {selectedNode.skills.length > 8 && (
                    <span className="text-xs text-slate-500">
                      +{selectedNode.skills.length - 8} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Interests */}
            {selectedNode.interests.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Tag className="w-4 h-4" />
                  Interests
                </h4>
                <div className="flex flex-wrap gap-2">
                  {selectedNode.interests.slice(0, 8).map((interest, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-500/20 text-green-300 border border-green-500/30"
                    >
                      {interest}
                    </span>
                  ))}
                  {selectedNode.interests.length > 8 && (
                    <span className="text-xs text-slate-500">
                      +{selectedNode.interests.length - 8} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Patterns */}
            {selectedNode.pattern_ids.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Sparkles className="w-4 h-4" />
                  Community Patterns
                </h4>
                <div className="space-y-2">
                  {getNodePatterns(selectedNode.pattern_ids)
                    .slice(0, 5)
                    .map((pattern) => {
                      const Icon = categoryIcons[pattern.category] || Sparkles;
                      return (
                        <div
                          key={pattern.id}
                          className="flex items-center gap-2 p-2 rounded-lg bg-slate-800"
                        >
                          <div
                            className="w-2 h-2 rounded-full flex-shrink-0"
                            style={{ backgroundColor: pattern.color }}
                          />
                          <Icon className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          <span className="text-sm text-slate-300 truncate">
                            {pattern.name}
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}

            {/* View Profile Link */}
            <Link
              to={`/members/${selectedNode.id}`}
              className="flex items-center justify-center gap-2 w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
            >
              View Full Profile
              <ArrowRight className="w-4 h-4" />
            </Link>
          </>
        )}

        {selectedEdge && (
          <>
            {/* Edge Header */}
            <div className="text-center">
              <div
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${
                  edgeTypeColors[selectedEdge.type] || 'bg-gray-500'
                } bg-opacity-20 text-white`}
              >
                <div
                  className={`w-3 h-3 rounded-full ${
                    edgeTypeColors[selectedEdge.type] || 'bg-gray-500'
                  }`}
                />
                {edgeTypeLabels[selectedEdge.type] || selectedEdge.type}
              </div>
            </div>

            {/* Connected Members */}
            <div className="space-y-4">
              {[selectedEdge.source, selectedEdge.target].map((nodeId, index) => {
                const node = getNodeById(nodeId);
                if (!node) return null;
                return (
                  <div
                    key={nodeId}
                    className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg"
                  >
                    {node.photo_url ? (
                      <img
                        src={node.photo_url}
                        alt={node.name}
                        className="w-12 h-12 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                        <User className="w-6 h-6 text-white" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white truncate">
                        {node.name}
                      </p>
                      {node.role && (
                        <p className="text-sm text-slate-400 truncate">
                          {node.role}
                        </p>
                      )}
                    </div>
                    {index === 0 && (
                      <LinkIcon className="w-5 h-5 text-slate-500" />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Strength Indicator */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-slate-400">
                  Connection Strength
                </h4>
                <span className="text-lg font-bold text-white">
                  {selectedEdge.strength}%
                </span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${
                    edgeTypeColors[selectedEdge.type] || 'bg-gray-500'
                  } transition-all duration-300`}
                  style={{ width: `${selectedEdge.strength}%` }}
                />
              </div>
            </div>

            {/* Discovery Info */}
            <div className="bg-slate-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-2">
                How Discovered
              </h4>
              <p className="text-slate-300 capitalize">
                {selectedEdge.discovered_via.replace(/_/g, ' ')}
              </p>
            </div>

            {/* Evidence */}
            {selectedEdge.evidence &&
              Object.keys(selectedEdge.evidence).length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">
                    Evidence
                  </h4>
                  <div className="bg-slate-800 rounded-lg p-3 space-y-2">
                    {Object.entries(selectedEdge.evidence).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-xs text-slate-500 capitalize">
                          {key.replace(/_/g, ' ')}:
                        </span>
                        <p className="text-sm text-slate-300">
                          {Array.isArray(value)
                            ? value.join(', ')
                            : String(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </>
        )}
      </div>
    </div>
  );
};
