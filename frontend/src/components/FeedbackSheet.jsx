import React, { useState, useEffect } from 'react';
import {
  MessageCircle,
  X,
  Send,
  Bug,
  Zap,
  Palette,
  Lightbulb,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  RefreshCw,
  GitPullRequest
} from 'lucide-react';
import { soundEngine } from '../utils/audio';

const CATEGORIES = [
  { id: 'bug', label: 'Bug Report', icon: Bug, color: 'red' },
  { id: 'performance', label: 'Slow / Lag', icon: Zap, color: 'amber' },
  { id: 'ui', label: 'Visual Issue', icon: Palette, color: 'blue' },
  { id: 'suggestion', label: 'Idea', icon: Lightbulb, color: 'emerald' },
  { id: 'crash', label: 'Crash', icon: AlertTriangle, color: 'rose' },
];

const SEVERITIES = [
  { id: 'low', label: 'Low', dot: 'bg-blue-400' },
  { id: 'medium', label: 'Medium', dot: 'bg-amber-400' },
  { id: 'high', label: 'High', dot: 'bg-orange-500' },
  { id: 'critical', label: 'Critical', dot: 'bg-red-500' },
];

export default function FeedbackSheet({ isCrimson, backendUrl }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('submit'); // 'submit' | 'track'
  
  // Submit Form State
  const [category, setCategory] = useState('bug');
  const [severity, setSeverity] = useState('medium');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedId, setSubmittedId] = useState(null);

  // Tracking State
  const [trackedReports, setTrackedReports] = useState([]);
  const [isLoadingReports, setIsLoadingReports] = useState(false);

  // Retrieve user's stored feedback IDs from localStorage
  const getStoredFeedbackIds = () => {
    try {
      const stored = localStorage.getItem('astrolink_feedback_ids');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  };

  const saveFeedbackId = (id) => {
    try {
      const current = getStoredFeedbackIds();
      if (!current.includes(id)) {
        const updated = [id, ...current];
        localStorage.setItem('astrolink_feedback_ids', JSON.stringify(updated));
      }
    } catch (err) {
      console.error('Failed to save feedback ID:', err);
    }
  };

  // Fetch status of tracked reports
  const fetchTrackedReports = async () => {
    const ids = getStoredFeedbackIds();
    if (!ids.length) {
      setTrackedReports([]);
      return;
    }

    setIsLoadingReports(true);
    try {
      const res = await fetch(`${backendUrl}/api/feedback/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids }),
      });
      if (res.ok) {
        const data = await res.json();
        setTrackedReports(data.reports || []);
      }
    } catch (err) {
      console.error('Failed to fetch tracked feedback:', err);
    } finally {
      setIsLoadingReports(false);
    }
  };

  useEffect(() => {
    if (isOpen && activeTab === 'track') {
      fetchTrackedReports();
    }
  }, [isOpen, activeTab]);

  const handleSubmit = async () => {
    if (!message.trim()) return;
    setIsSubmitting(true);
    soundEngine.playClick();

    try {
      const res = await fetch(`${backendUrl}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category,
          severity,
          message: message.trim(),
          device_info: navigator.userAgent,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const newId = data.feedback_id;
        saveFeedbackId(newId);
        setSubmittedId(newId);

        setTimeout(() => {
          setSubmittedId(null);
          setMessage('');
          setCategory('bug');
          setSeverity('medium');
          setActiveTab('track');
          fetchTrackedReports();
        }, 1600);
      }
    } catch (err) {
      console.error('Feedback submission failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (report) => {
    const status = report.status || (report.resolved ? 'resolved' : 'pending');
    
    if (status === 'resolved') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          Resolved & Merged
        </span>
      );
    }

    if (status === 'triaged' || status === 'in_progress' || report.jules_issue_number) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
          <GitPullRequest className="w-3 h-3 text-blue-400" />
          Jules Investigating {report.jules_issue_number ? `#${report.jules_issue_number}` : ''}
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
        <Clock className="w-3 h-3 text-amber-400" />
        Pending Jules Triage
      </span>
    );
  };

  return (
    <>
      {/* Floating Action Button with Ticket Counter */}
      <button
        type="button"
        onClick={() => {
          soundEngine.playClick();
          setIsOpen(true);
        }}
        className={`fixed bottom-24 right-4 z-50 min-w-[48px] h-12 px-3 rounded-full flex items-center justify-center gap-2 shadow-2xl transition-all duration-300 active:scale-90 ${
          isCrimson
            ? 'bg-red-900/90 text-red-200 border border-red-700/60 shadow-red-950/50'
            : 'bg-slate-800/95 text-slate-200 border border-white/15 shadow-black/50'
        } ${isOpen ? 'scale-0 opacity-0 pointer-events-none' : 'scale-100 opacity-100'}`}
        title="Feedback & Bug Tracking"
      >
        <MessageCircle className="w-5 h-5 text-red-400" />
        <span className="text-xs font-semibold tracking-wider uppercase hidden sm:inline">Feedback</span>
      </button>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md transition-opacity duration-300"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Slide-Up Sheet Modal */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-50 max-h-[88vh] overflow-y-auto transition-transform duration-500 ease-apple-spring ${
          isOpen ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{ transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)' }}
      >
        <div
          className={`mx-auto max-w-lg rounded-t-3xl border-t border-x p-5 pb-8 shadow-2xl ${
            isCrimson
              ? 'bg-black border-red-900/40 text-red-100'
              : 'bg-slate-950 border-white/10 text-slate-100'
          }`}
        >
          {/* Handle bar */}
          <div className="flex justify-center mb-3">
            <div className={`w-10 h-1 rounded-full ${
              isCrimson ? 'bg-red-800' : 'bg-slate-700'
            }`} />
          </div>

          {/* Header & Tabs */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 bg-white/5 p-1 rounded-full border border-white/10">
              <button
                type="button"
                onClick={() => {
                  soundEngine.playClick();
                  setActiveTab('submit');
                }}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                  activeTab === 'submit'
                    ? isCrimson
                      ? 'bg-red-600 text-black shadow'
                      : 'bg-white/20 text-white shadow'
                    : isCrimson
                      ? 'text-red-400 hover:text-red-300'
                      : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                New Report
              </button>
              <button
                type="button"
                onClick={() => {
                  soundEngine.playClick();
                  setActiveTab('track');
                }}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-all flex items-center gap-1.5 ${
                  activeTab === 'track'
                    ? isCrimson
                      ? 'bg-red-600 text-black shadow'
                      : 'bg-white/20 text-white shadow'
                    : isCrimson
                      ? 'text-red-400 hover:text-red-300'
                      : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>Track Status</span>
                {trackedReports.length > 0 && (
                  <span className="w-4 h-4 rounded-full bg-red-500 text-black text-[10px] font-bold flex items-center justify-center">
                    {trackedReports.length}
                  </span>
                )}
              </button>
            </div>

            <button
              type="button"
              onClick={() => {
                soundEngine.playClick();
                setIsOpen(false);
              }}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all active:scale-90 ${
                isCrimson
                  ? 'hover:bg-red-950/60 text-red-500'
                  : 'hover:bg-white/10 text-slate-400'
              }`}
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* TAB 1: SUBMIT FEEDBACK */}
          {activeTab === 'submit' && (
            <>
              {submittedId ? (
                /* Success Banner */
                <div className="flex flex-col items-center justify-center py-8 gap-3">
                  <CheckCircle2 className={`w-12 h-12 ${
                    isCrimson ? 'text-red-400 animate-pulse' : 'text-emerald-400 animate-pulse'
                  }`} />
                  <p className="text-sm font-semibold">
                    Ticket #{submittedId} logged successfully!
                  </p>
                  <p className="text-xs text-slate-400 text-center max-w-xs">
                    Assigned to Jules for autonomous triage. Switching to tracking...
                  </p>
                </div>
              ) : (
                <>
                  {/* Category Chips */}
                  <div className="mb-4">
                    <label className={`text-xs font-medium uppercase tracking-wider mb-2 block ${
                      isCrimson ? 'text-red-600' : 'text-slate-400'
                    }`}>
                      Category
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {CATEGORIES.map((cat) => {
                        const Icon = cat.icon;
                        const isActive = category === cat.id;
                        return (
                          <button
                            key={cat.id}
                            type="button"
                            onClick={() => {
                              soundEngine.playClick();
                              setCategory(cat.id);
                            }}
                            className={`h-9 px-3 rounded-full flex items-center gap-1.5 text-xs font-medium transition-all active:scale-95 border ${
                              isActive
                                ? isCrimson
                                  ? 'bg-red-900/60 border-red-600 text-red-200'
                                  : 'bg-emerald-500/20 border-emerald-500/60 text-emerald-200'
                                : isCrimson
                                  ? 'border-red-900/40 text-red-500 hover:bg-red-950/40'
                                  : 'border-white/10 text-slate-400 hover:bg-white/5'
                            }`}
                          >
                            <Icon className="w-3.5 h-3.5" />
                            {cat.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Severity Selector */}
                  <div className="mb-4">
                    <label className={`text-xs font-medium uppercase tracking-wider mb-2 block ${
                      isCrimson ? 'text-red-600' : 'text-slate-400'
                    }`}>
                      Severity
                    </label>
                    <div className="flex gap-2">
                      {SEVERITIES.map((sev) => {
                        const isActive = severity === sev.id;
                        return (
                          <button
                            key={sev.id}
                            type="button"
                            onClick={() => {
                              soundEngine.playClick();
                              setSeverity(sev.id);
                            }}
                            className={`h-8 px-3 rounded-full flex items-center gap-1.5 text-xs font-medium transition-all active:scale-95 border ${
                              isActive
                                ? isCrimson
                                  ? 'bg-red-900/60 border-red-500 text-red-200'
                                  : 'bg-white/15 border-white/30 text-slate-100'
                                : isCrimson
                                  ? 'border-red-900/30 text-red-500/70 hover:bg-red-950/30'
                                  : 'border-white/10 text-slate-400 hover:bg-white/5'
                            }`}
                          >
                            <span className={`w-2 h-2 rounded-full ${sev.dot}`} />
                            {sev.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Message Input */}
                  <div className="mb-5">
                    <label className={`text-xs font-medium uppercase tracking-wider mb-2 block ${
                      isCrimson ? 'text-red-600' : 'text-slate-400'
                    }`}>
                      Description & Expected Behavior
                    </label>
                    <textarea
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      placeholder="Describe what occurred (e.g. frame rejection rate, UI lag, feature suggestion)..."
                      rows={3}
                      className={`w-full px-4 py-3 rounded-xl text-xs sm:text-sm resize-none outline-none transition-all border ${
                        isCrimson
                          ? 'bg-red-950/20 border-red-900/50 text-red-200 placeholder-red-900 focus:border-red-600'
                          : 'bg-slate-900/70 border-white/10 text-slate-200 placeholder-slate-600 focus:border-white/30'
                      }`}
                    />
                    <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                      <span>Live camera and telescope telemetry attached automatically</span>
                    </div>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={!message.trim() || isSubmitting}
                    className={`w-full h-12 rounded-full flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase transition-all duration-200 active:scale-95 shadow-xl disabled:opacity-40 disabled:cursor-not-allowed ${
                      isCrimson
                        ? 'bg-red-600 text-black hover:bg-red-500 shadow-red-600/30'
                        : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-emerald-500/30'
                    }`}
                  >
                    <Send className="w-4 h-4" />
                    <span>{isSubmitting ? 'Sending to Jules...' : 'Submit to Jules'}</span>
                  </button>
                </>
              )}
            </>
          )}

          {/* TAB 2: TRACK REPORTS & LIVE STATUS */}
          {activeTab === 'track' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-400">
                  {trackedReports.length} report(s) linked to this device
                </span>
                <button
                  type="button"
                  onClick={() => {
                    soundEngine.playClick();
                    fetchTrackedReports();
                  }}
                  disabled={isLoadingReports}
                  className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-200"
                >
                  <RefreshCw className={`w-3 h-3 ${isLoadingReports ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>

              {trackedReports.length === 0 ? (
                <div className="py-10 text-center text-slate-500 text-xs">
                  <p>No feedback reports found for this device yet.</p>
                  <p className="mt-1 text-[11px]">Submit an issue in the "New Report" tab to track it here!</p>
                </div>
              ) : (
                <div className="max-h-80 overflow-y-auto space-y-2.5 pr-1">
                  {trackedReports.map((report) => (
                    <div
                      key={report.id}
                      className={`p-3.5 rounded-2xl border transition-all ${
                        isCrimson
                          ? 'bg-red-950/20 border-red-900/40 text-red-200'
                          : 'bg-slate-900/60 border-white/10 text-slate-200'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-mono opacity-60">#{report.id}</span>
                          <span className="text-xs font-semibold capitalize">{report.category}</span>
                        </div>
                        {getStatusBadge(report)}
                      </div>

                      <p className="text-xs text-slate-300 line-clamp-2 mb-2">
                        {report.message}
                      </p>

                      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-white/5">
                        <span>{new Date(report.timestamp).toLocaleDateString()}</span>
                        {report.jules_issue_url && (
                          <a
                            href={report.jules_issue_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-emerald-400 hover:underline font-medium"
                          >
                            <span>View on GitHub</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
