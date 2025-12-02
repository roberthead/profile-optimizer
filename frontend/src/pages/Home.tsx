import React from 'react';
import { ProfileHealth } from '../components/ProfileHealth';

export const Home: React.FC = () => {
  return (
    <div className="space-y-8">
      <div className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-2xl shadow-lg p-8 text-center">
        <h1 className="text-3xl font-bold mb-3">
          Welcome to Profile Optimizer
        </h1>
        <p className="text-lg text-indigo-100">
          Your AI-powered assistant for enriching White Rabbit Ashland member profiles.
        </p>
      </div>

      <ProfileHealth />
    </div>
  );
};
