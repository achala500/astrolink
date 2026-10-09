import React from 'react';
import { 
  Play, 
  Square, 
  Sliders, 
  Sparkles, 
  SunMedium, 
  Download, 
  RotateCcw, 
  Moon,
  Flame
} from 'lucide-react';
import { soundEngine } from '../utils/audio';

export default function Dock({ 
  isRunning, 
  onStartSequence, 
  onStopSequence, 
  onResetStack,
  onOpenSettings, 
  onOpenExport, 
  isCrimson, 
  onToggleCrimson,
  revealDeepSky,
  onToggleRevealDeepSky,
  clearCityGlow,
  onToggleClearCityGlow
}) {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-[94vw] max-w-2xl pointer-events-auto">
      <div className={`p-2 sm:p-2.5 rounded-full border shadow-2xl backdrop-blur-2xl flex items-center justify-between gap-1 sm:gap-2 transition-all duration-300 ease-apple-spring ${
        isCrimson 
          ? 'bg-black/95 border-red-900/50 text-red-500 shadow-red-950/20' 
          : 'bg-slate-950/85 border-white/10 text-slate-300 shadow-black/40'
      }`}>
        {/* Left Side: Capture Settings & Filter Toggles */}
        <div className="flex items-center gap-1 sm:gap-1.5">
          {/* Settings Configurator (48px hit target) */}
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onOpenSettings();
            }}
            className={`min-w-[48px] h-12 px-3 rounded-full flex items-center justify-center gap-1.5 transition-all active:scale-95 text-xs font-medium border ${
              isCrimson 
                ? 'hover:bg-red-950/40 border-transparent hover:border-red-800/40 text-red-400' 
                : 'hover:bg-white/10 border-transparent hover:border-white/10 text-slate-300'
            }`}
            title="Configure Exposure Sequence"
            aria-label="Configure exposure sequence plan"
          >
            <Sliders className="w-4 h-4" />
            <span className="hidden md:inline">Plan</span>
          </button>

          {/* Reveal Deep Sky (MTF Auto-Stretch Toggle) */}
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onToggleRevealDeepSky();
            }}
            className={`min-w-[48px] h-12 px-3 rounded-full flex items-center justify-center gap-1.5 transition-all active:scale-95 text-xs font-medium border ${
              revealDeepSky 
                ? (isCrimson 
                    ? 'bg-red-900/40 border-red-600 text-red-300 shadow-lg shadow-red-950/50' 
                    : 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-lg shadow-amber-950/50')
                : (isCrimson 
                    ? 'border-transparent hover:bg-red-950/40 text-red-500/60' 
                    : 'border-transparent hover:bg-white/5 text-slate-400')
            }`}
            title="Reveal Deep Sky (PixInsight MTF Stretch)"
            aria-label="Reveal Deep Sky MTF stretch"
          >
            <Sparkles className="w-4 h-4" />
            <span className="hidden md:inline">Reveal Sky</span>
          </button>

          {/* Clear City Glow (Background Gradient Removal Toggle) */}
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onToggleClearCityGlow();
            }}
            className={`min-w-[48px] h-12 px-3 rounded-full flex items-center justify-center gap-1.5 transition-all active:scale-95 text-xs font-medium border ${
              clearCityGlow 
                ? (isCrimson 
                    ? 'bg-red-900/40 border-red-600 text-red-300' 
                    : 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300')
                : (isCrimson 
                    ? 'border-transparent hover:bg-red-950/40 text-red-500/60' 
                    : 'border-transparent hover:bg-white/5 text-slate-400')
            }`}
            title="Clear City Glow (2nd Order Polynomial Removal)"
            aria-label="Clear City Glow background removal"
          >
            <SunMedium className="w-4 h-4" />
            <span className="hidden md:inline">Clear Glow</span>
          </button>
        </div>

        {/* Center: Hero Trigger Pill (Start Shooting / Stop Sequence) */}
        <div className="flex items-center px-1">
          {isRunning ? (
            <button
              type="button"
              onClick={() => {
                soundEngine.playClick();
                onStopSequence();
              }}
              className={`h-12 px-5 sm:px-6 rounded-full flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase transition-all duration-200 active:scale-95 shadow-xl ${
                isCrimson 
                  ? 'bg-red-600 text-black hover:bg-red-500 shadow-red-600/30' 
                  : 'bg-amber-500 text-slate-950 hover:bg-amber-400 shadow-amber-500/25'
              }`}
            >
              <Square className="w-4 h-4 fill-current" />
              <span>Pause Run</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                soundEngine.playClick();
                onStartSequence();
              }}
              className={`h-12 px-5 sm:px-7 rounded-full flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase transition-all duration-200 active:scale-95 shadow-xl ${
                isCrimson 
                  ? 'bg-red-600 text-black hover:bg-red-500 shadow-red-600/40' 
                  : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-emerald-500/30'
              }`}
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Start Shooting</span>
            </button>
          )}
        </div>

        {/* Right Side: Reset Stack, Export TIFF, Night Red Mode */}
        <div className="flex items-center gap-1 sm:gap-1.5">
          {/* Reset Stack */}
          <button
            type="button"
            onClick={() => {
              if (window.confirm('Reset current stack and start fresh session?')) {
                soundEngine.playClick();
                onResetStack();
              }
            }}
            className={`min-w-[48px] h-12 px-3 rounded-full flex items-center justify-center transition-all active:scale-95 border ${
              isCrimson 
                ? 'border-transparent hover:bg-red-950/40 text-red-500/70 hover:text-red-400' 
                : 'border-transparent hover:bg-white/10 text-slate-400 hover:text-slate-200'
            }`}
            title="Reset Master Stack"
            aria-label="Reset Master Stack"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Master 16-Bit TIFF Export */}
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onOpenExport();
            }}
            className={`min-w-[48px] h-12 px-3.5 rounded-full flex items-center justify-center gap-1.5 transition-all active:scale-95 text-xs font-medium border ${
              isCrimson 
                ? 'border-red-900/60 bg-red-950/30 hover:bg-red-900/40 text-red-400' 
                : 'border-white/15 bg-white/5 hover:bg-white/10 text-slate-200'
            }`}
            title="Export 16-Bit TIFF Master"
            aria-label="Export 16-Bit TIFF Master"
          >
            <Download className="w-4 h-4" />
            <span className="hidden md:inline">Export</span>
          </button>

          {/* OLED Astro Red Mode Toggle */}
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onToggleCrimson();
            }}
            className={`min-w-[48px] h-12 px-3 rounded-full flex items-center justify-center transition-all active:scale-95 border ${
              isCrimson 
                ? 'bg-red-600 text-black border-red-500' 
                : 'border-transparent hover:bg-white/10 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle OLED Night Crimson Mode"
            aria-label={isCrimson ? "Disable OLED Night Crimson Mode" : "Enable OLED Night Crimson Mode"}
          >
            {isCrimson ? (
              <Flame className="w-4 h-4 fill-current" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
