import React, { useState } from 'react';
import { 
  Sparkles, 
  SunMedium, 
  Download, 
  Check, 
  Loader2, 
  Layers, 
  RotateCcw
} from 'lucide-react';
import { soundEngine } from '../utils/audio';
import { apiFetch } from '../utils/api';

/**
 * Controls — Actions & Post-Processing Footer
 * Human-language, Apple-grade controls for:
 * - "Reveal Deep Sky" (PixInsight MTF Auto-Stretch)
 * - "Clear City Glow" (2nd-Order Bivariate Polynomial Gradient Removal)
 * - "Clean Starlight" (Streaming Sigma-Clipped Stacking)
 * - Direct 16-Bit Master Linear TIFF Download
 */
export default function Controls({
  revealDeepSky,
  onToggleRevealDeepSky,
  clearCityGlow,
  onToggleClearCityGlow,
  cleanStarlight = true,
  onToggleCleanStarlight,
  backendUrl,
  stackCount = 0,
  onResetStack,
  isCrimson = false
}) {
  const [downloadingTiff, setDownloadingTiff] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const handleDownloadTiff = async () => {
    try {
      setDownloadingTiff(true);
      soundEngine.playClick();

      const exportEndpoint = `${backendUrl || ''}/api/export`;
      const response = await apiFetch(exportEndpoint);
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

      setDownloadSuccess(true);
      soundEngine.playFrameCaptured();
      setTimeout(() => setDownloadSuccess(false), 3000);
    } catch (err) {
      alert(`Master TIFF export failed: ${err.message}`);
    } finally {
      setDownloadingTiff(false);
    }
  };

  return (
    <footer 
      className={`fixed bottom-0 left-0 right-0 z-40 p-3 sm:p-4 backdrop-blur-2xl border-t transition-all duration-300 ease-apple-spring select-none ${
        isCrimson
          ? 'bg-black/95 border-red-950/60 text-red-500'
          : 'bg-slate-950/90 border-white/10 text-slate-200'
      }`}
    >
      <div className="max-w-4xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Post-Processing Filters (Human Terminology) */}
        <div className="flex items-center flex-wrap gap-2">
          {/* Reveal Deep Sky (MTF AutoStretch) */}
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onToggleRevealDeepSky();
            }}
            className={`min-h-[48px] px-4 rounded-2xl flex items-center gap-2 text-xs font-medium transition-all active:scale-95 border ${
              revealDeepSky
                ? (isCrimson 
                    ? 'bg-red-900/40 border-red-600 text-red-300 shadow-lg shadow-red-950/50' 
                    : 'bg-amber-500/20 border-amber-500/60 text-amber-300 shadow-lg shadow-amber-950/50')
                : (isCrimson 
                    ? 'bg-red-950/20 border-red-900/30 text-red-500/60 hover:bg-red-950/40' 
                    : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10')
            }`}
            title="Reveal Deep Sky (MTF Auto-Stretch)"
          >
            <Sparkles className="w-4 h-4 shrink-0" />
            <span>Reveal Deep Sky</span>
          </button>

          {/* Clear City Glow (Polynomial Light Pollution Removal) */}
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onToggleClearCityGlow();
            }}
            className={`min-h-[48px] px-4 rounded-2xl flex items-center gap-2 text-xs font-medium transition-all active:scale-95 border ${
              clearCityGlow
                ? (isCrimson 
                    ? 'bg-red-900/40 border-red-600 text-red-300 shadow-lg shadow-red-950/50' 
                    : 'bg-cyan-500/20 border-cyan-500/60 text-cyan-300 shadow-lg shadow-cyan-950/50')
                : (isCrimson 
                    ? 'bg-red-950/20 border-red-900/30 text-red-500/60 hover:bg-red-950/40' 
                    : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10')
            }`}
            title="Clear City Glow (Remove Light Pollution)"
          >
            <SunMedium className="w-4 h-4 shrink-0" />
            <span>Clear City Glow</span>
          </button>

          {/* Clean Starlight (Sigma-Clipped Stacking Filter) */}
          {onToggleCleanStarlight && (
            <button
              type="button"
              onClick={() => {
                soundEngine.playClick();
                onToggleCleanStarlight();
              }}
              className={`min-h-[48px] px-4 rounded-2xl flex items-center gap-2 text-xs font-medium transition-all active:scale-95 border ${
                cleanStarlight
                  ? (isCrimson 
                      ? 'bg-red-900/40 border-red-600 text-red-300' 
                      : 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300')
                  : (isCrimson 
                      ? 'bg-red-950/20 border-red-900/30 text-red-500/60' 
                      : 'bg-white/5 border-white/10 text-slate-400')
              }`}
              title="Clean Starlight (Sigma-Clipping satellite and hot-pixel rejection)"
            >
              <Layers className="w-4 h-4 shrink-0" />
              <span>Clean Starlight</span>
            </button>
          )}
        </div>

        {/* Export & Reset Triggers */}
        <div className="flex items-center gap-2">
          {onResetStack && (
            <button
              type="button"
              onClick={() => {
                if (window.confirm('Reset the active stacking session?')) {
                  soundEngine.playClick();
                  onResetStack();
                }
              }}
              className={`min-h-[48px] min-w-[48px] px-3 rounded-2xl flex items-center justify-center border transition-all active:scale-95 ${
                isCrimson 
                  ? 'border-red-900/30 text-red-500/60 hover:text-red-400 hover:bg-red-950/30' 
                  : 'border-white/10 text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
              title="Reset Master Stack"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}

          {/* Direct 16-Bit Master TIFF Download Button */}
          <button
            type="button"
            onClick={handleDownloadTiff}
            disabled={downloadingTiff || stackCount === 0}
            className={`min-h-[48px] px-5 rounded-2xl flex items-center gap-2 font-semibold text-xs tracking-wider uppercase transition-all active:scale-95 shadow-xl ${
              stackCount === 0
                ? 'opacity-40 cursor-not-allowed bg-slate-800 text-slate-500 border border-slate-700/50'
                : downloadSuccess
                  ? 'bg-emerald-600 text-white'
                  : isCrimson
                    ? 'bg-red-600 text-black hover:bg-red-500 shadow-red-600/30'
                    : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-emerald-500/25'
            }`}
          >
            {downloadingTiff ? (
              <Loader2 className="w-4 h-4 animate-spin shrink-0" />
            ) : downloadSuccess ? (
              <Check className="w-4 h-4 shrink-0" />
            ) : (
              <Download className="w-4 h-4 shrink-0" />
            )}
            <span>
              {downloadingTiff 
                ? 'Compiling...' 
                : downloadSuccess 
                  ? 'TIFF Saved' 
                  : 'Download Master TIFF'}
            </span>
          </button>
        </div>
      </div>
    </footer>
  );
}
