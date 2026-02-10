import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  MessageCircle,
  Sparkles,
  Users,
  Link2,
  BarChart3,
  RefreshCw,
  Clock,
  QrCode,
} from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface RecentAnswer {
  text: string;
  member_name: string;
  timestamp: string;
}

interface QuestionOfTheDay {
  question_id: number;
  question: string;
  context: string;
  category: string;
  recent_answers: RecentAnswer[];
}

interface PatternMember {
  name: string;
  role: string | null;
}

interface PatternSpotlight {
  pattern_id: number;
  pattern: string;
  description: string;
  category: string;
  members: PatternMember[];
  sample_questions: string[];
  vitality_score: number;
}

interface Connection {
  member_a_name: string;
  member_b_name: string;
  edge_type: string;
  discovered_at: string;
}

interface RecentConnections {
  connections: Connection[];
}

interface DisplayStats {
  member_count: number;
  edge_count: number;
  pattern_count: number;
  questions_answered_this_week: number;
}

// =============================================================================
// API Functions
// =============================================================================

async function fetchQuestionOfTheDay(): Promise<QuestionOfTheDay> {
  const response = await fetch(`${API_BASE}/display/question-of-the-day`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to fetch question of the day');
  }
  return response.json();
}

async function fetchPatternSpotlight(): Promise<PatternSpotlight> {
  const response = await fetch(`${API_BASE}/display/pattern-spotlight`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to fetch pattern spotlight');
  }
  return response.json();
}

async function fetchRecentConnections(): Promise<RecentConnections> {
  const response = await fetch(`${API_BASE}/display/recent-connections`);
  if (!response.ok) throw new Error('Failed to fetch recent connections');
  return response.json();
}

async function fetchDisplayStats(): Promise<DisplayStats> {
  const response = await fetch(`${API_BASE}/display/stats`);
  if (!response.ok) throw new Error('Failed to fetch display stats');
  return response.json();
}

// =============================================================================
// Helper Components
// =============================================================================

const categoryColors: Record<string, string> = {
  origin_story: 'from-amber-500 to-orange-600',
  creative_spark: 'from-purple-500 to-pink-600',
  collaboration: 'from-blue-500 to-cyan-600',
  future_vision: 'from-green-500 to-emerald-600',
  community_connection: 'from-indigo-500 to-purple-600',
  hidden_depths: 'from-slate-500 to-gray-600',
  impact_legacy: 'from-rose-500 to-red-600',
  skill_cluster: 'from-blue-500 to-indigo-600',
  interest_theme: 'from-purple-500 to-violet-600',
  collaboration_opportunity: 'from-green-500 to-teal-600',
  community_strength: 'from-orange-500 to-amber-600',
  cross_domain: 'from-pink-500 to-rose-600',
};

const CurrentTime: React.FC = () => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 text-white/80">
      <Clock className="w-5 h-5" />
      <span className="text-lg font-medium">
        {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  );
};

const LoadingCard: React.FC<{ title: string }> = ({ title }) => (
  <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 animate-pulse">
    <div className="flex items-center gap-3 mb-4">
      <div className="w-8 h-8 bg-white/20 rounded-lg" />
      <div className="h-6 bg-white/20 rounded w-32" />
    </div>
    <div className="space-y-3">
      <div className="h-4 bg-white/20 rounded w-full" />
      <div className="h-4 bg-white/20 rounded w-3/4" />
    </div>
  </div>
);

const ErrorCard: React.FC<{ title: string; message: string }> = ({ title, message }) => (
  <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6">
    <div className="flex items-center gap-3 mb-4">
      <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
        <span className="text-white/60">!</span>
      </div>
      <h3 className="text-xl font-semibold text-white/80">{title}</h3>
    </div>
    <p className="text-white/60">{message}</p>
  </div>
);

// =============================================================================
// Main Display Component
// =============================================================================

