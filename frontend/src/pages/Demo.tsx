import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  User, Users, Monitor, Smartphone, Mail, MessageSquare,
  Network, Database, Calendar, Clock, ChevronRight, Sparkles,
  RefreshCw
} from 'lucide-react';
import api from '../api/client';

interface DemoSection {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  type: 'individual' | 'group' | 'system';
}

const sections: DemoSection[] = [
  {
    id: 'individual-question',
    title: 'Individual Questions',
    description: 'Questions targeted to a specific member based on their profile, patterns, and connections',
    icon: <User className="w-6 h-6" />,
    type: 'individual',
  },
  {
    id: 'group-question',
    title: 'Group Questions',
    description: 'Questions for whoever is present, based on time of day, meetings, and who might be there',
    icon: <Users className="w-6 h-6" />,
    type: 'group',
  },
  {
    id: 'mobile-swipe',
    title: 'Mobile Swipe',
    description: 'Swipe interface for answering questions on phone',
    icon: <Smartphone className="w-6 h-6" />,
    type: 'individual',
  },
  {
    id: 'clubhouse-display',
    title: 'Clubhouse Display',
    description: 'Full-screen display for the clubhouse TV/monitor',
    icon: <Monitor className="w-6 h-6" />,
    type: 'group',
  },
  {
    id: 'email-preview',
    title: 'Email Templates',
    description: 'Weekly digest and event recommendation emails',
    icon: <Mail className="w-6 h-6" />,
    type: 'individual',
  },
  {
    id: 'sms-preview',
    title: 'SMS Messages',
    description: 'Question nudges, event alerts, connection nudges',
    icon: <MessageSquare className="w-6 h-6" />,
    type: 'individual',
  },
  {
    id: 'graph',
    title: 'Community Graph',
    description: 'Interactive visualization of member connections',
    icon: <Network className="w-6 h-6" />,
    type: 'system',
  },
  {
    id: 'data-model',
    title: 'Data Model',
    description: 'Entity explorer with live stats',
    icon: <Database className="w-6 h-6" />,
    type: 'system',
  },
];

const MEETING_OPTIONS = [
  { value: '', label: 'No meeting selected' },
  { value: 'AI Cohort Meeting', label: 'AI Cohort Meeting' },
  { value: 'Creator Workshop', label: 'Creator Workshop' },
  { value: 'Startup Office Hours', label: 'Startup Office Hours' },
  { value: 'Community Dinner', label: 'Community Dinner' },
  { value: 'Demo Day', label: 'Demo Day' },
  { value: 'Social Hour', label: 'Social Hour' },
];

const TIME_OPTIONS = [
  { value: 'morning', label: 'Morning (lighter questions)' },
  { value: 'afternoon', label: 'Afternoon (balanced)' },
  { value: 'evening', label: 'Evening (deeper)' },
  { value: 'night', label: 'Night (philosophical)' },
];

