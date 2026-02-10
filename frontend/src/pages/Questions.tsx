import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  HelpCircle,
  Sparkles,
  User,
  Globe,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Lightbulb,
  Target,
  Send,
  ExternalLink,
  Check,
  AlertCircle,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Question {
  id: number;
  question_text: string;
  question_type: 'free_form' | 'multiple_choice' | 'yes_no' | 'fill_in_blank';
  category: string;
  difficulty_level: number;
  purpose: string;
  follow_up_prompts: string[];
  potential_insights: string[];
  related_profile_fields: string[];
  options: string[];
  blank_prompt: string | null;
}

interface QuestionDeck {
  id: number;
  deck_id: string;
  name: string;
  description: string | null;
  member_id: number | null;
  is_active: boolean;
  version: number;
  questions: Question[];
  created_at: string;
}

interface Member {
  id: number;
  name: string;
  email: string;
}

interface DeckGenerationResponse {
  success: boolean;
  deck_id: number | null;
  questions_generated: number;
  response_text: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

async function fetchDecks(): Promise<QuestionDeck[]> {
  const response = await fetch(`${API_BASE}/questions/decks`);
  if (!response.ok) throw new Error('Failed to fetch decks');
  return response.json();
}

async function fetchMembers(): Promise<Member[]> {
  const response = await fetch(`${API_BASE}/members?limit=100`);
  if (!response.ok) throw new Error('Failed to fetch members');
  const data = await response.json();
  return data.members;
}

async function generateGlobalDeck(params: {
  deck_name: string;
  description?: string;
  num_questions: number;
  focus_categories?: string[];
}): Promise<DeckGenerationResponse> {
  const response = await fetch(`${API_BASE}/questions/deck/generate-global`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) throw new Error('Failed to generate global deck');
  return response.json();
}

async function generatePersonalDeck(params: {
  member_id: number;
  num_questions: number;
}): Promise<DeckGenerationResponse> {
  const response = await fetch(`${API_BASE}/questions/deck/generate-personal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) throw new Error('Failed to generate personal deck');
  return response.json();
}

async function refineDeck(params: {
  deck_id: number;
  feedback: string;
}): Promise<DeckGenerationResponse> {
  const response = await fetch(`${API_BASE}/questions/deck/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) throw new Error('Failed to refine deck');
  return response.json();
}

async function shareQuestion(params: {
  question_id: number;
  notes?: string;
}): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/questions/share`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to share question' }));
    throw new Error(error.detail || 'Failed to share question');
  }
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

const questionTypeColors: Record<string, string> = {
  free_form: 'bg-slate-100 text-slate-700 border border-slate-300',
  multiple_choice: 'bg-cyan-100 text-cyan-800 border border-cyan-300',
  yes_no: 'bg-emerald-100 text-emerald-800 border border-emerald-300',
  fill_in_blank: 'bg-violet-100 text-violet-800 border border-violet-300',
};

const questionTypeLabels: Record<string, string> = {
  free_form: 'Free Form',
  multiple_choice: 'Multiple Choice',
  yes_no: 'Yes/No',
  fill_in_blank: 'Fill in Blank',
};

const questionTypeIcons: Record<string, string> = {
  free_form: '✍️',
  multiple_choice: '☑️',
  yes_no: '👍',
  fill_in_blank: '___',
};

const categoryLabels: Record<string, string> = {
  origin_story: 'Origin Story',
  creative_spark: 'Creative Spark',
  collaboration: 'Collaboration',
  future_vision: 'Future Vision',
  community_connection: 'Community Connection',
  hidden_depths: 'Hidden Depths',
  impact_legacy: 'Impact & Legacy',
};

const DifficultyBadge: React.FC<{ level: number }> = ({ level }) => {
  const colors = ['bg-green-100 text-green-800', 'bg-yellow-100 text-yellow-800', 'bg-red-100 text-red-800'];
  const labels = ['Easy', 'Medium', 'Deep'];
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[level - 1]}`}>
      {labels[level - 1]}
    </span>
  );
};

