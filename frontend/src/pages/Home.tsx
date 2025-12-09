import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ProfileHealth } from '../components/ProfileHealth';
import { ProfileChat } from '../components/ProfileChat';

interface MemberOption {
  id: number;
  first_name: string | null;
  last_name: string | null;
  email: string;
}

interface MembersResponse {
  members: MemberOption[];
  total: number;
}

async function fetchMembers(): Promise<MembersResponse> {
  const response = await fetch('http://localhost:8000/api/v1/members?per_page=100');
  if (!response.ok) {
    throw new Error('Failed to fetch members');
  }
  return response.json();
}

export const Home: React.FC = () => {
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);

  const { data: membersData, isLoading: membersLoading } = useQuery({
    queryKey: ['members'],
    queryFn: fetchMembers,
  });

  const getMemberDisplayName = (member: MemberOption) => {
    const name = [member.first_name, member.last_name].filter(Boolean).join(' ');
    return name || member.email;
  };

  const sortedMembers = membersData?.members
    ? [...membersData.members].sort((a, b) => {
        const nameA = getMemberDisplayName(a).toLowerCase();
        const nameB = getMemberDisplayName(b).toLowerCase();
        return nameA.localeCompare(nameB);
      })
    : [];

  // Set default member once data loads (first alphabetically)
  React.useEffect(() => {
    if (sortedMembers.length && selectedMemberId === null) {
      setSelectedMemberId(sortedMembers[0].id);
    }
  }, [sortedMembers, selectedMemberId]);

  const selectedMember = sortedMembers.find(m => m.id === selectedMemberId);
  const selectedMemberName = selectedMember ? getMemberDisplayName(selectedMember) : '';

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-2xl shadow-lg p-6 text-center">
        <h1 className="text-2xl font-bold mb-2">
          Profile Optimizer
        </h1>
        <p className="text-indigo-100">
          AI-powered profile enrichment for White Rabbit Ashland members
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
        <label htmlFor="member-select" className="block text-sm font-medium text-gray-700 mb-2">
          Select a Member
        </label>
        {membersLoading ? (
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        ) : (
          <select
            id="member-select"
            value={selectedMemberId ?? ''}
            onChange={(e) => setSelectedMemberId(Number(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {sortedMembers.map((member) => (
              <option key={member.id} value={member.id}>
                {getMemberDisplayName(member)} ({member.email})
              </option>
            ))}
          </select>
        )}
      </div>

      {selectedMemberId && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <ProfileHealth memberId={selectedMemberId} />
          </div>
          <div>
            <ProfileChat memberId={selectedMemberId} memberName={selectedMemberName} />
          </div>
        </div>
      )}
    </div>
  );
};
