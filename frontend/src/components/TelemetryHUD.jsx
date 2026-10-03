import React from 'react';
import { Clock, Layers, Sparkles, Activity, AlertCircle } from 'lucide-react';

export default function TelemetryHUD({ telemetry, isCrimson }) {
  const stackCount = telemetry?.stackCount ?? 0;
  const totalExp = telemetry?.totalExp ?? 0;
  const fwhm = telemetry?.fwhm ?? 0;
  const snrGain = telemetry?.snrGain ?? 0;
  const alertMessage = telemetry?.alertMessage ?? null;

  const formatDuration = (seconds) => {
    const s = Math.floor(seconds);
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="absolute top-16 left-4 z-30 pointer-events-none flex flex-col gap-2 font-mono text-xs">
      <div className={`p-3 rounded-2xl border backdrop-blur-xl transition-colors duration-300 shadow-xl ${
        isCrimson 
          ? 'bg-black/80 border-red-900/30 text-red-400' 
          : 'bg-slate-950/70 border-white/10 text-slate-300'
      }`}>
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 opacity-60" />
            <span className="font-semibold text-sm">{formatDuration(totalExp)}</span>
            <span className="opacity-50 text-[10px]">INTEGRATION</span>
          </div>

          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 opacity-60" />
            <span className="font-semibold">{stackCount}</span>
            <span className="opacity-50 text-[10px]">FRAMES</span>
          </div>

          <div className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 opacity-60 text-amber-400" />
            <span className="font-semibold text-amber-400">+{snrGain.toFixed(1)} dB</span>
            <span className="opacity-50 text-[10px]">SNR</span>
          </div>

          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 opacity-60" />
            <span className={`font-semibold ${fwhm <= 2.8 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {fwhm > 0 ? `${fwhm.toFixed(2)} px` : '–'}
            </span>
            <span className="opacity-50 text-[10px]">FWHM</span>
          </div>
        </div>
      </div>

      {alertMessage && (
        <div className={`p-2.5 rounded-xl border backdrop-blur-md flex items-center gap-2 max-w-xs animate-pulse text-[11px] ${
          isCrimson 
            ? 'bg-red-950/80 border-red-700/50 text-red-200' 
            : 'bg-amber-950/80 border-amber-600/50 text-amber-200'
        }`}>
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>{alertMessage}</span>
        </div>
      )}
    </div>
  );
}
