import React, { useState } from 'react';
import { 
  X, 
  Download, 
  Share2, 
  Layers, 
  Clock, 
  Sparkles, 
  Activity, 
  Compass, 
  Check, 
  FileText,
  Image,
  Loader2,
  ShieldCheck
} from 'lucide-react';
import { soundEngine } from '../utils/audio';

export default function ExportSheet({
  isOpen,
  onClose,
  isCrimson,
  telemetry,
  gpsCoords,
  backendUrl,
  previewUrl
}) {
  if (!isOpen) return null;

  const [downloadingTiff, setDownloadingTiff] = useState(false);
  const [downloadedTiff, setDownloadedTiff] = useState(false);
  const [downloadingPreview, setDownloadingPreview] = useState(false);

  const stackCount = telemetry?.stackCount ?? 0;
  const totalExp = telemetry?.totalExp ?? 0;
  const fwhm = telemetry?.fwhm ?? 0;
  const snrGain = telemetry?.snrGain ?? 0;

  const formatDuration = (seconds) => {
    const s = Math.floor(seconds);
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    return `${mins}m ${secs}s`;
  };

  // 1. Download Master 16-Bit Linear Scientific TIFF
  const handleDownloadTiff = async () => {
    try {
      setDownloadingTiff(true);
      soundEngine.playClick();

      const exportEndpoint = `${backendUrl || ''}/api/export`;
      const response = await fetch(exportEndpoint);
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AstroLink_Master_16bit_${Date.now()}.tiff`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setDownloadedTiff(true);
      soundEngine.playFrameCaptured();
      setTimeout(() => setDownloadedTiff(false), 3000);
    } catch (err) {
      alert(`Export error: ${err.message}`);
    } finally {
      setDownloadingTiff(false);
    }
  };

  // 2. Download or Share 1080p JPEG/WebP Preview Frame
  const handleSharePreview = async (format = 'webp') => {
    soundEngine.playClick();
    if (!previewUrl) return;

    try {
      setDownloadingPreview(true);
      const res = await fetch(previewUrl);
      const blob = await res.blob();
      const ext = format === 'jpeg' ? 'jpg' : 'webp';
      const mime = format === 'jpeg' ? 'image/jpeg' : 'image/webp';
      const file = new File([blob], `AstroLink_Preview_${Date.now()}.${ext}`, { type: mime });

      if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          title: 'AstroLink Stacking Session',
          text: `Deep sky stack: ${stackCount} frames, ${formatDuration(totalExp)}, +${snrGain.toFixed(1)}dB SNR.`,
          files: [file]
        });
      } else {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AstroLink_Preview_${Date.now()}.${ext}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch {
      // Fallback
    } finally {
      setDownloadingPreview(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center pointer-events-auto">
      {/* Backdrop */}
      <div 
        onClick={onClose}
        className="absolute inset-0 bg-black/75 backdrop-blur-md transition-opacity duration-300 animate-fade-in"
      />

      {/* Sheet Content */}
      <div 
        className={`relative z-10 w-full max-w-xl rounded-t-[32px] sm:rounded-3xl border border-b-0 sm:border-b shadow-2xl p-6 sm:p-7 flex flex-col gap-6 animate-scale-in transition-all duration-300 ${
          isCrimson 
            ? 'bg-black/95 border-red-900/50 text-red-500 shadow-red-950/30' 
            : 'bg-slate-950/95 border-white/10 text-slate-200 shadow-black/80'
        }`}
      >
        {/* Handle */}
        <div className="w-12 h-1.5 rounded-full mx-auto opacity-30 bg-current -mt-2 mb-1" />

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-2xl ${isCrimson ? 'bg-red-950/40 text-red-400' : 'bg-white/10 text-slate-100'}`}>
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold tracking-tight">Master Output</h2>
              <p className="text-[11px] opacity-60">Full-Quality 16-Bit Scientific TIFF & High-Res Share</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full hover:bg-white/10 opacity-70 hover:opacity-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Telemetry Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="p-3 rounded-2xl bg-white/[0.03] border border-inherit/15">
            <div className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-1 mb-1">
              <Layers className="w-3.5 h-3.5" /> Clean Frames
            </div>
            <div className="text-sm font-mono font-bold">{stackCount} stacked</div>
            <div className="text-[10px] opacity-60 mt-0.5">100% Accepted</div>
          </div>

          <div className="p-3 rounded-2xl bg-white/[0.03] border border-inherit/15">
            <div className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-1 mb-1">
              <Clock className="w-3.5 h-3.5" /> Total Light
            </div>
            <div className="text-sm font-mono font-bold">{formatDuration(totalExp)}</div>
            <div className="text-[10px] opacity-60 mt-0.5">Deep integration</div>
          </div>

          <div className="p-3 rounded-2xl bg-white/[0.03] border border-inherit/15">
            <div className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-1 mb-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" /> SNR Gain
            </div>
            <div className="text-sm font-mono font-bold text-amber-400">+{snrGain.toFixed(1)} dB</div>
            <div className="text-[10px] opacity-60 mt-0.5">Dynamic range boost</div>
          </div>

          <div className="p-3 rounded-2xl bg-white/[0.03] border border-inherit/15">
            <div className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-1 mb-1">
              <Activity className="w-3.5 h-3.5" /> Sharpness
            </div>
            <div className="text-sm font-mono font-bold">{fwhm > 0 ? `${fwhm.toFixed(2)}px` : '–'}</div>
            <div className="text-[10px] opacity-60 mt-0.5">{fwhm <= 2.5 ? 'Airy disk limit' : 'Focus stable'}</div>
          </div>
        </div>

        {/* GPS Observation Metadata */}
        <div className="flex items-center justify-between p-3.5 rounded-2xl bg-white/[0.02] border border-inherit/10 text-xs">
          <div className="flex items-center gap-2 opacity-80">
            <Compass className="w-4 h-4" />
            <span>Observing Site Geolocation:</span>
          </div>
          <div className="font-mono font-semibold">
            {gpsCoords ? `${gpsCoords.lat.toFixed(4)}°, ${gpsCoords.lon.toFixed(4)}°` : 'Offline (Local)'}
          </div>
        </div>

        {/* Save Options (Full Quality TIFF vs Shareable Preview) */}
        <div className="flex flex-col gap-2.5">
          {/* Option 1: 16-Bit Scientific TIFF */}
          <button
            type="button"
            onClick={handleDownloadTiff}
            disabled={downloadingTiff || stackCount === 0}
            className={`w-full h-14 rounded-2xl flex items-center justify-between px-5 font-semibold text-xs tracking-wider uppercase transition-all active:scale-98 shadow-xl ${
              stackCount === 0
                ? 'opacity-40 cursor-not-allowed bg-slate-800 text-slate-500'
                : downloadedTiff
                  ? 'bg-emerald-600 text-white'
                  : isCrimson
                    ? 'bg-red-600 text-black hover:bg-red-500 shadow-red-600/30'
                    : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-emerald-500/25'
            }`}
          >
            <div className="flex items-center gap-2.5">
              {downloadingTiff ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : downloadedTiff ? (
                <Check className="w-4 h-4" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              <span>
                {downloadingTiff 
                  ? 'Writing Uncompressed TIFF...' 
                  : downloadedTiff 
                    ? '16-Bit TIFF Saved' 
                    : 'Save Full-Quality 16-Bit TIFF'}
              </span>
            </div>
            <span className="font-mono opacity-60 text-[10px] lowercase">.tiff (linear)</span>
          </button>

          {/* Option 2: Shareable High-Res JPEG / WebP */}
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleSharePreview('jpeg')}
              disabled={!previewUrl}
              className={`h-12 px-4 rounded-2xl flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase transition-all active:scale-98 border ${
                !previewUrl
                  ? 'opacity-40 cursor-not-allowed border-transparent bg-slate-900 text-slate-600'
                  : isCrimson
                    ? 'border-red-900/50 bg-red-950/20 hover:bg-red-900/40 text-red-300'
                    : 'border-white/15 bg-white/5 hover:bg-white/10 text-slate-200'
              }`}
            >
              <Image className="w-4 h-4" />
              <span>Share JPEG</span>
            </button>

            <button
              type="button"
              onClick={() => handleSharePreview('webp')}
              disabled={!previewUrl}
              className={`h-12 px-4 rounded-2xl flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase transition-all active:scale-98 border ${
                !previewUrl
                  ? 'opacity-40 cursor-not-allowed border-transparent bg-slate-900 text-slate-600'
                  : isCrimson
                    ? 'border-red-900/50 bg-red-950/20 hover:bg-red-900/40 text-red-300'
                    : 'border-white/15 bg-white/5 hover:bg-white/10 text-slate-200'
              }`}
            >
              <Share2 className="w-4 h-4" />
              <span>Share WebP</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
