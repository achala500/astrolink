import React, { useState, useEffect, useRef, useCallback } from 'react';
import { User, Camera, DownloadCloud, X } from 'lucide-react';
import DynamicIsland from './components/DynamicIsland';
import Viewport from './components/Viewport';
import Dock from './components/Dock';
import SessionSheet from './components/SessionSheet';
import ExportSheet from './components/ExportSheet';
import FeedbackSheet from './components/FeedbackSheet';
import AuthModal from './components/AuthModal';
import CameraModal from './components/CameraModal';
import { soundEngine } from './utils/audio';
import { apiFetch } from './utils/api';

export default function App() {
  // Theme & Display State
  const [isCrimson, setIsCrimson] = useState(() => {
    return localStorage.getItem('astrolink_crimson') === 'true';
  });
  const [audioEnabled, setAudioEnabled] = useState(true);

  // Optical & Processing Toggles
  const [revealDeepSky, setRevealDeepSky] = useState(true);
  const [clearCityGlow, setClearCityGlow] = useState(true);

  // Intervalometer & Camera State
  const [exposureSeconds, setExposureSeconds] = useState(15);
  const [frameCount, setFrameCount] = useState(60);
  const [delaySeconds, setDelaySeconds] = useState(2.0);
  const [iso, setIso] = useState('1600');
  const [bulbMode, setBulbMode] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  // Sheets & Modals Visibility
  const [sessionSheetOpen, setSessionSheetOpen] = useState(false);
  const [exportSheetOpen, setExportSheetOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [cameraModalOpen, setCameraModalOpen] = useState(false);

  // Telemetry & WebSocket State
  const [isConnected, setIsConnected] = useState(false);
  const [telemetry, setTelemetry] = useState({
    stackCount: 0,
    totalExp: 0,
    fwhm: 0,
    snrGain: 0,
    alertMessage: null,
    intervalometerRunning: false
  });
  const [previewUrl, setPreviewUrl] = useState(null);
  const [gpsCoords, setGpsCoords] = useState(null);
  const [availableUpdate, setAvailableUpdate] = useState(null);
  const [commandError, setCommandError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const prevStackCountRef = useRef(0);
  const wakeLockRef = useRef(null);

  // Use same-origin URLs so the app works behind HTTPS/reverse proxies and Arena previews.
  // Vite proxies these paths to the local API during development.
  const getBackendUrls = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const token = import.meta.env.VITE_ASTROLINK_API_TOKEN;
    const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : '';
    return {
      wsUrl: `${protocol}//${window.location.host}/ws${tokenQuery}`,
      httpUrl: '',
    };
  };

  const { wsUrl, httpUrl } = getBackendUrls();

  // 1. WebSocket Auto-Reconnect with Exponential Backoff
  const connectWebSocket = useCallback(function connect() {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;
      socket.binaryType = 'blob';

      socket.onopen = () => {
        setIsConnected(true);
        reconnectAttemptRef.current = 0;
      };

      socket.onmessage = (event) => {
        // Handle Binary WebP preview frame
        if (event.data instanceof Blob) {
          const objectUrl = URL.createObjectURL(event.data);
          setPreviewUrl(prev => {
            if (prev && prev.startsWith('blob:')) {
              URL.revokeObjectURL(prev);
            }
            return objectUrl;
          });
          return;
        }

        // Handle JSON Telemetry & Commands
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'command_response') {
            if (data.command === 'START_SEQUENCE' && !data.success) {
              setIsRunning(false);
              setCommandError(data.error || 'Camera sequence could not start');
              window.setTimeout(() => setCommandError(null), 7000);
            }
          }
          if (data.type === 'telemetry') {
            setTelemetry(() => {
              // Trigger harmonious chime if new frame was added
              if (data.stackCount > prevStackCountRef.current && data.stackCount > 0) {
                soundEngine.playFrameCaptured();
              }
              prevStackCountRef.current = data.stackCount;

              if (data.intervalometerRunning !== undefined) {
                setIsRunning(data.intervalometerRunning);
              }
              return data;
            });

            // If base64 preview is attached
            if (data.preview && typeof data.preview === 'string') {
              setPreviewUrl(data.preview);
            }
          }
        } catch {
          // Non-JSON message ignore
        }
      };

      socket.onerror = () => {
        socket.close();
      };

      socket.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        // Exponential backoff reconnect: 1s, 2s, 4s, 8s max
        const backoff = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 8000);
        reconnectAttemptRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, backoff);
      };
    } catch {
      setIsConnected(false);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    }
  }, [wsUrl]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWebSocket]);

  // Send WebSocket Command Helper
  const sendCommand = (cmdObj) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(cmdObj));
    } else {
      alert('Telescope server is offline. Check connection to astrolink.local.');
    }
  };

  // Check for a verified release notification. Installation remains user-controlled.
  useEffect(() => {
    apiFetch('/api/update/check')
      .then((response) => response.ok ? response.json() : null)
      .then((update) => {
        if (update?.updateAvailable && update.releaseUrl) setAvailableUpdate(update);
      })
      .catch(() => {});
  }, []);

  // Sync preview controls with the server so a reload or second client does
  // not silently use different processing settings.
  useEffect(() => {
    apiFetch('/api/settings')
      .then((response) => response.ok ? response.json() : null)
      .then((settings) => {
        if (!settings) return;
        if (typeof settings.revealDeepSky === 'boolean') setRevealDeepSky(settings.revealDeepSky);
        if (typeof settings.clearCityGlow === 'boolean') setClearCityGlow(settings.clearCityGlow);
      })
      .catch(() => {});
  }, []);

  // 2. Screen Wake Lock API (Keep phone display on during night session)
  useEffect(() => {
    const requestWakeLock = async () => {
      if ('wakeLock' in navigator) {
        try {
          wakeLockRef.current = await navigator.wakeLock.request('screen');
        } catch {
          // Wake lock rejected or unsupported
        }
      }
    };

    requestWakeLock();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        requestWakeLock();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (wakeLockRef.current) {
        wakeLockRef.current.release().catch(() => {});
      }
    };
  }, []);

  // 3. Device GPS Capture (Completely offline location coordinates)
  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setGpsCoords({
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            alt: pos.coords.altitude,
          });
        },
        () => {
          // Default or denied GPS permissions
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 600000 }
      );
    }
  }, []);

  const updateProcessingSetting = (name, value) => {
    apiFetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [name]: value }),
    }).catch(() => {
      // Keep the local control responsive; the next telemetry update will
      // reflect the server state if the request could not be delivered.
    });
  };

  // 4. OLED Astro Red Mode Persistence
  const toggleCrimson = () => {
    setIsCrimson(prev => {
      const next = !prev;
      localStorage.setItem('astrolink_crimson', String(next));
      return next;
    });
  };

  // 5. Sequence Execution Handlers
  const handleStartSequence = () => {
    setCommandError(null);
    setIsRunning(true);
    sendCommand({
      command: 'START_SEQUENCE',
      exposure_seconds: Number(exposureSeconds),
      frame_count: Number(frameCount),
      delay_seconds: Number(delaySeconds),
      iso: iso === 'Auto' ? null : iso,
      bulb_mode: Boolean(bulbMode)
    });
  };

  const handleStopSequence = () => {
    setIsRunning(false);
    sendCommand({ command: 'STOP_SEQUENCE' });
  };

  const handleResetStack = () => {
    prevStackCountRef.current = 0;
    sendCommand({ command: 'RESET_STACK' });
  };

  return (
    <div className={`fixed inset-0 w-full h-[100dvh] overflow-hidden select-none ${
      isCrimson ? 'theme-crimson bg-black text-red-500' : 'bg-black text-slate-100'
   }`}>
      {availableUpdate && (
        <div className="fixed top-3 left-1/2 -translate-x-1/2 z-[60] w-[min(92vw,30rem)] rounded-2xl border border-emerald-400/40 bg-slate-950/95 px-4 py-3 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <DownloadCloud className="h-5 w-5 shrink-0 text-emerald-400" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-white">AstroLink {availableUpdate.latestVersion} is available</p>
              <p className="text-[10px] text-slate-400">Download the verified release from GitHub. Nothing installs silently.</p>
              <a className="mt-1 inline-block text-[11px] font-semibold text-emerald-300 underline" href={availableUpdate.releaseUrl} target="_blank" rel="noreferrer">View release</a>
            </div>
            <button type="button" aria-label="Dismiss update" onClick={() => setAvailableUpdate(null)} className="rounded-full p-1 text-slate-400 hover:bg-white/10 hover:text-white"><X className="h-4 w-4" /></button>
          </div>
        </div>
      )}
      {commandError && (
        <div role="alert" className="fixed top-20 left-1/2 -translate-x-1/2 z-[55] max-w-[92vw] rounded-2xl border border-amber-400/40 bg-slate-950/95 px-4 py-3 text-center text-xs text-amber-200 shadow-2xl">
          <strong className="block text-amber-300">Sequence not started</strong>
          <span>{commandError}</span>
        </div>
      )}
      {/* Top Bar Actions (Top-Left): Profile & Camera Hub */}
      <div className="fixed top-4 left-4 z-40 flex items-center gap-2">
        <button
          type="button"
          onClick={() => {
            soundEngine.playClick();
            setAuthModalOpen(true);
          }}
          className={`h-10 px-3.5 rounded-full flex items-center gap-2 border shadow-xl backdrop-blur-xl transition-all duration-200 active:scale-90 ${
            isCrimson
              ? 'bg-black/90 border-red-900/50 text-red-400 hover:border-red-600'
              : 'bg-slate-950/80 border-white/10 text-slate-200 hover:border-white/30'
          }`}
          title="Astronomer Profile & Offline/Cloud Status"
        >
          <User className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs font-semibold uppercase tracking-wider hidden sm:inline">Profile</span>
        </button>

        <button
          type="button"
          onClick={() => {
            soundEngine.playClick();
            setCameraModalOpen(true);
          }}
          className={`h-10 px-3.5 rounded-full flex items-center gap-2 border shadow-xl backdrop-blur-xl transition-all duration-200 active:scale-90 ${
            isCrimson
              ? 'bg-black/90 border-red-900/50 text-red-400 hover:border-red-600'
              : 'bg-slate-950/80 border-white/10 text-slate-200 hover:border-white/30'
          }`}
          title="Camera Tether, USB Detection & Multi-OS Connection"
        >
          <Camera className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-xs font-semibold uppercase tracking-wider hidden sm:inline">Camera Hub</span>
        </button>
      </div>

      {/* Dynamic Island Status Capsule & Atmospheric Alert HUD */}
      <DynamicIsland
        telemetry={telemetry}
        isConnected={isConnected}
        isCrimson={isCrimson}
        audioEnabled={audioEnabled}
        onToggleAudio={() => {
          const next = soundEngine.toggleSound();
          setAudioEnabled(next);
        }}
        gpsCoords={gpsCoords}
      />

      {/* Primary Astronomical Hardware Viewport */}
      <Viewport
        previewUrl={previewUrl}
        telemetry={telemetry}
        isConnected={isConnected}
        isCrimson={isCrimson}
        revealDeepSky={revealDeepSky}
        clearCityGlow={clearCityGlow}
        backendUrl={httpUrl}
      />

      {/* Floating Bottom Ergonomic Pill Dock */}
      <Dock
        isRunning={isRunning}
        onStartSequence={handleStartSequence}
        onStopSequence={handleStopSequence}
        onResetStack={handleResetStack}
        onOpenSettings={() => setSessionSheetOpen(true)}
        onOpenExport={() => setExportSheetOpen(true)}
        isCrimson={isCrimson}
        onToggleCrimson={toggleCrimson}
        revealDeepSky={revealDeepSky}
        onToggleRevealDeepSky={() => {
            const next = !revealDeepSky;
            setRevealDeepSky(next);
            updateProcessingSetting('revealDeepSky', next);
          }}
        clearCityGlow={clearCityGlow}
        onToggleClearCityGlow={() => {
            const next = !clearCityGlow;
            setClearCityGlow(next);
            updateProcessingSetting('clearCityGlow', next);
          }}
      />

      {/* Session Settings Sheet */}
      <SessionSheet
        isOpen={sessionSheetOpen}
        onClose={() => setSessionSheetOpen(false)}
        isCrimson={isCrimson}
        exposureSeconds={exposureSeconds}
        setExposureSeconds={setExposureSeconds}
        frameCount={frameCount}
        setFrameCount={setFrameCount}
        delaySeconds={delaySeconds}
        setDelaySeconds={setDelaySeconds}
        iso={iso}
        setIso={setIso}
        bulbMode={bulbMode}
        setBulbMode={setBulbMode}
        isRunning={isRunning}
        onStartSequence={handleStartSequence}
        onStopSequence={handleStopSequence}
      />

      {/* 16-Bit Master TIFF Export Sheet */}
      <ExportSheet
        isOpen={exportSheetOpen}
        onClose={() => setExportSheetOpen(false)}
        isCrimson={isCrimson}
        telemetry={telemetry}
        gpsCoords={gpsCoords}
        backendUrl={httpUrl}
        previewUrl={previewUrl}
      />

      {/* Jules Autonomous Feedback System */}
      <FeedbackSheet
        isCrimson={isCrimson}
        backendUrl={httpUrl}
      />

      {/* Firebase Cloud Authentication Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        isCrimson={isCrimson}
      />

      {/* Camera & Hardware Direct Connection Hub */}
      <CameraModal
        isOpen={cameraModalOpen}
        onClose={() => setCameraModalOpen(false)}
        isCrimson={isCrimson}
        backendUrl={httpUrl}
      />
    </div>
  );
}
