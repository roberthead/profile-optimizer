import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Loader2,
  CheckCircle2,
  Sparkles,
  BookmarkIcon,
  Home,
  ChevronLeft,
  Coffee,
  Flame,
} from 'lucide-react';
import { QuestionCard } from '../components/QuestionCard';
import type { MobileQuestionData } from '../types/questions';

const API_BASE = 'http://localhost:8000/api/v1';

// API functions
async function fetchNextQuestion(memberId: number): Promise<MobileQuestionData | null> {
  const response = await fetch(`${API_BASE}/mobile/questions/next?member_id=${memberId}`);
  if (!response.ok) throw new Error('Failed to fetch question');
  const data = await response.json();
  return data;
}

async function submitAnswer(questionId: number, memberId: number, answer: string, responseTime?: number) {
  const response = await fetch(`${API_BASE}/mobile/questions/${questionId}/respond?member_id=${memberId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      response_value: answer,
      response_time_seconds: responseTime,
    }),
  });
  if (!response.ok) throw new Error('Failed to submit answer');
  return response.json();
}

async function skipQuestion(questionId: number, memberId: number) {
  const response = await fetch(`${API_BASE}/mobile/questions/${questionId}/skip?member_id=${memberId}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to skip question');
  return response.json();
}

async function saveQuestion(questionId: number, memberId: number) {
  const response = await fetch(`${API_BASE}/mobile/questions/${questionId}/save?member_id=${memberId}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to save question');
  return response.json();
}

async function markNotMyVibe(questionId: number, memberId: number) {
  const response = await fetch(`${API_BASE}/mobile/questions/${questionId}/not-my-vibe?member_id=${memberId}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to mark question');
  return response.json();
}

async function fetchSessionStats(memberId: number) {
  const response = await fetch(`${API_BASE}/mobile/stats?member_id=${memberId}`);
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
}

interface Member {
  id: number;
  first_name: string | null;
  last_name: string | null;
  email: string;
}

async function fetchMembers(): Promise<{ members: Member[] }> {
  const response = await fetch(`${API_BASE}/members?per_page=100`);
  if (!response.ok) throw new Error('Failed to fetch members');
  return response.json();
}

// Animation states for card transitions
type AnimationState = 'entering' | 'visible' | 'exiting-left' | 'exiting-right' | 'exiting-up' | 'exiting-down';

const animationClasses: Record<AnimationState, string> = {
  'entering': 'opacity-0 scale-95 translate-y-4',
  'visible': 'opacity-100 scale-100 translate-y-0',
  'exiting-left': 'opacity-0 -translate-x-full rotate-[-10deg]',
  'exiting-right': 'opacity-0 translate-x-full rotate-[10deg]',
  'exiting-up': 'opacity-0 -translate-y-full scale-90',
  'exiting-down': 'opacity-0 translate-y-full scale-90',
};

export const MobileQuestion: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  // Get member_id from URL or default to null (show member selector)
  const memberId = searchParams.get('member_id') ? Number(searchParams.get('member_id')) : null;

  // Animation and timing state
  const [animationState, setAnimationState] = useState<AnimationState>('entering');
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [dropsEarned, setDropsEarned] = useState(0);
  const [showDropsAnimation, setShowDropsAnimation] = useState(false);

  // Fetch members for selector
  const { data: membersData } = useQuery({
    queryKey: ['members'],
    queryFn: fetchMembers,
    enabled: !memberId,
  });

  // Fetch next question
  const { data: question, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['mobileQuestion', memberId],
    queryFn: () => fetchNextQuestion(memberId!),
    enabled: !!memberId,
    staleTime: 0,
  });

  // Fetch session stats
  const { data: stats } = useQuery({
    queryKey: ['mobileStats', memberId],
    queryFn: () => fetchSessionStats(memberId!),
    enabled: !!memberId,
  });

  // Reset animation when question changes
  useEffect(() => {
    if (question && !isRefetching) {
      setAnimationState('entering');
      setQuestionStartTime(Date.now());
      const timer = setTimeout(() => setAnimationState('visible'), 50);
      return () => clearTimeout(timer);
    }
  }, [question?.id, isRefetching]);

  // Mutations
  const answerMutation = useMutation({
    mutationFn: ({ answer }: { answer: string }) => {
      const responseTime = Math.floor((Date.now() - questionStartTime) / 1000);
      return submitAnswer(question!.id, memberId!, answer, responseTime);
    },
    onSuccess: (data) => {
      // Show drops earned with animation!
      if (data.drops_earned > 0) {
        setDropsEarned(data.drops_earned);
        setShowDropsAnimation(true);
        setTimeout(() => setShowDropsAnimation(false), 2000);
      }
      showSuccessAnimation(`+${data.drops_earned} drops!`);
      animateAndFetchNext('exiting-right');
    },
  });

  const skipMutation = useMutation({
    mutationFn: () => skipQuestion(question!.id, memberId!),
    onSuccess: () => {
      animateAndFetchNext('exiting-left');
    },
  });

  const saveMutation = useMutation({
    mutationFn: () => saveQuestion(question!.id, memberId!),
    onSuccess: () => {
      showSuccessAnimation('Saved for later!');
      animateAndFetchNext('exiting-up');
    },
  });

  const notMyVibeMutation = useMutation({
    mutationFn: () => markNotMyVibe(question!.id, memberId!),
    onSuccess: () => {
      animateAndFetchNext('exiting-down');
    },
  });

  const showSuccessAnimation = (message: string) => {
    setSuccessMessage(message);
    setShowSuccess(true);
    setTimeout(() => setShowSuccess(false), 1500);
  };

  const animateAndFetchNext = useCallback((exitDirection: AnimationState) => {
    setAnimationState(exitDirection);
    setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: ['mobileStats', memberId] });
      refetch();
    }, 300);
  }, [memberId, queryClient, refetch]);

  const isSubmitting = answerMutation.isPending || skipMutation.isPending ||
                       saveMutation.isPending || notMyVibeMutation.isPending;

  // Member selector view
  if (!memberId) {
    const sortedMembers = membersData?.members
      ? [...membersData.members].sort((a, b) => {
          const nameA = [a.first_name, a.last_name].filter(Boolean).join(' ').toLowerCase() || a.email;
          const nameB = [b.first_name, b.last_name].filter(Boolean).join(' ').toLowerCase() || b.email;
          return nameA.localeCompare(nameB);
        })
      : [];

    return (
      <div className="min-h-screen bg-gradient-to-b from-indigo-100 to-purple-100 flex flex-col">
        <div className="p-4 flex items-center gap-3">
          <Link
            to="/"
            className="p-2 rounded-full bg-white/80 text-gray-600 hover:bg-white transition-colors"
          >
            <Home className="w-5 h-5" />
          </Link>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center px-6 pb-20">
          <div className="bg-white rounded-3xl shadow-xl p-8 w-full max-w-md">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 rounded-full mb-4">
                <Sparkles className="w-8 h-8 text-indigo-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Quick Questions
              </h1>
              <p className="text-gray-600">
                Answer a few questions to help us learn more about you and connect you with the community.
              </p>
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Who are you?
              </label>
              {sortedMembers.map((member) => (
                <button
                  key={member.id}
                  onClick={() => setSearchParams({ member_id: String(member.id) })}
                  className="w-full p-4 text-left bg-gray-50 hover:bg-indigo-50 rounded-xl transition-colors"
                >
                  <div className="font-medium text-gray-900">
                    {[member.first_name, member.last_name].filter(Boolean).join(' ') || member.email}
                  </div>
                  {(member.first_name || member.last_name) && (
                    <div className="text-sm text-gray-500">{member.email}</div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-indigo-100 to-purple-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your next question...</p>
        </div>
      </div>
    );
  }

  // No more questions state
  if (!question) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-indigo-100 to-purple-100 flex flex-col">
        <div className="p-4 flex items-center gap-3">
          <Link
            to="/"
            className="p-2 rounded-full bg-white/80 text-gray-600 hover:bg-white transition-colors"
          >
            <Home className="w-5 h-5" />
          </Link>
        </div>

        <div className="flex-1 flex items-center justify-center px-6">
          <div className="bg-white rounded-3xl shadow-xl p-8 text-center max-w-md">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-6">
              <CheckCircle2 className="w-10 h-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">
              All caught up!
            </h2>
            <p className="text-gray-600 mb-6">
              You've answered all available questions. Check back later for new ones!
            </p>
            {stats && (
              <div className="bg-gray-50 rounded-xl p-4 mb-6">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-indigo-600">{stats.questions_answered_today}</div>
                    <div className="text-sm text-gray-500">Answered</div>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-2xl font-bold text-amber-600">
                      <Coffee className="w-5 h-5" />
                      {stats.cafe_drops || 0}
                    </div>
                    <div className="text-sm text-gray-500">Cafe Drops</div>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-2xl font-bold text-orange-500">
                      {stats.current_streak > 0 && <Flame className="w-5 h-5" />}
                      {stats.current_streak || 0}
                    </div>
                    <div className="text-sm text-gray-500">Day Streak</div>
                  </div>
                </div>
              </div>
            )}
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
            >
              <Home className="w-5 h-5" />
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Main question view
  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-100 to-purple-100 flex flex-col">
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSearchParams({})}
            className="p-2 rounded-full bg-white/80 text-gray-600 hover:bg-white transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <Link
            to="/"
            className="p-2 rounded-full bg-white/80 text-gray-600 hover:bg-white transition-colors"
          >
            <Home className="w-5 h-5" />
          </Link>
        </div>

        <div className="flex items-center gap-2">
          {/* Cafe drops counter */}
          {stats && (
            <div className={`flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-amber-100 to-orange-100 rounded-full text-sm font-medium text-amber-700 ${showDropsAnimation ? 'animate-bounce' : ''}`}>
              <Coffee className="w-4 h-4" />
              <span>{stats.cafe_drops || 0}</span>
              {stats.current_streak > 1 && (
                <span className="flex items-center gap-0.5 text-orange-600">
                  <Flame className="w-3 h-3" />
                  {stats.current_streak}
                </span>
              )}
            </div>
          )}

          {/* Saved questions indicator */}
          {stats && stats.questions_saved > 0 && (
            <button className="flex items-center gap-1 px-3 py-1.5 bg-white/80 rounded-full text-sm text-amber-600">
              <BookmarkIcon className="w-4 h-4" />
              {stats.questions_saved}
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-4 pb-4">
        <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
          <span>{question.questions_answered_today} answered today</span>
          <span>{question.questions_remaining} remaining</span>
        </div>
        <div className="h-2 bg-white/50 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(100, (question.questions_answered_today / Math.max(1, question.questions_answered_today + question.questions_remaining)) * 100)}%`
            }}
          />
        </div>
      </div>

      {/* Question card with animations */}
      <div className="flex-1 px-4 pb-6 relative overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ease-out ${animationClasses[animationState]}`}
        >
          <QuestionCard
            question={question}
            onAnswer={(answer) => answerMutation.mutate({ answer })}
            onSkip={() => skipMutation.mutate()}
            onSave={() => saveMutation.mutate()}
            onNotMyVibe={() => notMyVibeMutation.mutate()}
            isSubmitting={isSubmitting}
          />
        </div>

        {/* Success overlay with drops animation */}
        {showSuccess && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 animate-in fade-in duration-200">
            <div className="text-center">
              {dropsEarned > 0 ? (
                <>
                  <div className="relative">
                    <Coffee className="w-16 h-16 text-amber-500 mx-auto mb-3 animate-bounce" />
                    <div className="absolute -top-2 -right-2 bg-green-500 text-white text-sm font-bold rounded-full w-8 h-8 flex items-center justify-center animate-ping">
                      +{dropsEarned}
                    </div>
                  </div>
                  <p className="text-xl font-semibold text-gray-900">{successMessage}</p>
                  <p className="text-sm text-amber-600 mt-1">Keep going!</p>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-3" />
                  <p className="text-xl font-semibold text-gray-900">{successMessage}</p>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Swipe hints for first-time users */}
      {stats && stats.total_answered < 3 && (
        <div className="px-4 pb-6">
          <div className="bg-white/60 rounded-xl p-3 text-center text-sm text-gray-600">
            <span className="font-medium">Tip:</span> Use the buttons below the card to skip, save, or signal when a question doesn't resonate.
          </div>
        </div>
      )}
    </div>
  );
};

export default MobileQuestion;
