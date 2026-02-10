import React, { useState } from 'react';
import {
  Sparkles,
  Users,
  ChevronUp,
  ChevronDown,
  Heart,
  Zap,
  Coffee,
  MessageCircle,
  Brain,
} from 'lucide-react';
import type { MobileQuestionData } from '../types/questions';

interface QuestionCardProps {
  question: MobileQuestionData;
  onAnswer: (answer: string) => void;
  onSkip: () => void;
  onSave: () => void;
  onNotMyVibe: () => void;
  isSubmitting: boolean;
}

// Vibe styling configuration
const vibeConfig: Record<string, { icon: React.FC<{ className?: string }>; color: string; bgColor: string }> = {
  warm: { icon: Heart, color: 'text-rose-600', bgColor: 'bg-rose-50' },
  playful: { icon: Zap, color: 'text-amber-600', bgColor: 'bg-amber-50' },
  deep: { icon: Brain, color: 'text-indigo-600', bgColor: 'bg-indigo-50' },
  edgy: { icon: Sparkles, color: 'text-purple-600', bgColor: 'bg-purple-50' },
  connector: { icon: Users, color: 'text-teal-600', bgColor: 'bg-teal-50' },
};

// Category styling
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

// Difficulty styling
const difficultyConfig: Record<number, { label: string; color: string }> = {
  1: { label: 'Quick', color: 'bg-green-100 text-green-700' },
  2: { label: 'Thoughtful', color: 'bg-yellow-100 text-yellow-700' },
  3: { label: 'Deep Dive', color: 'bg-red-100 text-red-700' },
};

const getMemberDisplayName = (member: MemberContext): string => {
  const name = [member.first_name, member.last_name].filter(Boolean).join(' ');
  return name || `Member #${member.id}`;
};