export default function Demo() {
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const [activeSection, setActiveSection] = useState<string>('individual-question');

  // Group context controls
  const [selectedTimeOfDay, setSelectedTimeOfDay] = useState<string>(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'morning';
    if (hour < 17) return 'afternoon';
    if (hour < 21) return 'evening';
    return 'night';
  });
  const [selectedMeeting, setSelectedMeeting] = useState<string>('');
  const [selectedPresentMembers, setSelectedPresentMembers] = useState<number[]>([]);

  // Fetch members for selector
  const { data: membersData } = useQuery({
    queryKey: ['members'],
    queryFn: async () => {
      const response = await api.get('/members?per_page=100');
      return response.data;
    },
  });

  // Fetch individual question for selected member
  const { data: individualQuestion, isLoading: loadingIndividual, refetch: refetchIndividual } = useQuery({
    queryKey: ['demo-individual-question', selectedMemberId],
    queryFn: async () => {
      const response = await api.get(`/mobile/questions/next?member_id=${selectedMemberId}`);
      return response.data;
    },
    enabled: !!selectedMemberId,
  });

  // Fetch group question using the agent-powered endpoint
  const { data: groupQuestion, isLoading: loadingGroup, refetch: refetchGroup } = useQuery({
    queryKey: ['demo-group-question', selectedTimeOfDay, selectedMeeting, selectedPresentMembers],
    queryFn: async () => {
      const response = await api.post('/display/group-question', {
        time_of_day: selectedTimeOfDay,
        day_of_week: new Date().toLocaleDateString('en-US', { weekday: 'long' }),
        meeting_name: selectedMeeting || null,
        present_member_ids: selectedPresentMembers.length >= 2 ? selectedPresentMembers : null,
      });
      return response.data;
    },
  });

  // Build group context for display
  const groupContext = {
    timeOfDay: selectedTimeOfDay,
    dayOfWeek: new Date().toLocaleDateString('en-US', { weekday: 'long' }),
    possibleMeetings: selectedMeeting ? [selectedMeeting] : [],
    presentMemberCount: selectedPresentMembers.length,
  };

  const members = membersData?.members || [];

  // Toggle member presence
  const toggleMemberPresence = (memberId: number) => {
    setSelectedPresentMembers(prev =>
      prev.includes(memberId)
        ? prev.filter(id => id !== memberId)
        : [...prev, memberId]
    );
  };

  const renderQuestionCard = (
    question: any,
    type: 'individual' | 'group',
    context?: any,
    isLoading?: boolean
  ) => {
    if (isLoading) {
      return (
        <div className="bg-white rounded-xl shadow-lg p-6 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-6 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-6 bg-gray-200 rounded w-1/2"></div>
        </div>
      );
    }

    if (!question) {
      return (
        <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-300 p-8 text-center">
          <p className="text-gray-500">
            {type === 'individual'
              ? 'Select a member to see their targeted question'
              : 'No question available'}
          </p>
        </div>
      );
    }

    return (
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        {/* Header */}
        <div className={`px-6 py-4 ${type === 'individual' ? 'bg-indigo-600' : 'bg-violet-600'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-white">
              {type === 'individual' ? <User className="w-5 h-5" /> : <Users className="w-5 h-5" />}
              <span className="font-medium">
                {type === 'individual' ? 'For You' : 'For the Group'}
              </span>
            </div>
            {question.vibe && (
              <span className="px-2 py-1 bg-white/20 rounded-full text-xs text-white">
                {question.vibe}
              </span>
            )}
          </div>
        </div>

        {/* Question */}
        <div className="p-6">
          <p className="text-xl font-medium text-gray-900 mb-4">
            {question.question || question.question_text}
          </p>

          {/* Context */}
          {question.context && (
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <p className="text-sm text-gray-600">{question.context}</p>
            </div>
          )}

          {/* Category & Difficulty */}
          <div className="flex items-center gap-2 mb-4">
            {question.category && (
              <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs">
                {question.category.replace('_', ' ')}
              </span>
            )}
            {question.difficulty_level && (
              <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                Level {question.difficulty_level}
              </span>
            )}
          </div>

          {/* Group Context */}
          {type === 'group' && context && (
            <div className="border-t pt-4 mt-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Group Context</p>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {context.dayOfWeek} {context.timeOfDay}
                </div>
                {context.possibleMeetings?.length > 0 && (
                  <div className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    {context.possibleMeetings[0]}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Recent Answers (for group) */}
          {type === 'group' && question.recent_answers?.length > 0 && (
            <div className="border-t pt-4 mt-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Recent Answers</p>
              <div className="space-y-2">
                {question.recent_answers.slice(0, 3).map((answer: any, i: number) => (
                  <div key={i} className="text-sm text-gray-600">
                    <span className="font-medium">{answer.member_name}:</span> "{answer.text}"
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderSectionContent = () => {
    switch (activeSection) {
      case 'individual-question':
      case 'group-question':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Individual Question */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <User className="w-5 h-5 text-indigo-600" />
                  Individual Question
                </h3>
                <button
                  onClick={() => refetchIndividual()}
                  className="p-2 text-gray-400 hover:text-gray-600"
                  title="Refresh"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

              {/* Member Selector */}
              <div className="mb-4">
                <select
                  value={selectedMemberId || ''}
                  onChange={(e) => setSelectedMemberId(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="">Select a member...</option>
                  {members.map((member: any) => (
                    <option key={member.id} value={member.id}>
                      {member.first_name} {member.last_name}
                    </option>
                  ))}
                </select>
              </div>

              {renderQuestionCard(individualQuestion, 'individual', null, loadingIndividual)}

              <p className="mt-4 text-sm text-gray-500">
                This question is targeted based on their profile, patterns they belong to,
                connections with other members, and their taste profile preferences.
              </p>
            </div>

            {/* Group Question */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Users className="w-5 h-5 text-violet-600" />
                  Group Question
                  <span className="text-xs font-normal text-violet-500 bg-violet-100 px-2 py-0.5 rounded-full">
                    Agent-Powered
                  </span>
                </h3>
                <button
                  onClick={() => refetchGroup()}
                  className="p-2 text-gray-400 hover:text-gray-600"
                  title="Refresh"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

              {/* Group Context Controls */}
              <div className="mb-4 space-y-3 p-4 bg-violet-50 rounded-lg border border-violet-100">
                <p className="text-xs text-violet-600 uppercase tracking-wide font-medium">Context Controls</p>

                {/* Time of Day */}
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Time of Day</label>
                  <select
                    value={selectedTimeOfDay}
                    onChange={(e) => setSelectedTimeOfDay(e.target.value)}
                    className="w-full px-3 py-2 border border-violet-200 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 text-sm bg-white"
                  >
                    {TIME_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* Meeting */}
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Meeting Context</label>
                  <select
                    value={selectedMeeting}
                    onChange={(e) => setSelectedMeeting(e.target.value)}
                    className="w-full px-3 py-2 border border-violet-200 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 text-sm bg-white"
                  >
                    {MEETING_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* Present Members */}
                <div>
                  <label className="block text-sm text-gray-600 mb-1">
                    Who's Present? ({selectedPresentMembers.length} selected)
                    {selectedPresentMembers.length >= 2 && (
                      <span className="text-violet-600 ml-1">• Agent analyzing relationships</span>
                    )}
                  </label>
                  <div className="max-h-32 overflow-y-auto bg-white border border-violet-200 rounded-lg p-2">
                    <div className="flex flex-wrap gap-1">
                      {members.slice(0, 20).map((member: any) => (
                        <button
                          key={member.id}
                          onClick={() => toggleMemberPresence(member.id)}
                          className={`px-2 py-1 rounded text-xs transition-colors ${
                            selectedPresentMembers.includes(member.id)
                              ? 'bg-violet-600 text-white'
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                          }`}
                        >
                          {member.first_name}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Targeting Reason (from agent) */}
              {groupQuestion?.targeting_reason && (
                <div className="mb-4 p-3 bg-green-50 rounded-lg border border-green-100">
                  <div className="flex items-start gap-2">
                    <Sparkles className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-green-600 uppercase tracking-wide font-medium mb-1">Agent Reasoning</p>
                      <p className="text-sm text-green-700">{groupQuestion.targeting_reason}</p>
                    </div>
                  </div>
                </div>
              )}

              {renderQuestionCard(groupQuestion, 'group', groupContext, loadingGroup)}

              <p className="mt-4 text-sm text-gray-500">
                {selectedPresentMembers.length >= 2
                  ? 'The GroupQuestionAgent analyzed profiles, connections, and patterns of present members to select this question.'
                  : 'Add 2+ present members above to enable agent-powered question selection based on their profiles and connections.'}
              </p>
            </div>
          </div>
        );

      case 'mobile-swipe':
        return (
          <div className="text-center py-8">
            <Smartphone className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Mobile Swipe Interface</h3>
            <p className="text-gray-600 mb-4">Swipe through questions on your phone</p>
            <a
              href="/mobile"
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Open Mobile View <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        );

      case 'clubhouse-display':
        return (
          <div className="text-center py-8">
            <Monitor className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Clubhouse Display</h3>
            <p className="text-gray-600 mb-4">Full-screen display for the clubhouse TV</p>
            <a
              href="/display"
              className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white rounded-lg hover:bg-violet-700"
            >
              Open Display View <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        );

      case 'email-preview':
      case 'sms-preview':
        return (
          <div className="text-center py-8">
            <Mail className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Message Templates</h3>
            <p className="text-gray-600 mb-4">Preview email and SMS templates</p>
            <a
              href="/messages"
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Open Messages View <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        );

      case 'graph':
        return (
          <div className="text-center py-8">
            <Network className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Community Graph</h3>
            <p className="text-gray-600 mb-4">Interactive visualization of member connections</p>
            <a
              href="/graph"
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Open Graph View <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        );

      case 'data-model':
        return (
          <div className="text-center py-8">
            <Database className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Data Model Explorer</h3>
            <p className="text-gray-600 mb-4">View the database schema and live stats</p>
            <a
              href="/data-model"
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Open Data Model <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold mb-2">🐰 Profile Optimizer Demo</h1>
          <p className="text-indigo-100">
            Explore the different user engagement touchpoints
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1 overflow-x-auto py-2">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
                  activeSection === section.id
                    ? section.type === 'individual'
                      ? 'bg-indigo-100 text-indigo-700'
                      : section.type === 'group'
                      ? 'bg-violet-100 text-violet-700'
                      : 'bg-gray-100 text-gray-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {section.icon}
                <span className="text-sm font-medium">{section.title}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-indigo-600"></div>
            <span className="text-gray-600">Individual (for a specific member)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-violet-600"></div>
            <span className="text-gray-600">Group (for whoever is present)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-gray-400"></div>
            <span className="text-gray-600">System (infrastructure)</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {renderSectionContent()}
      </div>

      {/* Quick Links Footer */}
      <div className="bg-white border-t mt-8">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <h3 className="text-lg font-semibold mb-4">Quick Links</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <a href="/mobile" className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 text-center">
              <Smartphone className="w-8 h-8 mx-auto mb-2 text-indigo-600" />
              <span className="text-sm font-medium">Mobile</span>
            </a>
            <a href="/display" className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 text-center">
              <Monitor className="w-8 h-8 mx-auto mb-2 text-violet-600" />
              <span className="text-sm font-medium">Display</span>
            </a>
            <a href="/graph" className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 text-center">
              <Network className="w-8 h-8 mx-auto mb-2 text-indigo-600" />
              <span className="text-sm font-medium">Graph</span>
            </a>
            <a href="/messages" className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 text-center">
              <Mail className="w-8 h-8 mx-auto mb-2 text-indigo-600" />
              <span className="text-sm font-medium">Messages</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
