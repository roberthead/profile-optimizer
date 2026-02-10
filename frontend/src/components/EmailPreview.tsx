import React from 'react';
import { Mail, RefreshCw } from 'lucide-react';

interface EmailPreviewProps {
  subject: string;
  html: string;
  from?: string;
  to?: string;
  isLoading?: boolean;
  onRefresh?: () => void;
}

export const EmailPreview: React.FC<EmailPreviewProps> = ({
  subject,
  html,
  from = 'White Rabbit <hello@whiterabbitashland.com>',
  to = 'member@example.com',
  isLoading = false,
  onRefresh,
}) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Email Client Header */}
      <div className="bg-gray-100 border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Email Preview</span>
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

      {/* Email Metadata */}
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 space-y-2">
        <div className="flex items-start gap-2 text-sm">
          <span className="text-gray-500 w-16 flex-shrink-0">From:</span>
          <span className="text-gray-900">{from}</span>
        </div>
        <div className="flex items-start gap-2 text-sm">
          <span className="text-gray-500 w-16 flex-shrink-0">To:</span>
          <span className="text-gray-900">{to}</span>
        </div>
        <div className="flex items-start gap-2 text-sm">
          <span className="text-gray-500 w-16 flex-shrink-0">Subject:</span>
          <span className="text-gray-900 font-medium">{subject}</span>
        </div>
      </div>

      {/* Email Content */}
      <div className="relative">
        {isLoading ? (
          <div className="p-8">
            <div className="animate-pulse space-y-4">
              <div className="h-12 bg-gray-100 rounded"></div>
              <div className="h-32 bg-gray-100 rounded"></div>
              <div className="h-24 bg-gray-100 rounded"></div>
            </div>
          </div>
        ) : (
          <div className="email-content-frame">
            <iframe
              srcDoc={html}
              title="Email Preview"
              className="w-full border-0"
              style={{ minHeight: '500px' }}
              sandbox="allow-same-origin"
              onLoad={(e) => {
                // Auto-resize iframe to content height
                const iframe = e.target as HTMLIFrameElement;
                if (iframe.contentDocument) {
                  const height = iframe.contentDocument.documentElement.scrollHeight;
                  iframe.style.height = `${height + 20}px`;
                }
              }}
            />
          </div>
        )}
      </div>

      {/* Responsive Preview Toggle */}
      <div className="bg-gray-50 border-t border-gray-200 px-4 py-2">
        <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
          <span>Desktop Preview</span>
          <span className="text-gray-300">|</span>
          <span className="text-gray-400">Mobile preview coming soon</span>
        </div>
      </div>
    </div>
  );
};

export default EmailPreview;