export const Display: React.FC = () => {
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Fetch all display data
  const {
    data: questionData,
    isLoading: questionLoading,
    error: questionError,
    refetch: refetchQuestion,
  } = useQuery({
    queryKey: ['display-question'],
    queryFn: fetchQuestionOfTheDay,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
    retry: false,
  });

  const {
    data: patternData,
    isLoading: patternLoading,
    error: patternError,
    refetch: refetchPattern,
  } = useQuery({
    queryKey: ['display-pattern'],
    queryFn: fetchPatternSpotlight,
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes (patterns change less often)
    gcTime: 30 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
    retry: false,
  });

  const {
    data: connectionsData,
    isLoading: connectionsLoading,
    refetch: refetchConnections,
  } = useQuery({
    queryKey: ['display-connections'],
    queryFn: fetchRecentConnections,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  const {
    data: statsData,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['display-stats'],
    queryFn: fetchDisplayStats,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  // Manual refresh all
  const handleRefresh = () => {
    refetchQuestion();
    refetchPattern();
    refetchConnections();
    refetchStats();
    setLastRefresh(new Date());
  };

  // Auto-refresh tracking
  useEffect(() => {
    const interval = setInterval(() => {
      setLastRefresh(new Date());
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const categoryGradient = questionData
    ? categoryColors[questionData.category] || 'from-indigo-600 to-violet-700'
    : 'from-indigo-600 to-violet-700';

  return (
    <div className={`min-h-screen bg-gradient-to-br ${categoryGradient} p-8`}>
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="bg-white/20 backdrop-blur-sm p-3 rounded-xl">
            <MessageCircle className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">White Rabbit Community</h1>
            <p className="text-white/70">Profile Optimizer Display</p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <CurrentTime />
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-4 py-2 bg-white/20 backdrop-blur-sm rounded-lg text-white hover:bg-white/30 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Question of the Day - Takes 2 columns */}
        <div className="lg:col-span-2">
          {questionLoading ? (
            <LoadingCard title="Question of the Day" />
          ) : questionError ? (
            <ErrorCard
              title="Question of the Day"
              message={(questionError as Error).message}
            />
          ) : questionData ? (
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="bg-white/20 p-2 rounded-lg">
                  <MessageCircle className="w-6 h-6 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-white">Question of the Day</h2>
                <span className="ml-auto px-3 py-1 bg-white/20 rounded-full text-sm text-white/80">
                  {questionData.category.replace(/_/g, ' ')}
                </span>
              </div>

              <p className="text-4xl font-bold text-white leading-tight mb-4">
                {questionData.question}
              </p>

              <p className="text-lg text-white/70 mb-8">
                {questionData.context}
              </p>

              {questionData.recent_answers.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider">
                    Recent Answers
                  </h3>
                  <div className="space-y-3">
                    {questionData.recent_answers.slice(0, 3).map((answer, i) => (
                      <div
                        key={i}
                        className="bg-white/10 rounded-xl p-4"
                      >
                        <p className="text-white/90 mb-2">"{answer.text}"</p>
                        <p className="text-sm text-white/60">
                          - {answer.member_name}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* QR Code placeholder */}
              <div className="mt-8 flex items-center gap-4 p-4 bg-white/10 rounded-xl">
                <div className="bg-white p-3 rounded-lg">
                  <QrCode className="w-12 h-12 text-gray-800" />
                </div>
                <div>
                  <p className="text-white font-medium">Answer on your phone</p>
                  <p className="text-white/60 text-sm">
                    Scan to share your answer
                  </p>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* Stats Panel */}
        <div className="space-y-6">
          {statsLoading ? (
            <LoadingCard title="Community Stats" />
          ) : statsData ? (
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="bg-white/20 p-2 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-white">Community Stats</h2>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/10 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-white">{statsData.member_count}</div>
                  <div className="text-sm text-white/60">Members</div>
                </div>
                <div className="bg-white/10 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-white">{statsData.edge_count}</div>
                  <div className="text-sm text-white/60">Connections</div>
                </div>
                <div className="bg-white/10 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-white">{statsData.pattern_count}</div>
                  <div className="text-sm text-white/60">Patterns</div>
                </div>
                <div className="bg-white/10 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-white">
                    {statsData.questions_answered_this_week}
                  </div>
                  <div className="text-sm text-white/60">Answers (week)</div>
                </div>
              </div>
            </div>
          ) : null}

          {/* Recent Connections */}
          {connectionsLoading ? (
            <LoadingCard title="Recent Connections" />
          ) : connectionsData && connectionsData.connections.length > 0 ? (
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="bg-white/20 p-2 rounded-lg">
                  <Link2 className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-white">Recent Connections</h2>
              </div>

              <div className="space-y-3">
                {connectionsData.connections.slice(0, 5).map((conn, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 text-white/80"
                  >
                    <Users className="w-4 h-4 text-white/60 flex-shrink-0" />
                    <span className="text-sm">
                      <span className="font-medium text-white">{conn.member_a_name}</span>
                      {' & '}
                      <span className="font-medium text-white">{conn.member_b_name}</span>
                      <span className="text-white/50 ml-2">({conn.edge_type})</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {/* Pattern Spotlight - Full width */}
        <div className="lg:col-span-3">
          {patternLoading ? (
            <LoadingCard title="Pattern Spotlight" />
          ) : patternError ? (
            <ErrorCard
              title="Pattern Spotlight"
              message={(patternError as Error).message}
            />
          ) : patternData ? (
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="bg-white/20 p-2 rounded-lg">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-white">Pattern Spotlight</h2>
                <span className="px-2 py-1 bg-white/20 rounded-full text-xs text-white/80">
                  {patternData.category.replace(/_/g, ' ')}
                </span>
                <span className="ml-auto text-sm text-white/60">
                  Vitality: {patternData.vitality_score}%
                </span>
              </div>

              <div className="grid lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <h3 className="text-2xl font-bold text-white mb-2">
                    {patternData.pattern}
                  </h3>
                  <p className="text-white/70 mb-4">
                    {patternData.description}
                  </p>

                  {patternData.sample_questions.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-2">
                        Explore This Pattern
                      </h4>
                      <ul className="space-y-2">
                        {patternData.sample_questions.slice(0, 3).map((q, i) => (
                          <li key={i} className="flex items-start gap-2 text-white/80">
                            <span className="text-white/40 mt-0.5">-</span>
                            {q}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-3">
                    Members ({patternData.members.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {patternData.members.slice(0, 8).map((member, i) => (
                      <span
                        key={i}
                        className="px-3 py-1.5 bg-white/20 rounded-full text-sm text-white"
                      >
                        {member.name}
                      </span>
                    ))}
                    {patternData.members.length > 8 && (
                      <span className="px-3 py-1.5 bg-white/10 rounded-full text-sm text-white/60">
                        +{patternData.members.length - 8} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-8 flex items-center justify-between text-white/50 text-sm">
        <span>White Rabbit Ashland</span>
        <span>
          Last updated: {lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </footer>
    </div>
  );
};
