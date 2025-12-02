import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight, Users, MapPin, Briefcase } from 'lucide-react';

interface MemberSummary {
  id: number;
  profile_id: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
  membership_status: string;
  location: string | null;
  role: string | null;
  skills_count: number;
  interests_count: number;
}

interface MembersListResponse {
  members: MemberSummary[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

const MEMBERSHIP_STATUSES = [
  { value: '', label: 'All Statuses' },
  { value: 'free', label: 'Free' },
  { value: 'active_create', label: 'Active Create' },
  { value: 'active_fellow', label: 'Active Fellow' },
  { value: 'active_team_member', label: 'Team Member' },
];

async function fetchMembers(
  page: number,
  search: string,
  membershipStatus: string
): Promise<MembersListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: '20',
  });

  if (search) params.set('search', search);
  if (membershipStatus) params.set('membership_status', membershipStatus);

  const response = await fetch(
    `http://localhost:8000/api/v1/members?${params}`
  );

  if (!response.ok) {
    throw new Error('Failed to fetch members');
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

export const MembersList: React.FC = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [membershipStatus, setMembershipStatus] = useState('');

  // Debounce search input
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['members', page, debouncedSearch, membershipStatus],
    queryFn: () => fetchMembers(page, debouncedSearch, membershipStatus),
  });

  if (error) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-red-200 p-8">
        <p className="text-red-600">Error loading members. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Members</h1>
          <p className="text-gray-600">
            {data ? `${data.total} members in the community` : 'Loading...'}
          </p>
        </div>
        <Users className="w-8 h-8 text-indigo-600" />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name, email, or bio..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <select
            value={membershipStatus}
            onChange={(e) => {
              setMembershipStatus(e.target.value);
              setPage(1);
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {MEMBERSHIP_STATUSES.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Members List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <div className="animate-pulse space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-100 rounded"></div>
              ))}
            </div>
          </div>
        ) : data?.members.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No members found matching your criteria.
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {data?.members.map((member) => (
              <li key={member.id}>
                <Link
                  to={`/members/${member.id}`}
                  className="block hover:bg-gray-50 transition-colors"
                >
                  <div className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3">
                          <p className="text-lg font-medium text-gray-900 truncate">
                            {member.first_name || member.last_name
                              ? `${member.first_name || ''} ${member.last_name || ''}`.trim()
                              : member.email}
                          </p>
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMembershipBadgeColor(
                              member.membership_status
                            )}`}
                          >
                            {formatMembershipStatus(member.membership_status)}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-4 text-sm text-gray-500">
                          {member.role && (
                            <span className="flex items-center gap-1">
                              <Briefcase className="w-4 h-4" />
                              {member.role}
                            </span>
                          )}
                          {member.location && (
                            <span className="flex items-center gap-1">
                              <MapPin className="w-4 h-4" />
                              {member.location}
                            </span>
                          )}
                          {(member.first_name || member.last_name) && (
                            <span className="text-gray-400">{member.email}</span>
                          )}
                        </div>
                      </div>
                      <div className="ml-4 flex items-center gap-4 text-sm text-gray-500">
                        {member.skills_count > 0 && (
                          <span>{member.skills_count} skills</span>
                        )}
                        {member.interests_count > 0 && (
                          <span>{member.interests_count} interests</span>
                        )}
                        <ChevronRight className="w-5 h-5 text-gray-400" />
                      </div>
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <p className="text-sm text-gray-700">
              Showing{' '}
              <span className="font-medium">
                {(data.page - 1) * data.per_page + 1}
              </span>{' '}
              to{' '}
              <span className="font-medium">
                {Math.min(data.page * data.per_page, data.total)}
              </span>{' '}
              of <span className="font-medium">{data.total}</span> members
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-sm text-gray-700">
                Page {data.page} of {data.total_pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages}
                className="p-2 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
