import React from 'react';
import { Play, Square, Timer, Layers, ShieldCheck } from 'lucide-react';
import { soundEngine } from '../utils/audio';

export default function DurationControls({
  exposureSeconds,
  setExposureSeconds,
  frameCount,
  setFrameCount,
  delaySeconds,
  setDelaySeconds,
  isRunning,
  onStartSequence,
  onStopSequence,
  isCrimson
}) {
  const PRESETS = [5, 10, 15, 20, 30, 60, 120];

  return (
    <div className={`p-5 rounded-3xl border shadow-xl flex flex-col gap-5 ${
      isCrimson 
        ? 'bg-black/90 border-red-900/40 text-red-500' 
        : 'bg-slate-900/80 border-white/10 text-slate-200'
    }`}>
      {/* Exposure Duration Presets */}
      <div className="flex flex-col gap-2">
        <label className="text-xs uppercase tracking-wider font-mono opacity-70 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Timer className="w-3.5 h-3.5" /> Exposure Duration
          </span>
          <span className="font-semibold text-sm">{exposureSeconds}s</span>
        </label>
        <div className="grid grid-cols-4 sm:grid-cols-7 gap-1.5">
          {PRESETS.map((sec) => (
            <button
              key={sec}
              type="button"
              onClick={() => {
                setExposureSeconds(sec);
                soundEngine.playClick();
              }}
              className={`h-11 rounded-xl text-xs font-mono font-medium transition-all active:scale-95 border ${
                exposureSeconds === sec
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
        </div>
      </div>

      {/* Frame Count Slider */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="opacity-70 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5" /> Total Frames
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
          <span>150 frames</span>
          <span>300 frames</span>
        </div>
      </div>

      {/* Settle Delay Slider (Min 2.0s mandatory for sensor heat dissipation) */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="opacity-70 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> Sensor Cooldown Delay
          </span>
          <span className="font-semibold text-sm">{delaySeconds}s</span>
        </div>
        <input
          type="range"
          min="2"
          max="15"
          step="0.5"
          value={delaySeconds}
          onChange={(e) => setDelaySeconds(Number(e.target.value))}
          className={`w-full h-2 rounded-lg appearance-none cursor-pointer ${
            isCrimson ? 'accent-red-600 bg-red-950/40' : 'accent-emerald-500 bg-slate-800'
          }`}
        />
        <div className="flex justify-between text-[10px] opacity-50 font-mono">
          <span>2.0s (min)</span>
          <span>Thermal cooldown between exposures</span>
          <span>15.0s</span>
        </div>
      </div>

      {/* Sequence Actions */}
      <div className="pt-2">
        {isRunning ? (
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onStopSequence();
            }}
            className={`w-full h-12 rounded-2xl flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase transition-all active:scale-98 shadow-xl ${
              isCrimson 
                ? 'bg-red-600 text-black hover:bg-red-500' 
                : 'bg-amber-500 text-slate-950 hover:bg-amber-400'
            }`}
          >
            <Square className="w-4 h-4 fill-current" />
            <span>Abort Run</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onStartSequence();
            }}
            className={`w-full h-12 rounded-2xl flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase transition-all active:scale-98 shadow-xl ${
              isCrimson 
                ? 'bg-red-600 text-black hover:bg-red-500' 
                : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400'
            }`}
          >
            <Play className="w-4 h-4 fill-current" />
            <span>Start Sequence</span>
          </button>
        )}
      </div>
    </div>
  );
}
