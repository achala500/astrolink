import React, { useState, useEffect } from 'react';
import { 
  Wifi, 
  WifiOff, 
  Sparkles, 
  Activity, 
  Clock, 
  Layers, 
  AlertTriangle, 
  Wind, 
  Cloud, 
  Eye, 
  ChevronDown,
  Volume2,
  VolumeX,
  Compass
} from 'lucide-react';
import { soundEngine } from '../utils/audio';

export default function DynamicIsland({ 
  telemetry, 
  isConnected, 
  isCrimson, 
  audioEnabled, 
  onToggleAudio,
  gpsCoords
}) {
  const [expanded, setExpanded] = useState(false);
  const [activeAlert, setActiveAlert] = useState(null);

  // Parse telemetry values with resilient defaults
  const stackCount = telemetry?.stackCount ?? 0;
  const totalExp = telemetry?.totalExp ?? 0;
  const fwhm = telemetry?.fwhm ?? 0;
  const snrGain = telemetry?.snrGain ?? 0;
  const alertMessage = telemetry?.alertMessage ?? null;
  const isRunning = telemetry?.intervalometerRunning ?? false;

  // Format total exposure into MM:SS or HH:MM:SS
  const formatDuration = (seconds) => {
    const s = Math.floor(seconds);
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    if (hrs > 0) {
      return `${hrs}h ${mins.toString().padStart(2, '0')}m`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Convert raw system alert messages into humane Apple-grade notifications
  const getAlertDetails = (msg) => {
    if (!msg) return null;
    const lower = msg.toLowerCase();
    if (lower.includes('eccentricity') || lower.includes('wind') || lower.includes('drift') || lower.includes('jitter')) {
      return {
        title: 'Frame Skipped',
        subtitle: 'Camera bumped by wind jitter',
        icon: Wind,
        color: isCrimson ? 'text-red-400' : 'text-amber-400',
        bg: isCrimson ? 'bg-red-950/80' : 'bg-amber-950/60',
        border: isCrimson ? 'border-red-600/40' : 'border-amber-500/40',
      };
    }
    if (lower.includes('cloud') || lower.includes('star count drop') || lower.includes('alignment')) {
      return {
        title: 'Passing Clouds Detected',
        subtitle: 'Auto-paused to protect stack purity',
        icon: Cloud,
        color: isCrimson ? 'text-red-400' : 'text-sky-400',
        bg: isCrimson ? 'bg-red-950/80' : 'bg-sky-950/60',
        border: isCrimson ? 'border-red-600/40' : 'border-sky-500/40',
      };
    }
    if (lower.includes('fwhm') || lower.includes('dew') || lower.includes('blur') || lower.includes('focus')) {
      return {
        title: 'Optics Cooling Down',
        subtitle: 'Touch up focus to restore sub-2.5px stars',
        icon: Eye,
        color: isCrimson ? 'text-red-400' : 'text-emerald-400',
        bg: isCrimson ? 'bg-red-950/80' : 'bg-emerald-950/60',
        border: isCrimson ? 'border-red-600/40' : 'border-emerald-500/40',
      };
    }
    return {
      title: 'Atmospheric Filter Active',
      subtitle: msg,
      icon: AlertTriangle,
      color: isCrimson ? 'text-red-400' : 'text-amber-400',
      bg: isCrimson ? 'bg-red-950/80' : 'bg-slate-900/90',
      border: isCrimson ? 'border-red-600/40' : 'border-slate-700',
    };
  };

  useEffect(() => {
    if (alertMessage) {
      const details = getAlertDetails(alertMessage);
      setActiveAlert(details);
      soundEngine.playWarning();

      // Auto-collapse after 7s
      const timer = setTimeout(() => {
        setActiveAlert(null);
      }, 7000);
      return () => clearTimeout(timer);
    }
  }, [alertMessage]);

  const alertDetails = activeAlert;

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center pointer-events-auto">
      {/* Dynamic Capsule */}
      <div 
        onClick={() => setExpanded(!expanded)}
        className={`group relative flex items-center justify-between cursor-pointer select-none px-4 py-2 rounded-full border transition-all duration-300 ease-apple-spring shadow-2xl backdrop-blur-2xl ${
          isCrimson 
            ? 'bg-black/90 border-red-900/40 text-red-500 hover:border-red-600/60' 
            : 'bg-slate-950/85 border-white/10 text-slate-200 hover:border-white/20'
        } ${expanded ? 'w-[94vw] max-w-lg rounded-3xl p-5' : 'h-11 min-w-[320px] max-w-md'}`}
      >
        {!expanded ? (
          /* Compact Dynamic Island */
          <div className="w-full flex items-center justify-between gap-3 text-xs tracking-tight">
            {/* Live Indicator & Stack Count */}
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                {isRunning && (
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    isCrimson ? 'bg-red-500' : 'bg-emerald-400'
                  }`} />
                )}
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  !isConnected 
                    ? 'bg-amber-500' 
                    : isRunning 
                      ? (isCrimson ? 'bg-red-500' : 'bg-emerald-500') 
                      : 'bg-slate-500'
                }`} />
              </span>
              <div className="flex items-baseline gap-1 font-mono font-medium">
                <span className="text-sm font-semibold">{stackCount}</span>
                <span className="opacity-60 text-[10px]">STACKED</span>
              </div>
            </div>

            {/* Total Integration Duration */}
            <div className="flex items-center gap-1.5 opacity-90 font-mono text-[11px]">
              <Clock className="w-3.5 h-3.5 opacity-50" />
              <span>{formatDuration(totalExp)}</span>
            </div>

            {/* SNR Gain */}
            <div className="flex items-center gap-1 font-mono text-[11px]">
              <Sparkles className={`w-3.5 h-3.5 ${isCrimson ? 'text-red-400' : 'text-amber-400'}`} />
              <span className="font-semibold">{snrGain > 0 ? `+${snrGain.toFixed(1)}` : '0.0'}</span>
              <span className="opacity-50 text-[10px]">dB</span>
            </div>

            {/* Quick Star Sharpness Focus Metric */}
            <div className="flex items-center gap-1.5 font-mono text-[11px]">
              <Activity className="w-3.5 h-3.5 opacity-50" />
              <span className={`${
                fwhm > 0 && fwhm <= 2.8 
                  ? (isCrimson ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold') 
                  : (isCrimson ? 'text-red-600' : 'text-amber-400')
              }`}>
                {fwhm > 0 ? `${fwhm.toFixed(1)}px` : '–'}
              </span>
            </div>

            {/* Chevron toggle */}
            <ChevronDown className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 transition-opacity" />
          </div>
        ) : (
          /* Expanded Inspection Card */
          <div className="w-full flex flex-col gap-4 text-xs">
            {/* Header with Connection & Audio */}
            <div className="flex items-center justify-between border-b pb-2 border-inherit/20">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className={`inline-flex rounded-full h-2 w-2 ${
                    isConnected ? (isCrimson ? 'bg-red-500' : 'bg-emerald-400') : 'bg-amber-400'
                  }`} />
                </span>
                <span className="font-semibold tracking-wide uppercase text-[11px]">
                  {isConnected ? 'AstroLink Session Active' : 'Connecting to Telescope...'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleAudio();
                  }}
                  className="p-1 rounded-full hover:bg-white/10 transition-colors"
                  title="Toggle Tactile Audio"
                >
                  {audioEnabled ? (
                    <Volume2 className="w-4 h-4 opacity-75" />
                  ) : (
                    <VolumeX className="w-4 h-4 opacity-40" />
                  )}
                </button>
                {isConnected ? (
                  <Wifi className="w-4 h-4 opacity-70" />
                ) : (
                  <WifiOff className="w-4 h-4 text-amber-400" />
                )}
              </div>
            </div>

            {/* 4-Stat Telemetry Matrix */}
            <div className="grid grid-cols-2 gap-2 text-left">
              <div className="p-2.5 rounded-xl bg-white/[0.03] border border-inherit/10">
                <div className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-1 mb-1">
                  <Layers className="w-3 h-3" /> Total Integrated
                </div>
                <div className="text-base font-mono font-bold">
                  {stackCount} <span className="text-[10px] font-normal opacity-60">frames</span>
                </div>
                <div className="text-[10px] opacity-70 mt-0.5 font-mono">
                  {formatDuration(totalExp)} total photons
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-white/[0.03] border border-inherit/10">
                <div className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-1 mb-1">
                  <Sparkles className="w-3 h-3 text-amber-400" /> Stacking Signal
                </div>
                <div className="text-base font-mono font-bold text-amber-400">
                  +{snrGain.toFixed(2)} <span className="text-[10px] font-normal opacity-70 text-slate-300">dB SNR</span>
                </div>
                <div className="text-[10px] opacity-70 mt-0.5">
                  √N Clean Starlight boost
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-white/[0.03] border border-inherit/10">
                <div className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-1 mb-1">
                  <Activity className="w-3 h-3" /> Star Diameter (FWHM)
                </div>
                <div className="text-base font-mono font-bold">
                  {fwhm > 0 ? `${fwhm.toFixed(2)} px` : 'Calibrating'}
                </div>
                <div className={`text-[10px] mt-0.5 font-medium ${
                  fwhm <= 2.6 ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  {fwhm <= 2.6 ? 'Crisp Optics (Airy Disk)' : 'Focus Drift Detected'}
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-white/[0.03] border border-inherit/10">
                <div className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-1 mb-1">
                  <Compass className="w-3 h-3" /> Observing Site GPS
                </div>
                <div className="text-xs font-mono font-semibold">
                  {gpsCoords ? `${gpsCoords.lat.toFixed(3)}°, ${gpsCoords.lon.toFixed(3)}°` : 'Offline (Local)'}
                </div>
                <div className="text-[10px] opacity-60 mt-0.5">
                  Bortle Zero Precision
                </div>
              </div>
            </div>

            <div className="text-center text-[10px] opacity-50 pt-1">
              Tap anywhere on island to collapse
            </div>
          </div>
        )}
      </div>

      {/* Atmospheric Alert Notification Banner (Non-Alarmist Apple HIG Toast) */}
      {alertDetails && (
        <div 
          className={`mt-2 flex items-center gap-3 px-4 py-2.5 rounded-2xl border text-xs shadow-xl animate-fade-in backdrop-blur-xl ${alertDetails.bg} ${alertDetails.border}`}
        >
          <alertDetails.icon className={`w-4 h-4 shrink-0 ${alertDetails.color}`} />
          <div className="flex flex-col text-left">
            <span className={`font-semibold ${alertDetails.color}`}>
              {alertDetails.title}
            </span>
            <span className="text-[11px] opacity-80 text-slate-300">
              {alertDetails.subtitle}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
