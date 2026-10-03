import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Crosshair, ZoomIn, ZoomOut, Maximize2, X, Sparkles, Activity } from 'lucide-react';
import { soundEngine } from '../utils/audio';

export default function Viewport({ 
  previewUrl, 
  telemetry, 
  isCrimson, 
  revealDeepSky, 
  clearCityGlow 
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const imageRef = useRef(null);

  // Transform state for pan & zoom
  const [transform, setTransform] = useState({ scale: 1, x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const pinchStartRef = useRef(null);
  const lastTapRef = useRef(0);

  // Star targeting reticle & inset focus loupe
  const [targetPoint, setTargetPoint] = useState(null); // { imgX, imgY, normX, normY }
  const [showLoupe, setShowLoupe] = useState(false);
  const loupeCanvasRef = useRef(null);

  const fwhm = telemetry?.fwhm ?? 0;
  const isSharp = fwhm > 0 && fwhm <= 2.5;

  // Load preview image when previewUrl updates
  useEffect(() => {
    if (!previewUrl) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      imageRef.current = img;
      renderCanvas();
    };
    img.src = previewUrl;
  }, [previewUrl]);

  // Main canvas render function
  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear background
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);

    const img = imageRef.current;
    if (!img) {
      // Cosmic placeholder when waiting for first exposure
      renderStarFieldPlaceholder(ctx, width, height, isCrimson);
      return;
    }

    ctx.save();
    // Apply pan & zoom transform
    ctx.translate(transform.x, transform.y);
    ctx.scale(transform.scale, transform.scale);

    // Render astronomical preview with high quality smoothing
    ctx.imageSmoothingEnabled = transform.scale < 2.0;
    ctx.drawImage(img, 0, 0, img.width, img.height);

    // If star reticle is targeted, render Apple-style targeting brackets on image
    if (targetPoint) {
      renderReticle(ctx, targetPoint.imgX, targetPoint.imgY, isCrimson);
    }

    ctx.restore();

    // Render Loupe if active
    if (targetPoint && showLoupe && img) {
      renderLoupe(img, targetPoint.imgX, targetPoint.imgY);
    }
  }, [transform, targetPoint, showLoupe, isCrimson]);

  // Cosmic empty state
  const renderStarFieldPlaceholder = (ctx, w, h, crimson) => {
    ctx.fillStyle = crimson ? '#150303' : '#030712';
    ctx.fillRect(0, 0, w, h);

    // Draw faint celestial coordinate lines
    ctx.strokeStyle = crimson ? 'rgba(239, 68, 68, 0.06)' : 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    const step = 80;
    for (let x = 0; x < w; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += step) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Draw subtle guide crosshairs at center
    ctx.strokeStyle = crimson ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.15)';
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, 40, 0, Math.PI * 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(w / 2 - 60, h / 2);
    ctx.lineTo(w / 2 + 60, h / 2);
    ctx.moveTo(w / 2, h / 2 - 60);
    ctx.lineTo(w / 2, h / 2 + 60);
    ctx.stroke();
  };

  // Render Apple targeting brackets around star
  const renderReticle = (ctx, x, y, crimson) => {
    const size = 24;
    const arm = 8;
    ctx.strokeStyle = crimson ? '#ef4444' : '#10b981';
    ctx.lineWidth = 2;
    ctx.shadowColor = crimson ? 'rgba(239, 68, 68, 0.6)' : 'rgba(16, 185, 129, 0.6)';
    ctx.shadowBlur = 6;

    // Top-left corner
    ctx.beginPath();
    ctx.moveTo(x - size, y - size + arm);
    ctx.lineTo(x - size, y - size);
    ctx.lineTo(x - size + arm, y - size);
    ctx.stroke();

    // Top-right corner
    ctx.beginPath();
    ctx.moveTo(x + size - arm, y - size);
    ctx.lineTo(x + size, y - size);
    ctx.lineTo(x + size, y - size + arm);
    ctx.stroke();

    // Bottom-left corner
    ctx.beginPath();
    ctx.moveTo(x - size, y + size - arm);
    ctx.lineTo(x - size, y + size);
    ctx.lineTo(x - size + arm, y + size);
    ctx.stroke();

    // Bottom-right corner
    ctx.beginPath();
    ctx.moveTo(x + size - arm, y + size);
    ctx.lineTo(x + size, y + size);
    ctx.lineTo(x + size, y + size - arm);
    ctx.stroke();

    // Center focal point
    ctx.beginPath();
    ctx.arc(x, y, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = crimson ? '#ef4444' : '#10b981';
    ctx.fill();

    ctx.shadowBlur = 0;
  };

  // Render 6x Magnification Loupe Inset
  const renderLoupe = (img, x, y) => {
    const loupe = loupeCanvasRef.current;
    if (!loupe) return;
    const lCtx = loupe.getContext('2d');
    if (!lCtx) return;

    const cropSize = 36; // 36x36 px source crop
    const sx = Math.max(0, Math.min(img.width - cropSize, x - cropSize / 2));
    const sy = Math.max(0, Math.min(img.height - cropSize, y - cropSize / 2));

    lCtx.imageSmoothingEnabled = false; // Nearest neighbor for pixelated focus inspection
    lCtx.clearRect(0, 0, loupe.width, loupe.height);
    lCtx.drawImage(img, sx, sy, cropSize, cropSize, 0, 0, loupe.width, loupe.height);

    // Crosshairs in loupe
    lCtx.strokeStyle = isCrimson ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)';
    lCtx.lineWidth = 1;
    lCtx.beginPath();
    lCtx.moveTo(loupe.width / 2, 0);
    lCtx.lineTo(loupe.width / 2, loupe.height);
    lCtx.moveTo(0, loupe.height / 2);
    lCtx.lineTo(loupe.width, loupe.height / 2);
    lCtx.stroke();
  };

  // Resize canvas to fill container
  useEffect(() => {
    const handleResize = () => {
      const container = containerRef.current;
      const canvas = canvasRef.current;
      if (!container || !canvas) return;

      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;

      // Fit to screen on initial load
      if (imageRef.current) {
        fitToScreen(imageRef.current);
      } else {
        renderCanvas();
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [renderCanvas]);

  // Fit image to screen bounds
  const fitToScreen = (img = imageRef.current) => {
    const canvas = canvasRef.current;
    if (!canvas || !img) return;

    const scaleX = canvas.width / img.width;
    const scaleY = canvas.height / img.height;
    const scale = Math.min(scaleX, scaleY) * 0.95;

    const x = (canvas.width - img.width * scale) / 2;
    const y = (canvas.height - img.height * scale) / 2;

    setTransform({ scale, x, y });
  };

  // Re-render when transform changes
  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);

  // Mouse wheel zoom
  const handleWheel = (e) => {
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const newScale = Math.max(0.1, Math.min(transform.scale * zoomFactor, 25));

    const newX = mouseX - (mouseX - transform.x) * (newScale / transform.scale);
    const newY = mouseY - (mouseY - transform.y) * (newScale / transform.scale);

    setTransform({ scale: newScale, x: newX, y: newY });
  };

  // Mouse drag pan
  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX - transform.x,
      y: e.clientY - transform.y,
      initClientX: e.clientX,
      initClientY: e.clientY,
    };
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setTransform(prev => ({
      ...prev,
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y,
    }));
  };

  const handleMouseUp = (e) => {
    if (!isDragging) return;
    setIsDragging(false);

    // If movement was minimal (< 5px), treat as tap/click on a star
    const dx = Math.abs(e.clientX - dragStartRef.current.initClientX);
    const dy = Math.abs(e.clientY - dragStartRef.current.initClientY);
    if (dx < 5 && dy < 5) {
      handleReticleTap(e.clientX, e.clientY);
    }
  };

  // Touch handling (pinch zoom + single-finger pan + double-tap)
  const handleTouchStart = (e) => {
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      const now = Date.now();
      if (now - lastTapRef.current < 300) {
        // Double-tap detected -> Reset to fit
        fitToScreen();
        soundEngine.playClick();
      }
      lastTapRef.current = now;

      setIsDragging(true);
      dragStartRef.current = {
        x: touch.clientX - transform.x,
        y: touch.clientY - transform.y,
        initClientX: touch.clientX,
        initClientY: touch.clientY,
      };
      pinchStartRef.current = null;
    } else if (e.touches.length === 2) {
      setIsDragging(false);
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const distance = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
      pinchStartRef.current = {
        distance,
        scale: transform.scale,
        center: {
          x: (t1.clientX + t2.clientX) / 2,
          y: (t1.clientY + t2.clientY) / 2,
        }
      };
    }
  };

  const handleTouchMove = (e) => {
    if (e.touches.length === 1 && isDragging) {
      const touch = e.touches[0];
      setTransform(prev => ({
        ...prev,
        x: touch.clientX - dragStartRef.current.x,
        y: touch.clientY - dragStartRef.current.y,
      }));
    } else if (e.touches.length === 2 && pinchStartRef.current) {
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const distance = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
      const factor = distance / pinchStartRef.current.distance;
      const newScale = Math.max(0.1, Math.min(pinchStartRef.current.scale * factor, 25));

      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const pinchX = pinchStartRef.current.center.x - rect.left;
      const pinchY = pinchStartRef.current.center.y - rect.top;

      const newX = pinchX - (pinchX - transform.x) * (newScale / transform.scale);
      const newY = pinchY - (pinchY - transform.y) * (newScale / transform.scale);

      setTransform({ scale: newScale, x: newX, y: newY });
    }
  };

  const handleTouchEnd = (e) => {
    if (isDragging && e.changedTouches.length === 1) {
      const touch = e.changedTouches[0];
      const dx = Math.abs(touch.clientX - dragStartRef.current.initClientX);
      const dy = Math.abs(touch.clientY - dragStartRef.current.initClientY);
      if (dx < 6 && dy < 6) {
        handleReticleTap(touch.clientX, touch.clientY);
      }
    }
    setIsDragging(false);
    pinchStartRef.current = null;
  };

  // Tap on viewport to drop Focus Reticle on a star
  const handleReticleTap = (clientX, clientY) => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;

    const rect = canvas.getBoundingClientRect();
    const canvasX = clientX - rect.left;
    const canvasY = clientY - rect.top;

    // Convert canvas coordinates back to image pixel space
    const imgX = (canvasX - transform.x) / transform.scale;
    const imgY = (canvasY - transform.y) / transform.scale;

    // Check if click was inside image boundaries
    if (imgX >= 0 && imgX <= img.width && imgY >= 0 && imgY <= img.height) {
      setTargetPoint({
        imgX: Math.round(imgX),
        imgY: Math.round(imgY),
        normX: imgX / img.width,
        normY: imgY / img.height,
      });
      setShowLoupe(true);
      soundEngine.playClick();
    }
  };

  return (
    <div 
      ref={containerRef} 
      className="relative w-full h-full overflow-hidden bg-black select-none touch-none"
    >
      {/* Primary Astronomical Hardware Canvas */}
      <canvas
        ref={canvasRef}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        className="w-full h-full cursor-crosshair block"
      />

      {/* Floating Viewport Quick Controls (Top-Right) */}
      <div className="absolute top-20 right-4 z-30 flex flex-col gap-2">
        <button
          type="button"
          onClick={() => fitToScreen()}
          className={`p-3 rounded-full border backdrop-blur-xl transition-all duration-200 active:scale-90 ${
            isCrimson 
              ? 'bg-black/80 border-red-900/40 text-red-500 hover:border-red-600' 
              : 'bg-slate-950/70 border-white/10 text-slate-200 hover:border-white/30'
          }`}
          title="Fit to Screen (Double Tap)"
        >
          <Maximize2 className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => {
            const newScale = Math.min(transform.scale * 1.5, 25);
            setTransform(prev => ({ ...prev, scale: newScale }));
            soundEngine.playClick();
          }}
          className={`p-3 rounded-full border backdrop-blur-xl transition-all duration-200 active:scale-90 ${
            isCrimson 
              ? 'bg-black/80 border-red-900/40 text-red-500 hover:border-red-600' 
              : 'bg-slate-950/70 border-white/10 text-slate-200 hover:border-white/30'
          }`}
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => {
            const newScale = Math.max(transform.scale * 0.7, 0.1);
            setTransform(prev => ({ ...prev, scale: newScale }));
            soundEngine.playClick();
          }}
          className={`p-3 rounded-full border backdrop-blur-xl transition-all duration-200 active:scale-90 ${
            isCrimson 
              ? 'bg-black/80 border-red-900/40 text-red-500 hover:border-red-600' 
              : 'bg-slate-950/70 border-white/10 text-slate-200 hover:border-white/30'
          }`}
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
      </div>

      {/* Interactive Focus Loupe & Circular Sharpness Gauge */}
      {targetPoint && showLoupe && (
        <div 
          className={`absolute bottom-28 left-4 z-40 p-4 rounded-3xl border shadow-2xl backdrop-blur-2xl animate-scale-in flex flex-col gap-3 ${
            isCrimson 
              ? 'bg-black/95 border-red-700/60 text-red-500' 
              : 'bg-slate-950/90 border-white/15 text-slate-100'
          }`}
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-1.5">
              <Crosshair className={`w-4 h-4 ${isCrimson ? 'text-red-500' : 'text-emerald-400'}`} />
              <span className="text-[11px] font-mono uppercase tracking-wider font-semibold">
                Star Focus Reticle (6x)
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                setShowLoupe(false);
                setTargetPoint(null);
                soundEngine.playClick();
              }}
              className="p-1 rounded-full hover:bg-white/10 opacity-70 hover:opacity-100"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center gap-4">
            {/* 6x Pixel Zoom Canvas */}
            <div className="relative w-28 h-28 rounded-2xl overflow-hidden border border-inherit/20 bg-black">
              <canvas
                ref={loupeCanvasRef}
                width={112}
                height={112}
                className="w-full h-full block"
              />
              <div className="absolute bottom-1 right-1 text-[9px] font-mono px-1 rounded bg-black/60 opacity-60">
                {targetPoint.imgX},{targetPoint.imgY}
              </div>
            </div>

            {/* Circular Focus Quality Gauge */}
            <div className="flex flex-col items-center justify-center gap-1 text-center">
              <div className="relative flex items-center justify-center w-20 h-20">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                  {/* Background track */}
                  <path
                    className="opacity-20"
                    stroke={isCrimson ? '#ef4444' : '#ffffff'}
                    strokeWidth="3.2"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  {/* Active gauge arc: 0 to 4px scale, inverse so smaller is fuller */}
                  <path
                    stroke={isSharp ? (isCrimson ? '#ef4444' : '#10b981') : '#f59e0b'}
                    strokeDasharray={`${Math.max(10, Math.min(100, (4.5 - (fwhm || 2.2)) / 3.5 * 100))}, 100`}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center font-mono">
                  <span className={`text-sm font-bold ${
                    isSharp ? (isCrimson ? 'text-red-400' : 'text-emerald-400') : 'text-amber-400'
                  }`}>
                    {fwhm > 0 ? fwhm.toFixed(1) : '2.1'}
                  </span>
                  <span className="text-[8px] opacity-60">PX FWHM</span>
                </div>
              </div>

              <span className={`text-[10px] font-medium ${
                isSharp ? (isCrimson ? 'text-red-400' : 'text-emerald-400') : 'text-amber-400'
              }`}>
                {isSharp ? 'Pinpoint Focus' : 'Focus Drift'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Active Processing Filters Indicator (Bottom Left) */}
      <div className="absolute bottom-28 right-4 z-20 flex flex-col gap-1.5 pointer-events-none text-right font-mono text-[10px]">
        {revealDeepSky && (
          <div className="flex items-center justify-end gap-1.5 opacity-80">
            <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300">
              REVEAL DEEP SKY (MTF)
            </span>
          </div>
        )}
        {clearCityGlow && (
          <div className="flex items-center justify-end gap-1.5 opacity-80">
            <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300">
              CLEAR CITY GLOW
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
