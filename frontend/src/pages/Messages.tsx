import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Mail, Smartphone, ChevronDown, RefreshCw } from 'lucide-react';
import { EmailPreview } from '../components/EmailPreview';
import { SMSPreview } from '../components/SMSPreview';

interface MemberSummary {
  id: number;
  profile_id: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
}

interface MembersListResponse {
  members: MemberSummary[];
  total: number;
}

interface EmailContent {
  subject: string;
  html: string;
  plain_text: string;
}

interface SMSContent {
  text: string;
  character_count: number;
  is_within_limit: boolean;
}

type EmailType = 'weekly-digest' | 'event-recommendation';
type SMSType = 'question-nudge' | 'event-alert' | 'connection-nudge';

const API_BASE = 'http://localhost:8000/api/v1';

async function fetchMembers(): Promise<MembersListResponse> {
  const response = await fetch(`${API_BASE}/members?per_page=100`);
  if (!response.ok) throw new Error('Failed to fetch members');
  return response.json();
}

async function fetchEmailContent(memberId: number, type: EmailType): Promise<EmailContent> {
  const endpoint = type === 'weekly-digest'
    ? `${API_BASE}/messages/email/weekly-digest/${memberId}`
    : `${API_BASE}/messages/email/event-recommendation/${memberId}`;
  const response = await fetch(endpoint);
  if (!response.ok) throw new Error('Failed to fetch email content');
  return response.json();
}

async function fetchSMSContent(memberId: number, type: SMSType): Promise<SMSContent> {
  let endpoint = '';
  switch (type) {
    case 'question-nudge':
      endpoint = `${API_BASE}/messages/sms/question-nudge/${memberId}`;
      break;
    case 'event-alert':
      endpoint = `${API_BASE}/messages/sms/event-alert/${memberId}/community-gathering`;
      break;
    case 'connection-nudge':
      endpoint = `${API_BASE}/messages/sms/connection-nudge/${memberId}`;
      break;
  }
  const response = await fetch(endpoint);
  if (!response.ok) throw new Error('Failed to fetch SMS content');
  return response.json();
}

const EMAIL_TYPES: { value: EmailType; label: string; description: string }[] = [
  {
    value: 'weekly-digest',
    label: 'Weekly Digest',
    description: 'Connections, questions, events, and stats'
  },
  {
    value: 'event-recommendation',
    label: 'Event Recommendation',
    description: 'Personalized event suggestions'
  },
];

const SMS_TYPES: { value: SMSType; label: string; description: string }[] = [
  {
    value: 'question-nudge',
    label: 'Question Nudge',
    description: 'Quick question from their queue'
  },
  {
    value: 'event-alert',
    label: 'Event Alert',
    description: 'Event happening soon'
  },
  {
    value: 'connection-nudge',
    label: 'Connection Nudge',
    description: 'Someone they should meet'
  },
];