export const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  onAnswer,
  onSkip,
  onSave,
  onNotMyVibe,
  isSubmitting,
}) => {
  const [textAnswer, setTextAnswer] = useState('');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [showContext, setShowContext] = useState(false);

  const vibeStyle = question.vibe ? vibeConfig[question.vibe] : null;
  const VibeIcon = vibeStyle?.icon || Coffee;
  const difficulty = difficultyConfig[question.difficulty_level] || difficultyConfig[1];

  const handleSubmit = () => {
    let answer = '';

    switch (question.question_type) {
      case 'yes_no':
      case 'multiple_choice':
        answer = selectedOption || '';
        break;
      case 'fill_in_blank':
      case 'free_form':
        answer = textAnswer;
        break;
    }

    if (answer) {
      onAnswer(answer);
    }
  };

  const isAnswerValid = () => {
    switch (question.question_type) {
      case 'yes_no':
      case 'multiple_choice':
        return selectedOption !== null;
      case 'fill_in_blank':
      case 'free_form':
        return textAnswer.trim().length > 0;
      default:
        return false;
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-3xl shadow-xl overflow-hidden">
      {/* Header with badges */}
      <div className="px-5 pt-5 pb-3">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Category badge */}
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${categoryColors[question.category] || 'bg-gray-100 text-gray-800'}`}>
              {categoryLabels[question.category] || question.category}
            </span>

            {/* Difficulty badge */}
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${difficulty.color}`}>
              {difficulty.label}
            </span>
          </div>

          {/* Vibe indicator */}
          {vibeStyle && (
            <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${vibeStyle.bgColor}`}>
              <VibeIcon className={`w-4 h-4 ${vibeStyle.color}`} />
              <span className={`text-xs font-medium ${vibeStyle.color} capitalize`}>
                {question.vibe}
              </span>
            </div>
          )}
        </div>

        {/* Context toggle */}
        {(question.notes || question.related_members.length > 0 || question.related_pattern) && (
          <button
            onClick={() => setShowContext(!showContext)}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <MessageCircle className="w-4 h-4" />
            <span>Why this question?</span>
            {showContext ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}

        {/* Context panel */}
        {showContext && (
          <div className="mt-3 p-3 bg-gray-50 rounded-xl space-y-2 text-sm animate-in slide-in-from-top-2 duration-200">
            {question.notes && (
              <p className="text-gray-600">{question.notes}</p>
            )}
            {question.related_pattern && (
              <div className="flex items-center gap-2 text-gray-600">
                <Sparkles className="w-4 h-4 text-indigo-500" />
                <span>Related to pattern: <span className="font-medium">{question.related_pattern.name}</span></span>
              </div>
            )}
            {question.related_members.length > 0 && (
              <div className="flex items-center gap-2 text-gray-600">
                <Users className="w-4 h-4 text-teal-500" />
                <span>
                  Connects you with: {question.related_members.map(m => getMemberDisplayName(m)).join(', ')}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Question text */}
      <div className="flex-1 px-5 py-4 flex items-center">
        <h2 className="text-xl font-semibold text-gray-900 leading-relaxed">
          {question.question_text}
        </h2>
      </div>

      {/* Answer section */}
      <div className="px-5 pb-4">
        {/* Yes/No buttons */}
        {question.question_type === 'yes_no' && (
          <div className="flex gap-3">
            <button
              onClick={() => setSelectedOption('yes')}
              className={`flex-1 py-4 rounded-xl font-medium text-lg transition-all ${
                selectedOption === 'yes'
                  ? 'bg-green-500 text-white shadow-lg scale-105'
                  : 'bg-green-50 text-green-700 hover:bg-green-100'
              }`}
            >
              Yes
            </button>
            <button
              onClick={() => setSelectedOption('no')}
              className={`flex-1 py-4 rounded-xl font-medium text-lg transition-all ${
                selectedOption === 'no'
                  ? 'bg-red-500 text-white shadow-lg scale-105'
                  : 'bg-red-50 text-red-700 hover:bg-red-100'
              }`}
            >
              No
            </button>
          </div>
        )}

        {/* Multiple choice options */}
        {question.question_type === 'multiple_choice' && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {question.options.map((option, index) => (
              <button
                key={index}
                onClick={() => setSelectedOption(option)}
                className={`w-full p-4 text-left rounded-xl transition-all ${
                  selectedOption === option
                    ? 'bg-indigo-500 text-white shadow-lg'
                    : 'bg-gray-50 text-gray-800 hover:bg-gray-100'
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        )}

        {/* Fill in the blank */}
        {question.question_type === 'fill_in_blank' && (
          <div className="space-y-2">
            {question.blank_prompt && (
              <p className="text-gray-500 italic">"{question.blank_prompt}"</p>
            )}
            <input
              type="text"
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              placeholder="Type your answer..."
              className="w-full p-4 bg-gray-50 rounded-xl border-2 border-transparent focus:border-indigo-500 focus:bg-white focus:outline-none text-lg transition-all"
            />
          </div>
        )}

        {/* Free form text */}
        {question.question_type === 'free_form' && (
          <textarea
            value={textAnswer}
            onChange={(e) => setTextAnswer(e.target.value)}
            placeholder="Share your thoughts..."
            rows={3}
            className="w-full p-4 bg-gray-50 rounded-xl border-2 border-transparent focus:border-indigo-500 focus:bg-white focus:outline-none text-lg transition-all resize-none"
          />
        )}

        {/* Submit button for text answers */}
        {(question.question_type === 'fill_in_blank' || question.question_type === 'free_form') && textAnswer.trim() && (
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="mt-3 w-full py-4 bg-indigo-600 text-white rounded-xl font-semibold text-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isSubmitting ? 'Sending...' : 'Submit Answer'}
          </button>
        )}

        {/* Submit button for choice answers */}
        {(question.question_type === 'yes_no' || question.question_type === 'multiple_choice') && selectedOption && (
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="mt-3 w-full py-4 bg-indigo-600 text-white rounded-xl font-semibold text-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isSubmitting ? 'Sending...' : 'Confirm'}
          </button>
        )}
      </div>

      {/* Action buttons - mobile optimized with min 44px touch targets */}
      <div className="px-5 pb-6 pt-2 border-t border-gray-100">
        <div className="flex justify-between items-center">
          {/* Skip (Left) */}
          <button
            onClick={onSkip}
            disabled={isSubmitting}
            className="flex flex-col items-center gap-1 p-3 min-w-[60px] min-h-[60px] rounded-xl text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-all disabled:opacity-50"
            aria-label="Skip question"
          >
            <span className="text-2xl">&#x2190;</span>
            <span className="text-xs font-medium">Skip</span>
          </button>

          {/* Not My Vibe (Down) */}
          <button
            onClick={onNotMyVibe}
            disabled={isSubmitting}
            className="flex flex-col items-center gap-1 p-3 min-w-[60px] min-h-[60px] rounded-xl text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all disabled:opacity-50"
            aria-label="Not my vibe"
          >
            <span className="text-2xl">&#x2193;</span>
            <span className="text-xs font-medium">Not Me</span>
          </button>

          {/* Save for Later (Up) */}
          <button
            onClick={onSave}
            disabled={isSubmitting}
            className="flex flex-col items-center gap-1 p-3 min-w-[60px] min-h-[60px] rounded-xl text-gray-400 hover:text-amber-500 hover:bg-amber-50 transition-all disabled:opacity-50"
            aria-label="Save for later"
          >
            <span className="text-2xl">&#x2191;</span>
            <span className="text-xs font-medium">Save</span>
          </button>

          {/* Answer indicator (Right) - only shows when ready */}
          <div
            className={`flex flex-col items-center gap-1 p-3 min-w-[60px] min-h-[60px] rounded-xl transition-all ${
              isAnswerValid()
                ? 'text-green-500 bg-green-50'
                : 'text-gray-300'
            }`}
          >
            <span className="text-2xl">&#x2192;</span>
            <span className="text-xs font-medium">Answer</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuestionCard;
