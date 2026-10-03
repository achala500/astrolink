import React, { useState } from 'react';
import {
  MessageCircle,
  X,
  Send,
  Bug,
  Zap,
  Palette,
  Lightbulb,
  AlertTriangle,
  CheckCircle2
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
  const [category, setCategory] = useState('bug');
  const [severity, setSeverity] = useState('medium');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

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
        setSubmitted(true);
        setTimeout(() => {
          setSubmitted(false);
          setMessage('');
          setCategory('bug');
          setSeverity('medium');
          setIsOpen(false);
        }, 1800);
      }
    } catch (err) {
      console.error('Feedback submission failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      <button
        type="button"
        onClick={() => {
          soundEngine.playClick();
          setIsOpen(true);
        }}
        className={`fixed bottom-24 right-4 z-50 w-12 h-12 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 active:scale-90 ${
          isCrimson
            ? 'bg-red-900/80 text-red-300 border border-red-700/50 shadow-red-950/40'
            : 'bg-slate-800/90 text-slate-300 border border-white/10 shadow-black/40'
        } ${isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}`}
        title="Send Feedback"
      >
        <MessageCircle className="w-5 h-5" />
      </button>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sheet */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-50 transition-transform duration-500 ${
          isOpen ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{ transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)' }}
      >
        <div
          className={`mx-auto max-w-lg rounded-t-3xl border-t border-x p-5 pb-8 ${
            isCrimson
              ? 'bg-black border-red-900/40'
              : 'bg-slate-950 border-white/10'
          }`}
        >
          {/* Handle bar */}
          <div className="flex justify-center mb-4">
            <div className={`w-10 h-1 rounded-full ${
              isCrimson ? 'bg-red-800' : 'bg-slate-700'
            }`} />
          </div>

          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <h2 className={`text-lg font-semibold tracking-tight ${
              isCrimson ? 'text-red-400' : 'text-slate-100'
            }`}>
              Send Feedback
            </h2>
            <button
              type="button"
              onClick={() => {
                soundEngine.playClick();
                setIsOpen(false);
              }}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all active:scale-90 ${
                isCrimson
                  ? 'hover:bg-red-950/50 text-red-500'
                  : 'hover:bg-white/10 text-slate-400'
              }`}
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {submitted ? (
            /* Success State */
            <div className="flex flex-col items-center justify-center py-8 gap-3">
              <CheckCircle2 className={`w-12 h-12 ${
                isCrimson ? 'text-red-400' : 'text-emerald-400'
              }`} />
              <p className={`text-sm font-medium ${
                isCrimson ? 'text-red-300' : 'text-slate-200'
              }`}>
                Feedback received — Jules will handle it
              </p>
            </div>
          ) : (
            <>
              {/* Category Chips */}
              <div className="mb-4">
                <label className={`text-xs font-medium uppercase tracking-wider mb-2 block ${
                  isCrimson ? 'text-red-600' : 'text-slate-500'
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
                              ? 'bg-red-900/50 border-red-600 text-red-300'
                              : `bg-${cat.color}-500/20 border-${cat.color}-500/50 text-${cat.color}-300`
                            : isCrimson
                              ? 'border-red-900/30 text-red-600 hover:bg-red-950/40'
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
                  isCrimson ? 'text-red-600' : 'text-slate-500'
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
                        onClick={() => setSeverity(sev.id)}
                        className={`h-9 px-3 rounded-full flex items-center gap-1.5 text-xs font-medium transition-all active:scale-95 border ${
                          isActive
                            ? isCrimson
                              ? 'bg-red-900/50 border-red-600 text-red-300'
                              : 'bg-white/10 border-white/20 text-slate-200'
                            : isCrimson
                              ? 'border-red-900/30 text-red-600 hover:bg-red-950/40'
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
                  isCrimson ? 'text-red-600' : 'text-slate-500'
                }`}>
                  Describe the issue
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="What happened? What did you expect?"
                  rows={3}
                  className={`w-full px-4 py-3 rounded-xl text-sm resize-none outline-none transition-all border ${
                    isCrimson
                      ? 'bg-red-950/20 border-red-900/40 text-red-200 placeholder-red-800 focus:border-red-600'
                      : 'bg-slate-900/50 border-white/10 text-slate-200 placeholder-slate-600 focus:border-white/20'
                  }`}
                />
              </div>

              {/* Submit Button */}
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!message.trim() || isSubmitting}
                className={`w-full h-12 rounded-full flex items-center justify-center gap-2 font-semibold text-sm tracking-wide uppercase transition-all duration-200 active:scale-95 shadow-xl disabled:opacity-40 disabled:cursor-not-allowed ${
                  isCrimson
                    ? 'bg-red-600 text-black hover:bg-red-500 shadow-red-600/30'
                    : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-emerald-500/30'
                }`}
              >
                <Send className="w-4 h-4" />
                {isSubmitting ? 'Sending...' : 'Submit to Jules'}
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
