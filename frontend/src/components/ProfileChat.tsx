import React, { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Send, Bot, User, Lightbulb, RotateCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Suggestion {
  id: number;
  field_name: string;
  suggested_value: string;
  reasoning: string;
}

interface ChatResponse {
  response: string;
  session_id: string;
  suggestions_made: Suggestion[];
}

interface ChatHistoryResponse {
  messages: Message[];
  session_id: string;
}

interface ProfileChatProps {
  memberId: number;
  memberName: string;
}

const getSessionKey = (memberId: number) => `profile-chat-session-${memberId}`;

async function sendMessage(memberId: number, message: string, sessionId: string | null): Promise<ChatResponse> {
  const response = await fetch('http://localhost:8000/api/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      member_id: memberId,
      message,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to send message');
  }

  return response.json();
}

async function fetchChatHistory(memberId: number, sessionId: string): Promise<ChatHistoryResponse> {
  const response = await fetch(
    `http://localhost:8000/api/v1/chat/history?member_id=${memberId}&session_id=${sessionId}`
  );

  if (!response.ok) {
    throw new Error('Failed to fetch chat history');
  }

  return response.json();
}

export const ProfileChat: React.FC<ProfileChatProps> = ({ memberId, memberName }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(() => {
    // Initialize from localStorage
    return localStorage.getItem(getSessionKey(memberId));
  });
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isRestoringSession, setIsRestoringSession] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load session from localStorage (external system) when member changes
  useEffect(() => {
    const savedSessionId = localStorage.getItem(getSessionKey(memberId));
    if (savedSessionId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing from localStorage
      setSessionId(savedSessionId);
      setIsRestoringSession(true);
    } else {
      setSessionId(null);
      setMessages([]);
      setSuggestions([]);
    }
  }, [memberId]);

  // Fetch conversation history when we have a session to restore
  useEffect(() => {
    if (isRestoringSession && sessionId) {
      fetchChatHistory(memberId, sessionId)
        .then((data) => {
          setMessages(data.messages);
          setIsRestoringSession(false);
        })
        .catch(() => {
          // Session might be invalid, clear it
          localStorage.removeItem(getSessionKey(memberId));
          setSessionId(null);
          setMessages([]);
          setIsRestoringSession(false);
        });
    }
  }, [isRestoringSession, sessionId, memberId]);

  // Save session_id to localStorage when it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(getSessionKey(memberId), sessionId);
    }
  }, [sessionId, memberId]);

  const handleNewChat = () => {
    localStorage.removeItem(getSessionKey(memberId));
    setSessionId(null);
    setMessages([]);
    setSuggestions([]);
  };

  const chatMutation = useMutation({
    mutationFn: ({ message }: { message: string }) => sendMessage(memberId, message, sessionId),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }]);
      if (data.suggestions_made.length > 0) {
        setSuggestions((prev) => [...prev, ...data.suggestions_made]);
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || chatMutation.isPending) return;

    const userMessage = inputValue.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setInputValue('');
    chatMutation.mutate({ message: userMessage });
  };

  const handleStartChat = () => {
    const greeting = "Hi! I'd like to improve my profile.";
    setMessages([{ role: 'user', content: greeting }]);
    chatMutation.mutate({ message: greeting });
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 flex flex-col h-[600px]">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex justify-between items-start">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Profile Assistant</h2>
          <p className="text-sm text-gray-600">Chat to improve your profile for {memberName}</p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={handleNewChat}
            className="flex items-center gap-1 px-2 py-1 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            title="Start new conversation"
          >
            <RotateCcw className="w-4 h-4" />
            New
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isRestoringSession ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-12 h-12 text-indigo-400 mb-4 animate-pulse" />
            <p className="text-gray-600">Restoring conversation...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-12 h-12 text-indigo-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Start a conversation</h3>
            <p className="text-gray-600 mb-4 max-w-sm">
              I'll help you fill out your profile through a friendly chat. Nothing is published without your approval.
            </p>
            <button
              onClick={handleStartChat}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Start Chat
            </button>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-indigo-600" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {message.role === 'assistant' ? (
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                          li: ({ children }) => <li className="text-sm">{children}</li>,
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p>{message.content}</p>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0">
                    <User className="w-5 h-5 text-white" />
                  </div>
                )}
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-indigo-600" />
                </div>
                <div className="bg-gray-100 rounded-2xl px-4 py-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Suggestions indicator */}
      {suggestions.length > 0 && (
        <div className="px-4 py-2 bg-amber-50 border-t border-amber-200">
          <div className="flex items-center gap-2 text-amber-800">
            <Lightbulb className="w-4 h-4" />
            <span className="text-sm font-medium">{suggestions.length} suggestion(s) ready for review</span>
          </div>
        </div>
      )}

      {/* Input */}
      {messages.length > 0 && (
        <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              disabled={chatMutation.isPending}
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || chatMutation.isPending}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
