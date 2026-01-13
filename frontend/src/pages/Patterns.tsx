import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Users,
  Lightbulb,
  HelpCircle,
  Network,
  Layers,
  Zap,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Pattern {
  id: number;
  name: string;
  description: string;
  category: string;
  member_count: number;
  related_member_ids: number[];
  evidence: Record<string, unknown> | null;
  question_prompts: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface PatternDiscoveryResponse {
  success: boolean;
  patterns_found: number;
  patterns: Array<{ id: number; name: string; created: boolean }>;
  response_text: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

async function fetchPatterns(): Promise<Pattern[]> {
  const response = await fetch(`${API_BASE}/patterns`);
  if (!response.ok) throw new Error('Failed to fetch patterns');
  return response.json();
}

async function discoverPatterns(): Promise<PatternDiscoveryResponse> {
  const response = await fetch(`${API_BASE}/patterns/discover`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to discover patterns');
  return response.json();
}

async function refreshPatterns(): Promise<PatternDiscoveryResponse> {
  const response = await fetch(`${API_BASE}/patterns/refresh`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to refresh patterns');
  return response.json();
}

const categoryColors: Record<string, string> = {
  skill_cluster: 'bg-blue-100 text-blue-800',
  interest_theme: 'bg-purple-100 text-purple-800',
  collaboration_opportunity: 'bg-green-100 text-green-800',
  community_strength: 'bg-orange-100 text-orange-800',
  cross_domain: 'bg-pink-100 text-pink-800',
};

const categoryLabels: Record<string, string> = {
  skill_cluster: 'Skill Cluster',
  interest_theme: 'Interest Theme',
  collaboration_opportunity: 'Collaboration',
  community_strength: 'Community Strength',
  cross_domain: 'Cross-Domain',
};

const categoryIcons: Record<string, React.FC<{ className?: string }>> = {
  skill_cluster: Layers,
  interest_theme: Lightbulb,
  collaboration_opportunity: Network,
  community_strength: Zap,
  cross_domain: Sparkles,
};

const PatternCard: React.FC<{ pattern: Pattern }> = ({ pattern }) => {
  const [expanded, setExpanded] = useState(false);
  const Icon = categoryIcons[pattern.category] || Sparkles;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                  categoryColors[pattern.category] || 'bg-gray-100 text-gray-800'
                }`}
              >
                <Icon className="w-3 h-3" />
                {categoryLabels[pattern.category] || pattern.category}
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                <Users className="w-3 h-3" />
                {pattern.member_count} members
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">{pattern.name}</h3>
            <p className="text-sm text-gray-600 mt-1">{pattern.description}</p>
          </div>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-100">
          {pattern.evidence && Object.keys(pattern.evidence).length > 0 && (
            <div className="pt-4">
              <div className="text-sm font-medium text-gray-700 mb-2">Evidence</div>
              <div className="bg-gray-50 rounded-lg p-3 text-sm">
                {Object.entries(pattern.evidence).map(([key, value]) => (
                  <div key={key} className="mb-2 last:mb-0">
                    <span className="font-medium text-gray-600 capitalize">
                      {key.replace(/_/g, ' ')}:
                    </span>{' '}
                    <span className="text-gray-800">
                      {Array.isArray(value) ? value.join(', ') : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {pattern.question_prompts.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                <HelpCircle className="w-4 h-4" />
                Questions to Explore
              </div>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                {pattern.question_prompts.map((prompt, i) => (
                  <li key={i}>{prompt}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="text-xs text-gray-400">
            Discovered {new Date(pattern.created_at).toLocaleDateString()}
          </div>
        </div>
      )}
    </div>
  );
};

export const Patterns: React.FC = () => {
  const queryClient = useQueryClient();
  const [lastResponse, setLastResponse] = useState<string | null>(null);

  const { data: patterns, isLoading } = useQuery({
    queryKey: ['patterns'],
    queryFn: fetchPatterns,
  });

  const discoverMutation = useMutation({
    mutationFn: discoverPatterns,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['patterns'] });
      setLastResponse(data.response_text);
    },
  });

  const refreshMutation = useMutation({
    mutationFn: refreshPatterns,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['patterns'] });
      setLastResponse(data.response_text);
    },
  });

  const isProcessing = discoverMutation.isPending || refreshMutation.isPending;

  const categoryCounts = patterns?.reduce((acc, p) => {
    acc[p.category] = (acc[p.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="w-7 h-7 text-indigo-600" />
            Community Patterns
          </h1>
          <p className="text-gray-600 mt-1">
            Discover meaningful patterns in member skills, interests, and collaboration opportunities
          </p>
        </div>
        <div className="flex gap-2">
          {patterns && patterns.length > 0 && (
            <button
              onClick={() => refreshMutation.mutate()}
              disabled={isProcessing}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          )}
          <button
            onClick={() => discoverMutation.mutate()}
            disabled={isProcessing}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {discoverMutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Discovering...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Discover Patterns
              </>
            )}
          </button>
        </div>
      </div>

      {/* Last Response */}
      {lastResponse && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
            <div className="prose prose-sm max-w-none text-indigo-900">
              <ReactMarkdown>{lastResponse}</ReactMarkdown>
            </div>
          </div>
          <button
            onClick={() => setLastResponse(null)}
            className="mt-2 text-sm text-indigo-600 hover:text-indigo-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Category Summary */}
      {categoryCounts && Object.keys(categoryCounts).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(categoryCounts).map(([cat, count]) => {
            const Icon = categoryIcons[cat] || Sparkles;
            return (
              <span
                key={cat}
                className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                  categoryColors[cat] || 'bg-gray-100 text-gray-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                {categoryLabels[cat] || cat}: {count}
              </span>
            );
          })}
        </div>
      )}

      {/* Patterns List */}
      {isLoading ? (
        <div className="text-center py-12">
          <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading patterns...</p>
        </div>
      ) : patterns && patterns.length > 0 ? (
        <div className="space-y-4">
          {patterns.map((pattern) => (
            <PatternCard key={pattern.id} pattern={pattern} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Sparkles className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No patterns discovered yet</h3>
          <p className="text-gray-600 mb-4">
            Click "Discover Patterns" to analyze your community and find meaningful connections.
          </p>
          <button
            onClick={() => discoverMutation.mutate()}
            disabled={isProcessing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Discover Patterns
          </button>
        </div>
      )}
    </div>
  );
};