export const Messages: React.FC = () => {
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const [selectedEmailType, setSelectedEmailType] = useState<EmailType>('weekly-digest');
  const [selectedSMSType, setSelectedSMSType] = useState<SMSType>('question-nudge');

  // Fetch members for dropdown
  const { data: membersData, isLoading: membersLoading } = useQuery({
    queryKey: ['members-list'],
    queryFn: fetchMembers,
  });

  // Fetch email content
  const {
    data: emailContent,
    isLoading: emailLoading,
    refetch: refetchEmail,
  } = useQuery({
    queryKey: ['email-content', selectedMemberId, selectedEmailType],
    queryFn: () => fetchEmailContent(selectedMemberId!, selectedEmailType),
    enabled: selectedMemberId !== null,
  });

  // Fetch SMS content
  const {
    data: smsContent,
    isLoading: smsLoading,
    refetch: refetchSMS,
  } = useQuery({
    queryKey: ['sms-content', selectedMemberId, selectedSMSType],
    queryFn: () => fetchSMSContent(selectedMemberId!, selectedSMSType),
    enabled: selectedMemberId !== null,
  });

  const selectedMember = membersData?.members.find(m => m.id === selectedMemberId);
  const memberEmail = selectedMember?.email || 'member@example.com';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Message Templates</h1>
          <p className="text-gray-600">
            Preview email and SMS messages for community members
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Mail className="w-6 h-6 text-indigo-600" />
          <Smartphone className="w-6 h-6 text-indigo-600" />
        </div>
      </div>

      {/* Member Selector */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select a Member
        </label>
        <div className="relative">
          <select
            value={selectedMemberId || ''}
            onChange={(e) => setSelectedMemberId(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 appearance-none bg-white pr-10"
            disabled={membersLoading}
          >
            <option value="">
              {membersLoading ? 'Loading members...' : 'Choose a member to preview messages'}
            </option>
            {membersData?.members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.first_name || member.last_name
                  ? `${member.first_name || ''} ${member.last_name || ''}`.trim()
                  : member.email}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Message Previews */}
      {selectedMemberId ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Email Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Mail className="w-5 h-5 text-indigo-600" />
                Email Preview
              </h2>
              <button
                onClick={() => refetchEmail()}
                disabled={emailLoading}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
                title="Refresh email"
              >
                <RefreshCw className={`w-4 h-4 text-gray-500 ${emailLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Email Type Selector */}
            <div className="flex flex-wrap gap-2">
              {EMAIL_TYPES.map((type) => (
                <button
                  key={type.value}
                  onClick={() => setSelectedEmailType(type.value)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedEmailType === type.value
                      ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                      : 'bg-gray-100 text-gray-600 border border-transparent hover:bg-gray-200'
                  }`}
                  title={type.description}
                >
                  {type.label}
                </button>
              ))}
            </div>

            {/* Email Preview */}
            {emailContent ? (
              <EmailPreview
                subject={emailContent.subject}
                html={emailContent.html}
                to={memberEmail}
                isLoading={emailLoading}
                onRefresh={() => refetchEmail()}
              />
            ) : emailLoading ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
                <div className="animate-pulse space-y-4">
                  <div className="h-8 bg-gray-100 rounded w-2/3"></div>
                  <div className="h-4 bg-gray-100 rounded w-1/2"></div>
                  <div className="h-64 bg-gray-100 rounded"></div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center text-gray-500">
                Select a member to preview emails
              </div>
            )}
          </div>

          {/* SMS Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-indigo-600" />
                SMS Preview
              </h2>
              <button
                onClick={() => refetchSMS()}
                disabled={smsLoading}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
                title="Refresh SMS"
              >
                <RefreshCw className={`w-4 h-4 text-gray-500 ${smsLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* SMS Type Selector */}
            <div className="flex flex-wrap gap-2">
              {SMS_TYPES.map((type) => (
                <button
                  key={type.value}
                  onClick={() => setSelectedSMSType(type.value)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedSMSType === type.value
                      ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                      : 'bg-gray-100 text-gray-600 border border-transparent hover:bg-gray-200'
                  }`}
                  title={type.description}
                >
                  {type.label}
                </button>
              ))}
            </div>

            {/* SMS Preview */}
            {smsContent ? (
              <SMSPreview
                text={smsContent.text}
                characterCount={smsContent.character_count}
                isWithinLimit={smsContent.is_within_limit}
                isLoading={smsLoading}
                onRefresh={() => refetchSMS()}
              />
            ) : smsLoading ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
                <div className="animate-pulse space-y-4">
                  <div className="h-8 bg-gray-100 rounded w-1/2"></div>
                  <div className="h-48 bg-gray-100 rounded"></div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center text-gray-500">
                Select a member to preview SMS messages
              </div>
            )}

            {/* SMS Type Descriptions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">SMS Message Types</h3>
              <div className="space-y-2">
                {SMS_TYPES.map((type) => (
                  <div
                    key={type.value}
                    className={`p-3 rounded-lg transition-colors ${
                      selectedSMSType === type.value
                        ? 'bg-indigo-50 border border-indigo-100'
                        : 'bg-gray-50'
                    }`}
                  >
                    <p className="text-sm font-medium text-gray-800">{type.label}</p>
                    <p className="text-xs text-gray-500">{type.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-12 text-center">
          <div className="flex justify-center gap-4 mb-4">
            <Mail className="w-12 h-12 text-gray-300" />
            <Smartphone className="w-12 h-12 text-gray-300" />
          </div>
          <p className="text-gray-500 text-lg">
            Select a member above to preview their personalized messages
          </p>
          <p className="text-gray-400 text-sm mt-2">
            You'll see email and SMS templates customized for their profile
          </p>
        </div>
      )}

      {/* Info Footer */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3">About Message Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <p className="font-medium text-gray-800 mb-1">Email Templates</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Weekly digest with connections, questions, and events</li>
              <li>Personalized event recommendations</li>
              <li>HTML with responsive design</li>
              <li>White Rabbit branding throughout</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-gray-800 mb-1">SMS Templates</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Question nudges from targeted queue</li>
              <li>Event alerts with friend context</li>
              <li>Connection introductions</li>
              <li>Under 160 characters for single segment</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Messages;
