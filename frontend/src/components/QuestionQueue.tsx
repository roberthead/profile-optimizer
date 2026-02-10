import React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, ListOrdered, AlertCircle } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';

interface QueuedQuestionPattern {
  id: number;
  name: string;
  relationship: string;
  affinity?: number;
}

interface QueuedQuestion {
  position: number;
  question_id: number;
  question_text: string;
  type: string;
  category: string;
  difficulty: number;
  options: string[];
  blank_prompt: string | null;
  score: number;
  reason: string;
  reason_detail: string;
  related_patterns: QueuedQuestionPattern[];
}

interface ProfileGap {
  field: string;
  label: string;
}

interface HighAffinityPattern {
  id: number;
  name: string;
  affinity: number;
}

interface QueueScoringModel {
  total_available: number;
  already_answered: number;
  pattern_memberships: number;
  high_affinity_patterns: HighAffinityPattern[];
  profile_gaps: ProfileGap[];
}

interface QuestionQueueData {
  member_id: number;
  member_name: string;
  queue: QueuedQuestion[];
  scoring_summary: QueueScoringModel;
}

async function fetchQueue(memberId: number): Promise<QuestionQueueData> {
  const response = await fetch(`${API_BASE}/questions/queue/${memberId}`);
  if (!response.ok) throw new Error('Failed to fetch question queue');
  return response.json();
}

const categoryColors: Record<string, string> = {
  origin_story: 'bg-purple-100 text-purple-800',
  creative_spark: 'bg-orange-100 text-orange-800',
  collaboration: 'bg-blue-100 text-blue-800',
  future_vision: 'bg-green-100 text-green-800',
  community_connection: 'bg-pink-100 text-pink-800',
  hidden_depths: 'bg-indigo-100 text-indigo-800',
  impact_legacy: 'bg-amber-100 text-amber-800',
};

const categoryLabels: Record<string, string> = {
  origin_story: 'Origin Story',
  creative_spark: 'Creative Spark',
  collaboration: 'Collaboration',
  future_vision: 'Future Vision',
  community_connection: 'Community',
  hidden_depths: 'Hidden Depths',
  impact_legacy: 'Impact',
};

const questionTypeColors: Record<string, string> = {
  free_form: 'bg-slate-100 text-slate-700',
  multiple_choice: 'bg-cyan-100 text-cyan-800',
  yes_no: 'bg-emerald-100 text-emerald-800',
  fill_in_blank: 'bg-violet-100 text-violet-800',
};

const questionTypeLabels: Record<string, string> = {
  free_form: 'Free Form',
  multiple_choice: 'Multiple Choice',
  yes_no: 'Yes/No',
  fill_in_blank: 'Fill in Blank',
};

const reasonColors: Record<string, string> = {
  pattern_probe: 'bg-amber-100 text-amber-800 border-amber-300',
  pattern_deepen: 'bg-blue-100 text-blue-800 border-blue-300',
  profile_gap: 'bg-green-100 text-green-800 border-green-300',
  fallback: 'bg-gray-100 text-gray-700 border-gray-300',
  minimum: 'bg-gray-100 text-gray-500 border-gray-200',
};

const reasonLabels: Record<string, string> = {
  pattern_probe: 'Pattern Probe',
  pattern_deepen: 'Pattern Deepen',
  profile_gap: 'Profile Gap',
  fallback: 'Fallback',
  minimum: 'Base',
};

const difficultyLabels = ['Easy', 'Medium', 'Deep'];
const difficultyColors = [
  'bg-green-100 text-green-800',
  'bg-yellow-100 text-yellow-800',
  'bg-red-100 text-red-800',
];

export const QuestionQueue: React.FC<{ memberId: number }> = ({ memberId }) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['questionQueue', memberId],
    queryFn: () => fetchQueue(memberId),
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <ListOrdered className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">Question Queue</h2>
        </div>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-5 h-5 text-indigo-600 animate-spin mr-2" />
          <span className="text-gray-600">Building question queue...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-red-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <ListOrdered className="w-5 h-5 text-red-600" />
          <h2 className="text-lg font-semibold text-gray-900">Question Queue</h2>
        </div>
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle className="w-4 h-4" />
          <span>Failed to load question queue</span>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { queue, scoring_summary } = data;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-indigo-600">
            <ListOrdered className="w-5 h-5" />
          </span>
          <h2 className="text-lg font-semibold text-gray-900">Question Queue</h2>
          <span className="text-sm text-gray-500">
            ({queue.length} question{queue.length !== 1 ? 's' : ''})
          </span>
        </div>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['questionQueue', memberId] })}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Scoring Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6 p-4 bg-gray-50 rounded-lg">
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Available</div>
          <div className="text-lg font-semibold text-gray-900">{scoring_summary.total_available}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Answered</div>
          <div className="text-lg font-semibold text-gray-900">{scoring_summary.already_answered}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Patterns</div>
          <div className="text-lg font-semibold text-gray-900">{scoring_summary.pattern_memberships}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Profile Gaps</div>
          <div className="text-lg font-semibold text-gray-900">{scoring_summary.profile_gaps.length}</div>
        </div>
      </div>

      {/* High Affinity Patterns */}
      {scoring_summary.high_affinity_patterns.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            High Affinity Patterns
          </div>
          <div className="flex flex-wrap gap-1.5">
            {scoring_summary.high_affinity_patterns.map((p) => (
              <span
                key={p.id}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200"
              >
                {p.name}
                <span className="text-amber-600">({(p.affinity * 100).toFixed(0)}%)</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Profile Gaps */}
      {scoring_summary.profile_gaps.length > 0 && (
        <div className="mb-6">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Profile Gaps
          </div>
          <div className="flex flex-wrap gap-1.5">
            {scoring_summary.profile_gaps.map((gap) => (
              <span
                key={gap.field}
                className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-800 border border-green-200"
              >
                {gap.label}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Queue */}
      {queue.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          All available questions have been answered.
        </div>
      ) : (
        <div className="space-y-3">
          {queue.map((q) => (
            <div
              key={q.question_id}
              className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-start gap-3">
                {/* Position Number */}
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-sm font-bold">
                  {q.position}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Badges Row */}
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${difficultyColors[q.difficulty - 1]}`}>
                      {difficultyLabels[q.difficulty - 1]}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${categoryColors[q.category] || 'bg-gray-100 text-gray-800'}`}>
                      {categoryLabels[q.category] || q.category}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${questionTypeColors[q.type] || 'bg-gray-100 text-gray-700'}`}>
                      {questionTypeLabels[q.type] || q.type}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${reasonColors[q.reason] || 'bg-gray-100 text-gray-700 border-gray-300'}`}>
                      {reasonLabels[q.reason] || q.reason}
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs text-gray-500 bg-gray-50">
                      Score: {q.score}
                    </span>
                  </div>

                  {/* Question Text */}
                  <p className="text-gray-900 font-medium">{q.question_text}</p>

                  {/* Reason Detail */}
                  {q.reason_detail && q.reason_detail !== 'Base score' && (
                    <p className="text-xs text-gray-500 mt-1">{q.reason_detail}</p>
                  )}

                  {/* Related Pattern Pills */}
                  {q.related_patterns.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {q.related_patterns.map((rp) => (
                        <span
                          key={`${rp.id}-${rp.relationship}`}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${
                            rp.relationship === 'probe'
                              ? 'bg-amber-50 text-amber-700'
                              : 'bg-blue-50 text-blue-700'
                          }`}
                        >
                          {rp.name}
                          {rp.affinity != null && (
                            <span className="opacity-75">({(rp.affinity * 100).toFixed(0)}%)</span>
                          )}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
