import React, { useState, useEffect, useRef, useCallback } from 'react';
import DynamicIsland from './components/DynamicIsland';
import TelemetryHUD from './components/TelemetryHUD';
import Viewport from './components/Viewport';
import Dock from './components/Dock';
import SessionSheet from './components/SessionSheet';
import ExportSheet from './components/ExportSheet';
import FeedbackSheet from './components/FeedbackSheet';
import { soundEngine } from './utils/audio';

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

  // Sheets Visibility
  const [sessionSheetOpen, setSessionSheetOpen] = useState(false);
  const [exportSheetOpen, setExportSheetOpen] = useState(false);

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

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const prevStackCountRef = useRef(0);
  const wakeLockRef = useRef(null);

  // Determine backend HTTP and WS URLs
  const getBackendUrls = () => {
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const host = isLocalhost ? '127.0.0.1:8080' : `${window.location.hostname}:8080`;
    return {
      wsUrl: `ws://${host}/ws`,
      httpUrl: `http://${host}`,
    };
  };

  const { wsUrl, httpUrl } = getBackendUrls();

  // 1. WebSocket Auto-Reconnect with Exponential Backoff
  const connectWebSocket = useCallback(() => {
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
          if (data.type === 'telemetry') {
            setTelemetry(prev => {
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
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, backoff);
      };
    } catch {
      setIsConnected(false);
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
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
    <div className={`relative w-screen h-screen overflow-hidden select-none ${
      isCrimson ? 'theme-crimson bg-black text-red-500' : 'bg-black text-slate-100'
    }`}>
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
        isCrimson={isCrimson}
        revealDeepSky={revealDeepSky}
        clearCityGlow={clearCityGlow}
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
        onToggleRevealDeepSky={() => setRevealDeepSky(!revealDeepSky)}
        clearCityGlow={clearCityGlow}
        onToggleClearCityGlow={() => setClearCityGlow(!clearCityGlow)}
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
    </div>
  );
}
