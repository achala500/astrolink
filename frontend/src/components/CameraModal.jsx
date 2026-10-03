import React, { useState, useEffect, useCallback } from 'react';
import {
  Camera,
  X,
  Usb,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  HardDrive,
  ShieldCheck
} from 'lucide-react';
import { soundEngine } from '../utils/audio';

export default function CameraModal({ isOpen, onClose, isCrimson, backendUrl }) {
  const [detectedCameras, setDetectedCameras] = useState([]);
  const [isScanning, setIsScanning] = useState(false);
  const [activeTab, setActiveTab] = useState('status'); // 'status' | 'guide' | 'agent'

  const scanCameras = useCallback(async () => {
    setIsScanning(true);
    soundEngine.playClick();
    try {
      const res = await fetch(`${backendUrl || ''}/api/camera/detect`);
      if (res.ok) {
        const data = await res.json();
        setDetectedCameras(data.cameras || []);
      }
    } catch (err) {
      console.error('Camera detection scan error:', err);
    } finally {
      setIsScanning(false);
    }
  }, [backendUrl]);

  useEffect(() => {
    if (isOpen) {
      scanCameras();
    }
  }, [isOpen, scanCameras]);

  if (!isOpen) return null;

  return (
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
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight">Camera & Hardware Hub</h2>
              <p className="text-[11px] opacity-60">Multi-OS USB PTP & Field Connection Guide</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onClose();
            }}
            className="p-2 rounded-full hover:bg-white/10 transition-colors opacity-70 hover:opacity-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 my-4 p-1 rounded-2xl bg-white/[0.04] border border-inherit/10 flex-shrink-0">
          <button
            type="button"
            onClick={() => { soundEngine.playClick(); setActiveTab('status'); }}
            className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'status'
                ? isCrimson ? 'bg-red-600 text-black shadow-md' : 'bg-emerald-500 text-black shadow-md'
                : 'opacity-60 hover:opacity-100'
            }`}
          >
            Detected Hardware
          </button>
          <button
            type="button"
            onClick={() => { soundEngine.playClick(); setActiveTab('guide'); }}
            className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'guide'
                ? isCrimson ? 'bg-red-600 text-black shadow-md' : 'bg-emerald-500 text-black shadow-md'
                : 'opacity-60 hover:opacity-100'
            }`}
          >
            Connection Guide
          </button>
          <button
            type="button"
            onClick={() => { soundEngine.playClick(); setActiveTab('agent'); }}
            className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'agent'
                ? isCrimson ? 'bg-red-600 text-black shadow-md' : 'bg-emerald-500 text-black shadow-md'
                : 'opacity-60 hover:opacity-100'
            }`}
          >
            Multi-OS Node
          </button>
        </div>

        {/* Tab 1: Hardware Status & Auto-Detect */}
        {activeTab === 'status' && (
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider opacity-60">Connected Cameras</span>
              <button
                type="button"
                onClick={scanCameras}
                disabled={isScanning}
                className="flex items-center gap-1.5 px-3 py-1 rounded-xl text-[11px] font-semibold bg-white/5 hover:bg-white/10 border border-white/10 active:scale-95 transition-all"
              >
                <RefreshCw className={`w-3 h-3 ${isScanning ? 'animate-spin' : ''}`} />
                <span>Re-scan USB</span>
              </button>
            </div>

            {detectedCameras.length > 0 ? (
              <div className="space-y-2">
                {detectedCameras.map((cam, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-2xl bg-white/[0.04] border border-inherit/15 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
                        <CheckCircle2 className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-bold">{cam.name}</div>
                        <div className="text-[10px] font-mono opacity-60">
                          {cam.vendor} • {cam.connection_type.toUpperCase()}
                        </div>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      READY
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200">
                <div className="flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs space-y-1">
                    <p className="font-semibold">No Direct USB Camera Detected Yet</p>
                    <p className="text-[11px] opacity-80 leading-relaxed">
                      Connect your DSLR or Mirrorless camera (Canon, Nikon, Sony, Fuji, ZWO) via USB cable to this PC or Raspberry Pi field box. Turn camera dial to <b>Manual (M)</b> or <b>Bulb (B)</b>.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Input Options Grid */}
            <div className="grid grid-cols-2 gap-2 pt-2">
              <div className="p-3 rounded-2xl bg-white/[0.02] border border-inherit/10">
                <div className="flex items-center gap-1.5 text-xs font-semibold mb-1">
                  <Usb className="w-3.5 h-3.5 text-blue-400" /> USB PTP Tether
                </div>
                <p className="text-[10px] opacity-60 leading-relaxed">
                  Direct cable connection. Shutter triggered over USB wire with instant RAW download.
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-white/[0.02] border border-inherit/10">
                <div className="flex items-center gap-1.5 text-xs font-semibold mb-1">
                  <HardDrive className="w-3.5 h-3.5 text-emerald-400" /> Hot-Folder / SD Card
                </div>
                <p className="text-[10px] opacity-60 leading-relaxed">
                  Automatic ingestion from SD card DCIM or folders output by N.I.N.A, ASIAIR, or SharpCap.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Connection Architecture Guide */}
        {activeTab === 'guide' && (
          <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-inherit/15 space-y-2">
              <div className="font-bold flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-emerald-500 text-black flex items-center justify-center font-mono font-bold text-[11px]">1</span>
                <span>Camera Connects via USB (Zero Browser Needed)</span>
              </div>
              <p className="text-[11px] opacity-75 leading-relaxed pl-7">
                DSLRs and astro cameras have no web browser. They plug via a standard <b>USB cable</b> (USB-C/mini-USB) directly into your laptop or Raspberry Pi mounted on the telescope. AstroLink talks directly to the camera over USB PTP protocol.
              </p>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-inherit/15 space-y-2">
              <div className="font-bold flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-emerald-500 text-black flex items-center justify-center font-mono font-bold text-[11px]">2</span>
                <span>Phone / Tablet Connects via Local Wi-Fi</span>
              </div>
              <p className="text-[11px] opacity-75 leading-relaxed pl-7">
                Your phone or tablet connects to the same local Wi-Fi router or phone mobile hotspot. Open <b>http://astrolink.local:8080</b> in Safari or Chrome. Your phone acts as the wireless viewfinder and remote shutter control!
              </p>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-inherit/15 space-y-2">
              <div className="font-bold flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-emerald-500 text-black flex items-center justify-center font-mono font-bold text-[11px]">3</span>
                <span>Live Stacking Happens in Real Time</span>
              </div>
              <p className="text-[11px] opacity-75 leading-relaxed pl-7">
                Every sub-exposure shot by the camera streams over the local network into the Welford stacking engine, eliminating noise and revealing nebulae live on your screen.
              </p>
            </div>
          </div>
        )}

        {/* Tab 3: Multi-OS Standalone Camera Agent */}
        {activeTab === 'agent' && (
          <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
            <p className="text-[11px] opacity-75 leading-relaxed">
              If your camera is connected to a <b>Raspberry Pi</b>, <b>Linux box (StellarMate/Astroberry)</b>, or another laptop at the telescope mount, run the standalone AstroLink camera bridge:
            </p>

            <div className="p-3 rounded-2xl bg-black/60 border border-white/10 font-mono text-[11px] select-all space-y-1">
              <div className="text-emerald-400"># Auto-discovers station and streams camera sub-exposures:</div>
              <div className="text-white">python astrolink_camera_agent.py</div>
            </div>

            <div className="p-3 rounded-2xl bg-black/60 border border-white/10 font-mono text-[11px] select-all space-y-1">
              <div className="text-emerald-400"># Or watch specific directory / SD card:</div>
              <div className="text-white">python astrolink_camera_agent.py --watch /media/pi/CANON/DCIM</div>
            </div>

            <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 text-[11px] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 flex-shrink-0 text-emerald-400" />
              <span>100% Offline & Headless — zero browser, zero internet, zero cloud dependencies.</span>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="pt-4 mt-2 border-t border-inherit/10 flex items-center justify-between flex-shrink-0">
          <div className="text-[10px] font-mono opacity-50">
            Station IP: astrolink.local:8080
          </div>
          <button
            type="button"
            onClick={() => {
              soundEngine.playClick();
              onClose();
            }}
            className={`px-5 py-2 rounded-2xl font-bold text-xs uppercase tracking-wider transition-all active:scale-95 ${
              isCrimson
                ? 'bg-red-600 text-black hover:bg-red-500'
                : 'bg-emerald-500 text-black hover:bg-emerald-400'
            }`}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
