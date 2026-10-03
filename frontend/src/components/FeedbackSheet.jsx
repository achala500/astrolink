import { adminApiFetch } from '../utils/api';
import React, { useState, useEffect, useRef } from 'react';
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
  GitPullRequest,
  Camera,
  Paperclip,
  Trash2,
  Maximize2
} from 'lucide-react';
import { soundEngine } from '../utils/audio';

const CATEGORIES = [
  { id: 'bug', label: 'Bug Report', icon: Bug, color: 'red' },
  { id: 'performance', label: 'Slow / Lag', icon: Zap, color: 'amber' },
  { id: 'camera', label: 'Camera Tether', icon: Camera, color: 'blue' },
  { id: 'ui', label: 'Visual Issue', icon: Palette, color: 'purple' },
  { id: 'suggestion', label: 'Idea / Feature', icon: Lightbulb, color: 'emerald' },
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
  const [attachments, setAttachments] = useState([]); // [{ id, name, dataUrl, size }]
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedId, setSubmittedId] = useState(null);
  const fileInputRef = useRef(null);

  // Tracking State
  const [trackedReports, setTrackedReports] = useState([]);
  const [isLoadingReports, setIsLoadingReports] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);

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

  // 1. Capture Live Canvas Screenshot from Viewport
  const snapViewportScreenshot = () => {
    soundEngine.playClick();
    const canvas = document.querySelector('canvas');
    if (!canvas) {
      alert('No active telescope viewport canvas found to capture.');
      return;
    }

    try {
      const dataUrl = canvas.toDataURL('image/png');
      const newAtt = {
        id: `snap_${Date.now()}`,
        name: `Viewport_Snapshot_${new Date().toLocaleTimeString().replace(/:/g, '-')}.png`,
        dataUrl,
        size: Math.round((dataUrl.length * 3) / 4 / 1024), // Approx KB
      };
      setAttachments((prev) => [...prev, newAtt]);
    } catch (err) {
      console.error('Failed to capture canvas screenshot:', err);
    }
  };

  // 2. Handle File Upload (PNG, JPG, WebP)
  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    soundEngine.playClick();

    files.forEach((file) => {
      if (!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = (event) => {
        const dataUrl = event.target.result;
        setAttachments((prev) => [
          ...prev,
          {
            id: `file_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
            name: file.name,
            dataUrl,
            size: Math.round(file.size / 1024),
          },
        ]);
      };
      reader.readAsDataURL(file);
    });

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // 3. Paste Screenshot directly from Clipboard (Ctrl+V)
  useEffect(() => {
    if (!isOpen) return;

    const handlePaste = (e) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
          const blob = items[i].getAsFile();
          if (blob) {
            soundEngine.playClick();
            const reader = new FileReader();
            reader.onload = (event) => {
              const dataUrl = event.target.result;
              setAttachments((prev) => [
                ...prev,
                {
                  id: `paste_${Date.now()}`,
                  name: `Clipboard_Screenshot_${Date.now()}.png`,
                  dataUrl,
                  size: Math.round(blob.size / 1024),
                },
              ]);
            };
            reader.readAsDataURL(blob);
          }
        }
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [isOpen]);

  const removeAttachment = (id) => {
    soundEngine.playClick();
    setAttachments((prev) => prev.filter((a) => a.id !== id));
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
      const res = await adminApiFetch(`${backendUrl || ''}/api/feedback/track`, {
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    setIsSubmitting(true);
    soundEngine.playClick();

    try {
      const res = await adminApiFetch(`${backendUrl || ''}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category,
          severity,
          message: message.trim(),
          device_info: navigator.userAgent,
          attachments: attachments.map((a) => a.dataUrl),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const newId = data.feedback_id;
        saveFeedbackId(newId);
        setSubmittedId(newId);
        soundEngine.playFrameCaptured();

        setTimeout(() => {
          setSubmittedId(null);
          setMessage('');
          setAttachments([]);
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
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          Squashed by Jules
        </span>
      );
    }

    if (status === 'triaged' || status === 'in_progress' || report.jules_issue_number) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
          <GitPullRequest className="w-3 h-3 text-blue-400" />
          Jules Triaged {report.jules_issue_number ? `#${report.jules_issue_number}` : ''}
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
        <Clock className="w-3 h-3 text-amber-400" />
        Pending Jules Triage
      </span>
    );
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
        className={`fixed bottom-24 right-4 z-40 min-w-[48px] h-12 px-3 rounded-full flex items-center justify-center gap-2 shadow-2xl transition-all duration-300 active:scale-90 ${
          isCrimson
            ? 'bg-red-600 text-white shadow-red-950/60 hover:bg-red-500'
            : 'bg-emerald-500 text-black shadow-emerald-950/60 hover:bg-emerald-400'
        }`}
        title="Report issue or suggest improvement for Google Jules"
      >
        <MessageCircle className="w-5 h-5" />
        <span className="text-xs font-bold uppercase tracking-wider hidden sm:inline">Feedback</span>
      </button>

      {/* Main Feedback Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div
            className={`relative w-full max-w-lg rounded-3xl p-6 border shadow-2xl overflow-hidden transition-all duration-300 max-h-[90vh] flex flex-col ${
              isCrimson
                ? 'bg-[#0f0202] border-red-900/60 text-red-100 shadow-red-950/40'
                : 'bg-[#09090b] border-white/15 text-slate-100 shadow-black/80'
            }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-inherit/10 flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-2xl ${isCrimson ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                  <MessageCircle className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold tracking-tight">Professional Feedback & Bug Hub</h2>
                  <p className="text-[11px] opacity-60">Evaluated & Autonomously Squashed by Google Jules</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  soundEngine.playClick();
                  setIsOpen(false);
                }}
                className="p-2 rounded-full hover:bg-white/10 transition-colors opacity-70 hover:opacity-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tab Switcher */}
            <div className="flex gap-2 my-4 p-1 rounded-2xl bg-white/[0.04] border border-inherit/10 flex-shrink-0">
              <button
                type="button"
                onClick={() => { soundEngine.playClick(); setActiveTab('submit'); }}
                className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'submit'
                    ? isCrimson ? 'bg-red-600 text-black shadow-md' : 'bg-emerald-500 text-black shadow-md'
                    : 'opacity-60 hover:opacity-100'
                }`}
              >
                Submit Report & SS
              </button>
              <button
                type="button"
                onClick={() => { soundEngine.playClick(); setActiveTab('track'); }}
                className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'track'
                    ? isCrimson ? 'bg-red-600 text-black shadow-md' : 'bg-emerald-500 text-black shadow-md'
                    : 'opacity-60 hover:opacity-100'
                }`}
              >
                Track Tickets ({getStoredFeedbackIds().length})
              </button>
            </div>

            {/* TAB 1: SUBMIT REPORT */}
            {activeTab === 'submit' && (
              <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto space-y-4 pr-1">
                {/* Category Selector */}
                <div>
                  <label className="block text-[11px] font-semibold opacity-70 mb-2 uppercase tracking-wider">
                    Category
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {CATEGORIES.map((c) => {
                      const Icon = c.icon;
                      const isSelected = category === c.id;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => { soundEngine.playClick(); setCategory(c.id); }}
                          className={`p-2.5 rounded-2xl flex flex-col items-center justify-center gap-1.5 border transition-all text-xs font-medium active:scale-95 ${
                            isSelected
                              ? isCrimson
                                ? 'bg-red-950/40 border-red-500 text-red-200'
                                : 'bg-emerald-950/40 border-emerald-500 text-emerald-200'
                              : 'bg-white/[0.02] border-white/10 opacity-70 hover:opacity-100'
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                          <span className="text-[11px]">{c.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Severity Level */}
                <div>
                  <label className="block text-[11px] font-semibold opacity-70 mb-2 uppercase tracking-wider">
                    Severity Level
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {SEVERITIES.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => { soundEngine.playClick(); setSeverity(s.id); }}
                        className={`p-2 rounded-xl flex items-center justify-center gap-1.5 border text-xs font-medium transition-all ${
                          severity === s.id
                            ? 'bg-white/10 border-white/30 text-white'
                            : 'bg-white/[0.02] border-white/10 opacity-60 hover:opacity-100'
                        }`}
                      >
                        <span className={`w-2 h-2 rounded-full ${s.dot}`} />
                        <span>{s.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-[11px] font-semibold opacity-70 mb-1.5 uppercase tracking-wider">
                    Problem Details / Observation Notes
                  </label>
                  <textarea
                    rows={3}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Describe what occurred, camera model, or behavior observed... You can also press Ctrl+V to paste a screenshot!"
                    className="w-full p-3 rounded-2xl bg-white/[0.04] border border-inherit/20 text-xs focus:outline-none focus:border-emerald-500/50 transition-colors resize-none"
                    required
                  />
                </div>

                {/* Screenshot & Image Attachments Bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="block text-[11px] font-semibold opacity-70 uppercase tracking-wider">
                      Screenshots & Visual Proof ({attachments.length})
                    </label>
                    <span className="text-[10px] opacity-50">Ctrl+V to paste anytime</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={snapViewportScreenshot}
                      className="flex-1 h-10 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.09] border border-inherit/20 flex items-center justify-center gap-2 text-xs font-semibold active:scale-95 transition-all"
                    >
                      <Camera className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Snap Viewport</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="flex-1 h-10 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.09] border border-inherit/20 flex items-center justify-center gap-2 text-xs font-semibold active:scale-95 transition-all"
                    >
                      <Paperclip className="w-3.5 h-3.5 text-blue-400" />
                      <span>Attach Image / SS</span>
                    </button>

                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      multiple
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </div>

                  {/* Attachment Thumbnails Grid */}
                  {attachments.length > 0 && (
                    <div className="grid grid-cols-3 gap-2 pt-1">
                      {attachments.map((att) => (
                        <div
                          key={att.id}
                          className="relative group rounded-xl overflow-hidden border border-white/20 aspect-video bg-black/40"
                        >
                          <img
                            src={att.dataUrl}
                            alt={att.name}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-between p-1.5">
                            <span className="text-[9px] truncate text-white">{att.name}</span>
                            <button
                              type="button"
                              onClick={() => removeAttachment(att.id)}
                              className="p-1 rounded-full bg-red-600 text-white hover:bg-red-500"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Submit Action */}
                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={isSubmitting || !message.trim()}
                    className={`w-full h-12 rounded-2xl flex items-center justify-center gap-2 font-bold text-xs uppercase tracking-wider transition-all active:scale-98 shadow-xl ${
                      submittedId
                        ? 'bg-emerald-600 text-white'
                        : isSubmitting || !message.trim()
                          ? 'opacity-40 cursor-not-allowed bg-slate-800 text-slate-500'
                          : isCrimson
                            ? 'bg-red-600 text-black hover:bg-red-500 shadow-red-600/30'
                            : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-emerald-500/25'
                    }`}
                  >
                    {submittedId ? (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Logged Ticket #{submittedId} for Jules</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span>{isSubmitting ? 'Transmitting to Jules...' : 'Submit to Google Jules'}</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* TAB 2: TRACK TICKETS */}
            {activeTab === 'track' && (
              <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                <div className="flex items-center justify-between pb-1">
                  <span className="text-xs font-mono uppercase tracking-wider opacity-60">Submitted Issues</span>
                  <button
                    type="button"
                    onClick={fetchTrackedReports}
                    disabled={isLoadingReports}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-semibold bg-white/5 hover:bg-white/10 border border-white/10 active:scale-95 transition-all"
                  >
                    <RefreshCw className={`w-3 h-3 ${isLoadingReports ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>

                {trackedReports.length > 0 ? (
                  <div className="space-y-2.5">
                    {trackedReports.map((report) => (
                      <div
                        key={report.id}
                        className="p-3.5 rounded-2xl bg-white/[0.03] border border-inherit/15 space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[11px] font-bold text-emerald-400">
                            #{report.id}
                          </span>
                          {getStatusBadge(report)}
                        </div>

                        <p className="text-xs line-clamp-2 opacity-90">{report.message}</p>

                        {/* Render Attached Screenshots if present */}
                        {report.attachments && report.attachments.length > 0 && (
                          <div className="flex gap-2 pt-1 overflow-x-auto">
                            {report.attachments.map((attUrl, i) => (
                              <button
                                key={i}
                                type="button"
                                onClick={() => setPreviewImage(`${backendUrl || ''}${attUrl}`)}
                                className="relative rounded-lg overflow-hidden border border-white/20 w-16 h-10 flex-shrink-0 group"
                              >
                                <img
                                  src={`${backendUrl || ''}${attUrl}`}
                                  alt="Screenshot"
                                  className="w-full h-full object-cover"
                                />
                                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                  <Maximize2 className="w-3 h-3 text-white" />
                                </div>
                              </button>
                            ))}
                          </div>
                        )}

                        {report.jules_issue_url && (
                          <a
                            href={report.jules_issue_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] text-blue-400 hover:underline pt-1"
                          >
                            <span>View Autonomous PR on GitHub</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center opacity-60 text-xs">
                    No tickets tracked yet. Submit a bug report or suggestion to watch Jules evaluate and squash it autonomously.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Screenshot Lightbox Modal */}
      {previewImage && (
        <div 
          onClick={() => setPreviewImage(null)}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-lg animate-fade-in"
        >
          <div className="relative max-w-4xl max-h-[90vh] rounded-2xl overflow-hidden border border-white/20">
            <img src={previewImage} alt="Expanded Screenshot" className="max-w-full max-h-[85vh] object-contain" />
            <button
              type="button"
              onClick={() => setPreviewImage(null)}
              className="absolute top-3 right-3 p-2 rounded-full bg-black/70 text-white hover:bg-black"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
