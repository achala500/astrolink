import React, { useState } from 'react';
import { 
  X, 
  Camera, 
  Timer, 
  Layers, 
  ShieldCheck, 
  Play, 
  Square,
  Zap,
  BatteryCharging,
  CheckCircle2,
  Target,
  Sparkles,
  Flame
} from 'lucide-react';
import { soundEngine } from '../utils/audio';

export default function SessionSheet({
  isOpen,
  onClose,
  isCrimson,
  exposureSeconds,
  setExposureSeconds,
  frameCount,
  setFrameCount,
  delaySeconds,
  setDelaySeconds,
  iso,
  setIso,
  bulbMode,
  setBulbMode,
  isRunning,
  onStartSequence,
  onStopSequence
}) {
  if (!isOpen) return null;

  const PRESETS = [5, 10, 15, 20, 30, 60, 120];
  const ISO_OPTIONS = ['Auto', '400', '800', '1600', '3200', '6400', '12800'];

  // Session Goal Presets
  const applyGoalPreset = (goal) => {
    soundEngine.playClick();
    if (goal === 'quick') {
      // 15 minutes of integration (e.g. 45 x 20s)
      setExposureSeconds(20);
      setBulbMode(false);
      setFrameCount(45);
      setDelaySeconds(2.0);
    } else if (goal === 'deep') {
      // 1 hour of integration (e.g. 120 x 30s)
      setExposureSeconds(30);
      setBulbMode(false);
      setFrameCount(120);
      setDelaySeconds(2.0);
    } else if (goal === 'all_night') {
      // All-night run (e.g. 300 x 60s)
      setExposureSeconds(60);
      setBulbMode(false);
      setFrameCount(300);
      setDelaySeconds(3.0);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center pointer-events-auto">
      {/* Backdrop */}
      <div 
        onClick={onClose}
        className="absolute inset-0 bg-black/75 backdrop-blur-md transition-opacity duration-300 animate-fade-in"
      />

      {/* Apple Modal Sheet */}
      <div 
        className={`relative z-10 w-full max-w-xl max-h-[92vh] overflow-y-auto rounded-t-[32px] sm:rounded-3xl border border-b-0 sm:border-b shadow-2xl p-6 sm:p-7 flex flex-col gap-5 animate-scale-in transition-all duration-300 ${
          isCrimson 
            ? 'bg-black/95 border-red-900/50 text-red-500 shadow-red-950/30' 
            : 'bg-slate-950/95 border-white/10 text-slate-200 shadow-black/80'
        }`}
      >
        {/* Drag handle */}
        <div className="w-12 h-1.5 rounded-full mx-auto opacity-30 bg-current -mt-2 mb-1" />

        {/* Sheet Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-2xl ${isCrimson ? 'bg-red-950/40 text-red-400' : 'bg-white/10 text-slate-100'}`}>
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold tracking-tight">Capture Configurator</h2>
              <p className="text-[11px] opacity-60">USB Tethering & Hardware Intervalometer</p>
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

        {/* Camera Health Status Badge */}
        <div className={`p-3 rounded-2xl border flex items-center justify-between text-xs ${
          isCrimson 
            ? 'bg-red-950/30 border-red-900/40 text-red-300' 
            : 'bg-white/[0.03] border-white/10 text-slate-300'
        }`}>
          <div className="flex items-center gap-2">
            <CheckCircle2 className={`w-4 h-4 ${isCrimson ? 'text-red-400' : 'text-emerald-400'}`} />
            <div>
              <span className="font-semibold">DSLR / Mirrorless USB Ready</span>
              <span className="opacity-60 block text-[10px]">Direct RAM Ingestion Buffer</span>
            </div>
          </div>
          <div className="flex items-center gap-2 font-mono text-[11px]">
            <BatteryCharging className="w-4 h-4 text-emerald-400" />
            <span className="font-semibold">96%</span>
          </div>
        </div>

        {/* Session Goal Presets */}
        <div className="flex flex-col gap-2">
          <label className="text-[11px] uppercase tracking-wider font-mono opacity-70 flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5" /> Session Goal
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => applyGoalPreset('quick')}
              className={`p-2.5 rounded-2xl border text-left flex flex-col gap-0.5 transition-all active:scale-95 ${
                isCrimson 
                  ? 'bg-red-950/20 border-red-900/40 hover:bg-red-950/40' 
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
            >
              <span className="font-semibold text-xs flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-400" /> Quick Stack
              </span>
              <span className="text-[10px] opacity-60">15 mins • 45 frames</span>
            </button>

            <button
              type="button"
              onClick={() => applyGoalPreset('deep')}
              className={`p-2.5 rounded-2xl border text-left flex flex-col gap-0.5 transition-all active:scale-95 ${
                isCrimson 
                  ? 'bg-red-950/20 border-red-900/40 hover:bg-red-950/40' 
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
            >
              <span className="font-semibold text-xs flex items-center gap-1">
                <Target className="w-3 h-3 text-sky-400" /> Deep Target
              </span>
              <span className="text-[10px] opacity-60">1 hour • 120 frames</span>
            </button>

            <button
              type="button"
              onClick={() => applyGoalPreset('all_night')}
              className={`p-2.5 rounded-2xl border text-left flex flex-col gap-0.5 transition-all active:scale-95 ${
                isCrimson 
                  ? 'bg-red-950/20 border-red-900/40 hover:bg-red-950/40' 
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
            >
              <span className="font-semibold text-xs flex items-center gap-1">
                <Flame className="w-3 h-3 text-purple-400" /> All Night
              </span>
              <span className="text-[10px] opacity-60">Full Run • 300 frames</span>
            </button>
          </div>
        </div>

        {/* Shutter Speed / Exposure Length Selector */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="opacity-70 flex items-center gap-1.5 uppercase tracking-wider">
              <Timer className="w-3.5 h-3.5" /> Exposure Length
            </span>
            <span className="font-semibold text-sm">
              {bulbMode ? 'Bulb Mode' : `${exposureSeconds}s`}
            </span>
          </div>

          <div className="grid grid-cols-4 sm:grid-cols-8 gap-1.5">
            {PRESETS.map((sec) => (
              <button
                key={sec}
                type="button"
                onClick={() => {
                  setExposureSeconds(sec);
                  setBulbMode(false);
                  soundEngine.playClick();
                }}
                className={`h-11 rounded-2xl text-xs font-mono font-medium transition-all active:scale-95 border ${
                  !bulbMode && exposureSeconds === sec
                    ? (isCrimson 
                        ? 'bg-red-600 text-black border-red-500 font-bold' 
                        : 'bg-emerald-500 text-slate-950 border-emerald-400 font-bold')
                    : (isCrimson 
                        ? 'bg-red-950/20 border-red-900/30 text-red-400 hover:bg-red-950/40' 
                        : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10')
                }`}
              >
                {sec}s
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setBulbMode(true);
                soundEngine.playClick();
              }}
              className={`h-11 rounded-2xl text-xs font-mono font-medium transition-all active:scale-95 border ${
                bulbMode
                  ? (isCrimson 
                      ? 'bg-red-600 text-black border-red-500 font-bold' 
                      : 'bg-emerald-500 text-slate-950 border-emerald-400 font-bold')
                  : (isCrimson 
                      ? 'bg-red-950/20 border-red-900/30 text-red-400 hover:bg-red-950/40' 
                      : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10')
              }`}
            >
              BULB
            </button>
          </div>
        </div>

        {/* ISO Gain Selector */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="opacity-70 flex items-center gap-1.5 uppercase tracking-wider">
              <Zap className="w-3.5 h-3.5" /> Sensor ISO Gain
            </span>
            <span className="font-semibold text-sm">ISO {iso}</span>
          </div>
          <div className="grid grid-cols-4 sm:grid-cols-7 gap-1.5">
            {ISO_OPTIONS.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => {
                  setIso(opt);
                  soundEngine.playClick();
                }}
                className={`h-10 rounded-2xl text-xs font-mono font-medium transition-all active:scale-95 border ${
                  iso === opt
                    ? (isCrimson 
                        ? 'bg-red-600 text-black border-red-500 font-bold' 
                        : 'bg-amber-500 text-slate-950 border-amber-400 font-bold')
                    : (isCrimson 
                        ? 'bg-red-950/20 border-red-900/30 text-red-400 hover:bg-red-950/40' 
                        : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10')
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        {/* Total Frame Count */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="opacity-70 flex items-center gap-1.5 uppercase tracking-wider">
              <Layers className="w-3.5 h-3.5" /> Total Stack Frames
            </span>
            <span className="font-semibold text-sm">{frameCount} frames</span>
          </div>
          <input
            type="range"
            min="1"
            max="300"
            value={frameCount}
            onChange={(e) => setFrameCount(Number(e.target.value))}
            className={`w-full h-2 rounded-lg appearance-none cursor-pointer ${
              isCrimson ? 'accent-red-600 bg-red-950/40' : 'accent-emerald-500 bg-slate-800'
            }`}
          />
          <div className="flex justify-between text-[10px] opacity-40 font-mono">
            <span>1 frame</span>
            <span>150 frames (Deep Sky)</span>
            <span>300 frames</span>
          </div>
        </div>

        {/* Settle Delay (Mandatory Sensor Cooldown) */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="opacity-70 flex items-center gap-1.5 uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5" /> Sensor Cooldown Settle
            </span>
            <span className="font-semibold text-sm">{delaySeconds.toFixed(1)}s</span>
          </div>
          <input
            type="range"
            min="2.0"
            max="15.0"
            step="0.5"
            value={delaySeconds}
            onChange={(e) => setDelaySeconds(Number(e.target.value))}
            className={`w-full h-2 rounded-lg appearance-none cursor-pointer ${
              isCrimson ? 'accent-red-600 bg-red-950/40' : 'accent-emerald-500 bg-slate-800'
            }`}
          />
          <div className="flex justify-between text-[10px] opacity-50 font-mono">
            <span>2.0s (min cooldown)</span>
            <span>Thermal sensor dissipation delay</span>
            <span>15.0s</span>
          </div>
        </div>

        {/* Primary Action Button */}
        <div className="pt-2">
          {isRunning ? (
            <button
              type="button"
              onClick={() => {
                soundEngine.playClick();
                onStopSequence();
                onClose();
              }}
              className={`w-full h-14 rounded-2xl flex items-center justify-center gap-2 font-semibold text-sm tracking-wider uppercase transition-all active:scale-98 shadow-xl ${
                isCrimson 
                  ? 'bg-red-600 text-black hover:bg-red-500' 
                  : 'bg-amber-500 text-slate-950 hover:bg-amber-400'
              }`}
            >
              <Square className="w-4 h-4 fill-current" />
              <span>Abort Active Run</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                soundEngine.playClick();
                onStartSequence();
                onClose();
              }}
              className={`w-full h-14 rounded-2xl flex items-center justify-center gap-2 font-semibold text-sm tracking-wider uppercase transition-all active:scale-98 shadow-xl ${
                isCrimson 
                  ? 'bg-red-600 text-black hover:bg-red-500 shadow-red-600/30' 
                  : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-emerald-500/20'
              }`}
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Deploy Sequence ({frameCount} × {exposureSeconds}s)</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
