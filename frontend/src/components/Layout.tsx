import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  MessageSquare,
  Home,
  Users,
  HelpCircle,
  Sparkles,
  Smartphone,
  Play,
  Network,
  Database,
  Mail,
  Monitor,
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  // Primary nav - core data
  const navItems = [
    { path: "/", label: "Home", icon: Home },
    { path: "/members", label: "Members", icon: Users },
    { path: "/questions", label: "Questions", icon: HelpCircle },
    { path: "/patterns", label: "Patterns", icon: Sparkles },
  ];

  // Architecture/visualization nav
  const archItems = [
    { path: "/graph", label: "Graph", icon: Network },
    { path: "/data-model", label: "Data Model", icon: Database },
    { path: "/messages", label: "Messages", icon: Mail },
  ];

  // Demo/Experience links
  const demoItems = [
    { path: "/display", label: "Display", icon: Monitor },
    { path: "/mobile", label: "Mobile", icon: Smartphone },
    { path: "/demo", label: "Demo", icon: Play, highlight: true },
  ];

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 flex-shrink-0">
              <div className="bg-indigo-600 p-1.5 rounded-lg">
                <MessageSquare className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-violet-600 hidden sm:inline">
                Profile Optimizer
              </span>
            </Link>

            <nav className="flex items-center gap-0.5">
              {navItems.map((item) => {
                const isActive =
                  item.path === '/'
                    ? location.pathname === '/'
                    : location.pathname.startsWith(item.path);
                const Icon = item.icon;

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    title={item.label}
                    className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="hidden lg:inline">{item.label}</span>
                  </Link>
                );
              })}

              {/* Separator */}
              <div className="w-px h-5 bg-gray-200 mx-1.5" />

              {/* Architecture/Visualization links */}
              {archItems.map((item) => {
                const isActive = location.pathname.startsWith(item.path);
                const Icon = item.icon;

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    title={item.label}
                    className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-purple-100 text-purple-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="hidden lg:inline">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Right side - Demo links */}
          <div className="flex items-center gap-1">
            {demoItems.map((item) => {
              const Icon = item.icon;
              const isHighlight = 'highlight' in item && item.highlight;
              const isActive = location.pathname === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  title={item.label}
                  className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isHighlight
                      ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white hover:from-indigo-700 hover:to-violet-700'
                      : isActive
                      ? 'bg-green-100 text-green-700'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden md:inline">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
};
