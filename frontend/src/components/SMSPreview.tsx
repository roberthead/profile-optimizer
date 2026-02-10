import React from 'react';
import { Smartphone, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';

interface SMSPreviewProps {
  text: string;
  characterCount: number;
  isWithinLimit: boolean;
  sender?: string;
  isLoading?: boolean;
  onRefresh?: () => void;
}

const SMS_LIMIT = 160;

export const SMSPreview: React.FC<SMSPreviewProps> = ({
  text,
  characterCount,
  isWithinLimit,
  sender = 'White Rabbit',
  isLoading = false,
  onRefresh,
}) => {
  const getCharacterCountColor = () => {
    if (characterCount <= 140) return 'text-green-600';
    if (characterCount <= SMS_LIMIT) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Phone Header */}
      <div className="bg-gray-100 border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">SMS Preview</span>
          </div>
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              title="Refresh preview"
            >
              <RefreshCw className={`w-4 h-4 text-gray-500 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Phone Frame */}
      <div className="bg-gradient-to-b from-gray-900 to-gray-800 p-6">
        <div className="bg-black rounded-[2rem] p-2 max-w-xs mx-auto">
          {/* Phone Screen */}
          <div className="bg-white rounded-[1.5rem] overflow-hidden">
            {/* Status Bar */}
            <div className="bg-gray-100 px-4 py-2 flex items-center justify-between">
              <span className="text-xs text-gray-500">9:41</span>
              <div className="flex items-center gap-1">
                <div className="w-4 h-2 flex gap-0.5">
                  <div className="w-1 h-full bg-gray-400 rounded-full"></div>
                  <div className="w-1 h-full bg-gray-400 rounded-full"></div>
                  <div className="w-1 h-full bg-gray-400 rounded-full"></div>
                  <div className="w-1 h-full bg-gray-300 rounded-full"></div>
                </div>
                <div className="w-5 h-2 bg-gray-400 rounded-sm"></div>
              </div>
            </div>

            {/* Message Header */}
            <div className="px-4 py-3 border-b border-gray-200 text-center">
              <div className="w-10 h-10 bg-indigo-100 rounded-full mx-auto flex items-center justify-center mb-1">
                <span className="text-lg">&#x1F430;</span>
              </div>
              <p className="text-sm font-medium text-gray-900">{sender}</p>
            </div>

            {/* Message Content */}
            <div className="p-4 min-h-[200px] bg-gray-50">
              {isLoading ? (
                <div className="animate-pulse">
                  <div className="h-16 bg-gray-200 rounded-2xl rounded-tl-sm"></div>
                </div>
              ) : (
                <div className="flex justify-start">
                  <div className="max-w-[85%]">
                    <div className="bg-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
                      <p className="text-sm text-gray-900 whitespace-pre-wrap">{text}</p>
                    </div>
                    <p className="text-xs text-gray-400 mt-1 ml-2">Now</p>
                  </div>
                </div>
              )}
            </div>

            {/* Reply Input */}
            <div className="px-4 py-3 border-t border-gray-200 bg-white">
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-100 rounded-full px-4 py-2">
                  <span className="text-sm text-gray-400">iMessage</span>
                </div>
                <div className="w-8 h-8 bg-indigo-500 rounded-full flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Character Count Footer */}
      <div className="bg-gray-50 border-t border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isWithinLimit ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-500" />
            )}
            <span className="text-sm text-gray-600">
              {isWithinLimit ? 'Within SMS limit' : 'Exceeds SMS limit'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${getCharacterCountColor()}`}>
              {characterCount}
            </span>
            <span className="text-sm text-gray-400">/ {SMS_LIMIT}</span>
          </div>
        </div>

        {/* Character Progress Bar */}
        <div className="mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              characterCount <= 140
                ? 'bg-green-500'
                : characterCount <= SMS_LIMIT
                ? 'bg-yellow-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${Math.min(100, (characterCount / SMS_LIMIT) * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default SMSPreview;