const QuestionCard: React.FC<{
  question: Question;
  expanded: boolean;
  onToggle: () => void;
  onShare: (questionId: number) => void;
  isSharing: boolean;
  shareResult: { success: boolean; message: string } | null;
}> = ({
  question,
  expanded,
  onToggle,
  onShare,
  isSharing,
  shareResult,
}) => {
  return (
    <div className="border border-gray-200 rounded-lg bg-white">
      <button
        onClick={onToggle}
        className="w-full p-4 text-left flex items-start justify-between gap-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${questionTypeColors[question.question_type] || 'bg-gray-100 text-gray-800'}`}>
              {questionTypeIcons[question.question_type]} {questionTypeLabels[question.question_type] || question.question_type}
            </span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${categoryColors[question.category] || 'bg-gray-100 text-gray-800'}`}>
              {categoryLabels[question.category] || question.category}
            </span>
            <DifficultyBadge level={question.difficulty_level} />
          </div>
          <p className="text-gray-900 font-medium">{question.question_text}</p>
          {/* Show fill-in-blank prompt inline */}
          {question.question_type === 'fill_in_blank' && question.blank_prompt && (
            <p className="text-gray-500 italic mt-1 text-sm">"{question.blank_prompt}"</p>
          )}
          {/* Show options preview inline */}
          {question.question_type === 'multiple_choice' && question.options.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {question.options.map((opt, i) => (
                <span key={i} className="px-2 py-0.5 bg-cyan-50 text-cyan-700 rounded text-xs">
                  {opt}
                </span>
              ))}
            </div>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-100">
          <div className="pt-4">
            <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
              <Target className="w-4 h-4" />
              Purpose
            </div>
            <p className="text-sm text-gray-600">{question.purpose}</p>
          </div>

          {question.follow_up_prompts.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                <MessageSquare className="w-4 h-4" />
                Follow-up Prompts
              </div>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                {question.follow_up_prompts.map((prompt, i) => (
                  <li key={i}>{prompt}</li>
                ))}
              </ul>
            </div>
          )}

          {question.potential_insights.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                <Lightbulb className="w-4 h-4" />
                Potential Insights
              </div>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                {question.potential_insights.map((insight, i) => (
                  <li key={i}>{insight}</li>
                ))}
              </ul>
            </div>
          )}

          {question.related_profile_fields.length > 0 && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Related Profile Fields</div>
              <div className="flex flex-wrap gap-1">
                {question.related_profile_fields.map((field, i) => (
                  <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="pt-2 border-t border-gray-100 flex items-center gap-3">
            <button
              onClick={() => onShare(question.id)}
              disabled={isSharing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors disabled:opacity-50"
            >
              {isSharing ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <ExternalLink className="w-4 h-4" />
              )}
              Share with HQ
            </button>
            {shareResult && (
              <span className={`flex items-center gap-1 text-sm ${shareResult.success ? 'text-green-600' : 'text-red-600'}`}>
                {shareResult.success ? <Check className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                {shareResult.message}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const DeckCard: React.FC<{
  deck: QuestionDeck;
  onRefine: (deckId: number) => void;
  isRefining: boolean;
}> = ({ deck, onRefine, isRefining }) => {
  const [expanded, setExpanded] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set());
  const [sharingQuestionId, setSharingQuestionId] = useState<number | null>(null);
  const [shareNotes, setShareNotes] = useState('');
  const [shareResults, setShareResults] = useState<Record<number, { success: boolean; message: string }>>({});

  const shareMutation = useMutation({
    mutationFn: shareQuestion,
    onSuccess: (_data, variables) => {
      setShareResults((prev) => ({
        ...prev,
        [variables.question_id]: { success: true, message: 'Shared!' },
      }));
      setSharingQuestionId(null);
      setShareNotes('');
    },
    onError: (error: Error, variables) => {
      setShareResults((prev) => ({
        ...prev,
        [variables.question_id]: { success: false, message: error.message },
      }));
      setSharingQuestionId(null);
      setShareNotes('');
    },
  });

  const toggleQuestion = (id: number) => {
    setExpandedQuestions((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleShareConfirm = () => {
    if (sharingQuestionId) {
      shareMutation.mutate({
        question_id: sharingQuestionId,
        notes: shareNotes.trim() || undefined,
      });
    }
  };

  const sharingQuestion = sharingQuestionId
    ? deck.questions.find((q) => q.id === sharingQuestionId)
    : null;

  const categoryCounts = deck.questions.reduce((acc, q) => {
    acc[q.category] = (acc[q.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Share with HQ confirmation modal */}
      {sharingQuestion && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <ExternalLink className="w-5 h-5 text-indigo-600" />
              Share with HQ
            </h3>
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-900">{sharingQuestion.question_text}</p>
              <p className="text-xs text-gray-500 mt-1">{categoryLabels[sharingQuestion.category] || sharingQuestion.category} &middot; {questionTypeLabels[sharingQuestion.question_type] || sharingQuestion.question_type}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Notes <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <textarea
                value={shareNotes}
                onChange={(e) => setShareNotes(e.target.value)}
                placeholder="e.g., specific members who should receive this question..."
                className="w-full h-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
              />
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => {
                  setSharingQuestionId(null);
                  setShareNotes('');
                }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleShareConfirm}
                disabled={shareMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {shareMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Sharing...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Share
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              {deck.member_id ? (
                <User className="w-4 h-4 text-indigo-600" />
              ) : (
                <Globe className="w-4 h-4 text-green-600" />
              )}
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                {deck.member_id ? 'Personal Deck' : 'Global Deck'}
              </span>
              <span className="text-xs text-gray-400">v{deck.version}</span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">{deck.name}</h3>
            {deck.description && (
              <p className="text-sm text-gray-600 mt-1">{deck.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onRefine(deck.id)}
              disabled={isRefining}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isRefining ? 'animate-spin' : ''}`} />
              Refine
            </button>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {expanded ? 'Hide' : 'Show'} {deck.questions.length} questions
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-1 mt-3">
          {Object.entries(categoryCounts).map(([cat, count]) => (
            <span
              key={cat}
              className={`px-2 py-0.5 rounded text-xs font-medium ${categoryColors[cat] || 'bg-gray-100 text-gray-800'}`}
            >
              {categoryLabels[cat] || cat}: {count}
            </span>
          ))}
        </div>
      </div>

      {expanded && (
        <div className="p-4 space-y-3 bg-gray-50">
          {deck.questions.map((question) => (
            <QuestionCard
              key={question.id}
              question={question}
              expanded={expandedQuestions.has(question.id)}
              onToggle={() => toggleQuestion(question.id)}
              onShare={(id) => setSharingQuestionId(id)}
              isSharing={shareMutation.isPending && sharingQuestionId === question.id}
              shareResult={shareResults[question.id] || null}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const Questions: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'decks' | 'generate'>('decks');
  const [generateType, setGenerateType] = useState<'global' | 'personal'>('global');
  const [deckName, setDeckName] = useState('Community Discovery Deck');
  const [deckDescription, setDeckDescription] = useState('');
  const [numQuestions, setNumQuestions] = useState(20);
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const [refineFeedback, setRefineFeedback] = useState('');
  const [refiningDeckId, setRefiningDeckId] = useState<number | null>(null);
  const [lastResponse, setLastResponse] = useState<string | null>(null);

  const { data: decks, isLoading: decksLoading } = useQuery({
    queryKey: ['questionDecks'],
    queryFn: fetchDecks,
  });

  const { data: members } = useQuery({
    queryKey: ['members'],
    queryFn: fetchMembers,
  });

  const generateGlobalMutation = useMutation({
    mutationFn: generateGlobalDeck,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['questionDecks'] });
      setLastResponse(data.response_text);
      setActiveTab('decks');
    },
  });

  const generatePersonalMutation = useMutation({
    mutationFn: generatePersonalDeck,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['questionDecks'] });
      setLastResponse(data.response_text);
      setActiveTab('decks');
    },
  });

  const refineMutation = useMutation({
    mutationFn: refineDeck,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['questionDecks'] });
      setLastResponse(data.response_text);
      setRefiningDeckId(null);
      setRefineFeedback('');
    },
    onSettled: () => {
      setRefiningDeckId(null);
    },
  });

  const handleGenerate = () => {
    if (generateType === 'global') {
      generateGlobalMutation.mutate({
        deck_name: deckName,
        description: deckDescription || undefined,
        num_questions: numQuestions,
      });
    } else if (selectedMemberId) {
      generatePersonalMutation.mutate({
        member_id: selectedMemberId,
        num_questions: numQuestions,
      });
    }
  };

  const handleRefine = (deckId: number) => {
    setRefiningDeckId(deckId);
  };

  const submitRefine = () => {
    if (refiningDeckId && refineFeedback.trim()) {
      refineMutation.mutate({
        deck_id: refiningDeckId,
        feedback: refineFeedback,
      });
    }
  };

  const isGenerating = generateGlobalMutation.isPending || generatePersonalMutation.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <HelpCircle className="w-7 h-7 text-indigo-600" />
            Question Decks
          </h1>
          <p className="text-gray-600 mt-1">
            Generate and manage question decks for engaging profile conversations
          </p>
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

      {/* Refine Modal */}
      {refiningDeckId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Refine Question Deck</h3>
            <p className="text-sm text-gray-600 mb-4">
              Provide feedback to improve the questions in this deck. The agent will generate a new version based on your input.
            </p>
            <textarea
              value={refineFeedback}
              onChange={(e) => setRefineFeedback(e.target.value)}
              placeholder="e.g., Add more questions about creative processes, make the collaboration questions less formal..."
              className="w-full h-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
            />
            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => {
                  setRefiningDeckId(null);
                  setRefineFeedback('');
                }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={submitRefine}
                disabled={!refineFeedback.trim() || refineMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {refineMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Refining...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Refine Deck
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('decks')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'decks'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          View Decks
        </button>
        <button
          onClick={() => setActiveTab('generate')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'generate'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Generate New
        </button>
      </div>

      {activeTab === 'generate' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-600" />
            Generate Question Deck
          </h2>

          <div className="space-y-4">
            {/* Type Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Deck Type</label>
              <div className="flex gap-3">
                <button
                  onClick={() => setGenerateType('global')}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-colors ${
                    generateType === 'global'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <Globe className="w-5 h-5" />
                  <div className="text-left">
                    <div className="font-medium">Global Deck</div>
                    <div className="text-xs opacity-75">For all community members</div>
                  </div>
                </button>
                <button
                  onClick={() => setGenerateType('personal')}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-colors ${
                    generateType === 'personal'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <User className="w-5 h-5" />
                  <div className="text-left">
                    <div className="font-medium">Personal Deck</div>
                    <div className="text-xs opacity-75">Tailored to a specific member</div>
                  </div>
                </button>
              </div>
            </div>

            {/* Deck Name (for global) */}
            {generateType === 'global' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Deck Name</label>
                  <input
                    type="text"
                    value={deckName}
                    onChange={(e) => setDeckName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description / Purpose <span className="text-gray-400 font-normal">(optional)</span>
                  </label>
                  <textarea
                    value={deckDescription}
                    onChange={(e) => setDeckDescription(e.target.value)}
                    placeholder="e.g., Questions to help identify potential collaborators for the upcoming hackathon, focused on technical skills and project interests..."
                    className="w-full h-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Describe the specific purpose or theme for this deck. The AI will tailor questions accordingly.
                  </p>
                </div>
              </>
            )}

            {/* Member Selection (for personal) */}
            {generateType === 'personal' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Select Member</label>
                <select
                  value={selectedMemberId || ''}
                  onChange={(e) => setSelectedMemberId(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="">Choose a member...</option>
                  {members?.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Number of Questions */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Number of Questions
              </label>
              <input
                type="number"
                value={numQuestions}
                onChange={(e) => setNumQuestions(Math.max(1, Math.min(50, Number(e.target.value))))}
                min={1}
                max={50}
                className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating || (generateType === 'personal' && !selectedMemberId)}
              className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Generate Deck
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {activeTab === 'decks' && (
        <div className="space-y-4">
          {decksLoading ? (
            <div className="text-center py-12">
              <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">Loading question decks...</p>
            </div>
          ) : decks && decks.length > 0 ? (
            decks.map((deck) => (
              <DeckCard
                key={deck.id}
                deck={deck}
                onRefine={handleRefine}
                isRefining={refineMutation.isPending && refiningDeckId === deck.id}
              />
            ))
          ) : (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <HelpCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No question decks yet</h3>
              <p className="text-gray-600 mb-4">
                Generate your first deck to start engaging members with thoughtful questions.
              </p>
              <button
                onClick={() => setActiveTab('generate')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <Sparkles className="w-4 h-4" />
                Generate First Deck
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
