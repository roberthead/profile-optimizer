import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface ProfileHealthData {
  completeness_score: number;
  missing_fields: string[];
  optional_missing: string[];
  last_calculated: string;
}

async function fetchProfileHealth(): Promise<ProfileHealthData> {
  const response = await fetch('http://localhost:8000/api/v1/profile/evaluate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch profile health');
  }

  return response.json();
}

export const ProfileHealth: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['profileHealth'],
    queryFn: fetchProfileHealth,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-24 bg-gray-200 rounded mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-red-200 p-8">
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle className="w-5 h-5" />
          <p>Error loading profile health. Please try again.</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { completeness_score, missing_fields, optional_missing } = data;

  // Determine color based on score
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const allMissingFields = [...missing_fields, ...optional_missing];
  const isComplete = completeness_score === 100;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
      <h2 className="text-2xl font-semibold text-gray-900 mb-2">Profile Health</h2>
      <p className="text-gray-600 mb-6">See how complete your profile is</p>

      {/* Score Display */}
      <div className="mb-6">
        <div className="flex items-baseline gap-3 mb-2">
          <span className={`text-5xl font-bold ${getScoreColor(completeness_score)}`}>
            {completeness_score}%
          </span>
          <span className="text-gray-500">complete</span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full ${getProgressColor(completeness_score)} transition-all duration-500`}
            style={{ width: `${completeness_score}%` }}
          ></div>
        </div>
      </div>

      {/* Complete State */}
      {isComplete && (
        <div className="flex items-center gap-2 p-4 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle2 className="w-5 h-5 text-green-600" />
          <div>
            <p className="font-medium text-green-900">Your profile is 100% complete!</p>
            <p className="text-sm text-green-700">Great job keeping your information up to date.</p>
          </div>
        </div>
      )}

      {/* Missing Fields */}
      {!isComplete && allMissingFields.length > 0 && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Missing Information</h3>
          <div className="space-y-2">
            {missing_fields.length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-1">Required:</p>
                <ul className="space-y-1">
                  {missing_fields.map((field) => (
                    <li
                      key={field}
                      className="flex items-center gap-2 text-sm text-gray-600 pl-4"
                    >
                      <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                      {field}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {optional_missing.length > 0 && (
              <div className="mt-3">
                <p className="text-sm font-medium text-gray-700 mb-1">Optional:</p>
                <ul className="space-y-1">
                  {optional_missing.map((field) => (
                    <li
                      key={field}
                      className="flex items-center gap-2 text-sm text-gray-600 pl-4"
                    >
                      <span className="w-1.5 h-1.5 bg-gray-400 rounded-full"></span>
                      {field}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
