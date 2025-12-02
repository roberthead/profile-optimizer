import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Mail,
  MapPin,
  Briefcase,
  Building,
  Globe,
  User,
  Tag,
  MessageSquare,
} from 'lucide-react';

interface MemberDetailData {
  id: number;
  profile_id: string;
  clerk_user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  bio: string | null;
  company: string | null;
  role: string | null;
  website: string | null;
  location: string | null;
  membership_status: string;
  is_public: boolean;
  urls: string[];
  roles: string[];
  prompt_responses: string[];
  skills: string[];
  interests: string[];
  all_traits: string[];
}

async function fetchMember(id: string): Promise<MemberDetailData> {
  const response = await fetch(`http://localhost:8000/api/v1/members/${id}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Member not found');
    }
    throw new Error('Failed to fetch member');
  }

  return response.json();
}

function getMembershipBadgeColor(status: string): string {
  switch (status) {
    case 'active_create':
      return 'bg-green-100 text-green-800';
    case 'active_fellow':
      return 'bg-blue-100 text-blue-800';
    case 'active_team_member':
      return 'bg-purple-100 text-purple-800';
    case 'free':
      return 'bg-gray-100 text-gray-800';
    case 'cancelled':
    case 'expired':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-yellow-100 text-yellow-800';
  }
}

function formatMembershipStatus(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

const Section: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}> = ({ title, icon, children }) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <div className="flex items-center gap-2 mb-4">
      <span className="text-indigo-600">{icon}</span>
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
    </div>
    {children}
  </div>
);

export const MemberDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const { data: member, isLoading, error } = useQuery({
    queryKey: ['member', id],
    queryFn: () => fetchMember(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 w-32 bg-gray-200 rounded mb-6"></div>
          <div className="h-32 bg-gray-200 rounded-xl mb-6"></div>
          <div className="h-48 bg-gray-200 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error || !member) {
    return (
      <div className="space-y-6">
        <Link
          to="/members"
          className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Members
        </Link>
        <div className="bg-white rounded-xl shadow-sm border border-red-200 p-8">
          <p className="text-red-600">
            {error instanceof Error ? error.message : 'Error loading member'}
          </p>
        </div>
      </div>
    );
  }

  const displayName =
    member.first_name || member.last_name
      ? `${member.first_name || ''} ${member.last_name || ''}`.trim()
      : 'Unnamed Member';

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <Link
        to="/members"
        className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-800"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Members
      </Link>

      {/* Header Card */}
      <div className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-2xl shadow-lg p-8">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{displayName}</h1>
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getMembershipBadgeColor(
                  member.membership_status
                )}`}
              >
                {formatMembershipStatus(member.membership_status)}
              </span>
            </div>
            {member.role && (
              <p className="text-xl text-indigo-100 mb-1">{member.role}</p>
            )}
            {member.company && (
              <p className="text-indigo-200 flex items-center gap-2">
                <Building className="w-4 h-4" />
                {member.company}
              </p>
            )}
          </div>
          <div className="text-right text-sm text-indigo-200">
            <p>ID: {member.id}</p>
            <p className="text-xs mt-1 font-mono">{member.profile_id}</p>
          </div>
        </div>

        {/* Contact Info */}
        <div className="mt-6 flex flex-wrap gap-6 text-sm">
          <span className="flex items-center gap-2">
            <Mail className="w-4 h-4" />
            {member.email}
          </span>
          {member.location && (
            <span className="flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              {member.location}
            </span>
          )}
          {member.website && (
            <a
              href={member.website.startsWith('http') ? member.website : `https://${member.website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 hover:text-white/80"
            >
              <Globe className="w-4 h-4" />
              {member.website}
            </a>
          )}
        </div>
      </div>

      {/* Bio */}
      {member.bio && (
        <Section title="Bio" icon={<User className="w-5 h-5" />}>
          <p className="text-gray-700 whitespace-pre-wrap">{member.bio}</p>
        </Section>
      )}

      {/* Skills & Interests */}
      <div className="grid md:grid-cols-2 gap-6">
        {member.skills.length > 0 && (
          <Section title="Skills" icon={<Briefcase className="w-5 h-5" />}>
            <div className="flex flex-wrap gap-2">
              {member.skills.map((skill, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800"
                >
                  {skill}
                </span>
              ))}
            </div>
          </Section>
        )}

        {member.interests.length > 0 && (
          <Section title="Interests" icon={<Tag className="w-5 h-5" />}>
            <div className="flex flex-wrap gap-2">
              {member.interests.map((interest, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                >
                  {interest}
                </span>
              ))}
            </div>
          </Section>
        )}
      </div>

      {/* Prompt Responses */}
      {member.prompt_responses.length > 0 && (
        <Section
          title="Profile Responses"
          icon={<MessageSquare className="w-5 h-5" />}
        >
          <div className="space-y-4">
            {member.prompt_responses.map((response, index) => (
              <div
                key={index}
                className="p-4 bg-gray-50 rounded-lg border border-gray-200"
              >
                <p className="text-gray-700 whitespace-pre-wrap">{response}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Debug Info (collapsible) */}
      <details className="bg-gray-100 rounded-xl p-4">
        <summary className="cursor-pointer text-sm font-medium text-gray-600">
          Raw Data (for debugging)
        </summary>
        <pre className="mt-4 text-xs overflow-auto bg-gray-900 text-green-400 p-4 rounded-lg">
          {JSON.stringify(member, null, 2)}
        </pre>
      </details>
    </div>
  );
};
