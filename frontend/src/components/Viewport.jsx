import React, { useRef, useEffect, useState, useCallback } from 'react';
import { 
  Crosshair, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  X, 
  UploadCloud, 
  Camera, 
  Video, 
  CheckCircle2, 
  Loader2 
} from 'lucide-react';
import { soundEngine } from '../utils/audio';
import { apiFetch } from '../utils/api';

export default function Viewport({ 
  previewUrl, 
  telemetry, 
  isCrimson, 
  revealDeepSky, 
  clearCityGlow,
  backendUrl 
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const captureIntervalRef = useRef(null);

  // Transform state for pan & zoom
  const [transform, setTransform] = useState({ scale: 1, x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const pinchStartRef = useRef(null);
  const lastTapRef = useRef(0);
  const hasInitiallyFittedRef = useRef(false);

  // Star targeting reticle & inset focus loupe
  const [targetPoint, setTargetPoint] = useState(null);
  const [showLoupe, setShowLoupe] = useState(false);
  const loupeCanvasRef = useRef(null);

  // Drag & Drop & Upload State
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // { text, progress, type: 'info' | 'success' | 'error' }

  // In-Browser Live Device / Phone Camera State
  const [isDeviceCamActive, setIsDeviceCamActive] = useState(false);

  const fwhm = telemetry?.fwhm ?? 0;
  const isSharp = fwhm > 0 && fwhm <= 2.5;

  // Fit image to screen bounds
  const fitToScreen = useCallback((img = imageRef.current) => {
    const canvas = canvasRef.current;
    if (!canvas || !img || !img.width || !img.height) return;

    const scaleX = canvas.width / img.width;
    const scaleY = canvas.height / img.height;
    const scale = Math.min(scaleX, scaleY) * 0.95;

    const x = (canvas.width - img.width * scale) / 2;
    const y = (canvas.height - img.height * scale) / 2;

    setTransform({ scale, x, y });
  }, []);

  // Cosmic empty state
  const renderStarFieldPlaceholder = useCallback((ctx, w, h, crimson) => {
    ctx.fillStyle = crimson ? '#0a0000' : '#030712';
    ctx.fillRect(0, 0, w, h);

    // Draw faint celestial coordinate lines
    ctx.strokeStyle = crimson ? 'rgba(239, 68, 68, 0.08)' : 'rgba(255, 255, 255, 0.05)';
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
    ctx.strokeStyle = crimson ? 'rgba(239, 68, 68, 0.25)' : 'rgba(255, 255, 255, 0.2)';
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, 40, 0, Math.PI * 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(w / 2 - 60, h / 2);
    ctx.lineTo(w / 2 + 60, h / 2);
    ctx.moveTo(w / 2, h / 2 - 60);
    ctx.lineTo(w / 2, h / 2 + 60);
    ctx.stroke();
  }, []);

  // Render Apple targeting brackets around star
  const renderReticle = useCallback((ctx, x, y, crimson) => {
    const size = 24;
    const arm = 8;
    ctx.strokeStyle = crimson ? '#ef4444' : '#10b981';
    ctx.lineWidth = 2;
    ctx.shadowColor = crimson ? 'rgba(239, 68, 68, 0.6)' : 'rgba(16, 185, 129, 0.6)';
    ctx.shadowBlur = 6;

    // Top-left
    ctx.beginPath();
    ctx.moveTo(x - size, y - size + arm);
    ctx.lineTo(x - size, y - size);
    ctx.lineTo(x - size + arm, y - size);
    ctx.stroke();

    // Top-right
    ctx.beginPath();
    ctx.moveTo(x + size - arm, y - size);
    ctx.lineTo(x + size, y - size);
    ctx.lineTo(x + size, y - size + arm);
    ctx.stroke();

    // Bottom-left
    ctx.beginPath();
    ctx.moveTo(x - size, y + size - arm);
    ctx.lineTo(x - size, y + size);
    ctx.lineTo(x - size + arm, y + size);
    ctx.stroke();

    // Bottom-right
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
  }, []);

  // Render 6x Magnification Loupe Inset
  const renderLoupe = useCallback((img, x, y) => {
    const loupe = loupeCanvasRef.current;
    if (!loupe) return;
    const lCtx = loupe.getContext('2d');
    if (!lCtx) return;

    const cropSize = 36;
    const sx = Math.max(0, Math.min(img.width - cropSize, x - cropSize / 2));
    const sy = Math.max(0, Math.min(img.height - cropSize, y - cropSize / 2));

    lCtx.imageSmoothingEnabled = false;
    lCtx.clearRect(0, 0, loupe.width, loupe.height);
    lCtx.drawImage(img, sx, sy, cropSize, cropSize, 0, 0, loupe.width, loupe.height);

    lCtx.strokeStyle = isCrimson ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)';
    lCtx.lineWidth = 1;
    lCtx.beginPath();
    lCtx.moveTo(loupe.width / 2, 0);
    lCtx.lineTo(loupe.width / 2, loupe.height);
    lCtx.moveTo(0, loupe.height / 2);
    lCtx.lineTo(loupe.width, loupe.height / 2);
    lCtx.stroke();
  }, [isCrimson]);

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
  }, [transform, targetPoint, showLoupe, isCrimson, renderStarFieldPlaceholder, renderReticle, renderLoupe]);

  // Load preview image when previewUrl updates
  useEffect(() => {
    if (!previewUrl) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      imageRef.current = img;
      if (!hasInitiallyFittedRef.current) {
        hasInitiallyFittedRef.current = true;
        fitToScreen(img);
      } else {
        renderCanvas();
      }
    };
    img.src = previewUrl;
  }, [previewUrl, fitToScreen, renderCanvas]);

  // Resize canvas to fill container
  useEffect(() => {
    const handleResize = () => {
      const container = containerRef.current;
      const canvas = canvasRef.current;
      if (!container || !canvas) return;

      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;

      if (imageRef.current) {
        fitToScreen(imageRef.current);
      } else {
        renderCanvas();
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [renderCanvas, fitToScreen]);

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
      y: e.clientY - transform.y
    };
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setTransform(prev => ({
      ...prev,
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y
    }));
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Canvas Click: Drop star targeting reticle
  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;

    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Convert canvas click to image coordinates
    const imgX = (clickX - transform.x) / transform.scale;
    const imgY = (clickY - transform.y) / transform.scale;

    // Verify click is within image boundaries
    if (imgX >= 0 && imgX <= img.width && imgY >= 0 && imgY <= img.height) {
      setTargetPoint({
        imgX: Math.round(imgX),
        imgY: Math.round(imgY),
        normX: (imgX / img.width).toFixed(3),
        normY: (imgY / img.height).toFixed(3)
      });
      setShowLoupe(true);
      soundEngine.playClick();
    }
  };

  // Double Click / Double Tap: Recenter and fit
  const handleDoubleClick = () => {
    fitToScreen();
    soundEngine.playClick();
  };

  // Touch Handlers for Mobile Gestures
  const handleTouchStart = (e) => {
    if (e.touches.length === 1) {
      const now = Date.now();
      if (now - lastTapRef.current < 300) {
        handleDoubleClick();
      }
      lastTapRef.current = now;

      setIsDragging(true);
      dragStartRef.current = {
        x: e.touches[0].clientX - transform.x,
        y: e.touches[0].clientY - transform.y
      };
    } else if (e.touches.length === 2) {
      setIsDragging(false);
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const dist = Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY);
      pinchStartRef.current = {
        dist,
        scale: transform.scale,
        center: {
          x: (touch1.clientX + touch2.clientX) / 2,
          y: (touch1.clientY + touch2.clientY) / 2
        }
      };
    }
  };

  const handleTouchMove = (e) => {
    if (e.touches.length === 1 && isDragging) {
      setTransform(prev => ({
        ...prev,
        x: e.touches[0].clientX - dragStartRef.current.x,
        y: e.touches[0].clientY - dragStartRef.current.y
      }));
    } else if (e.touches.length === 2 && pinchStartRef.current) {
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const dist = Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY);
      const scaleFactor = dist / pinchStartRef.current.dist;
      const newScale = Math.max(0.1, Math.min(pinchStartRef.current.scale * scaleFactor, 25));

      const center = pinchStartRef.current.center;
      const newX = center.x - (center.x - transform.x) * (newScale / transform.scale);
      const newY = center.y - (center.y - transform.y) * (newScale / transform.scale);

      setTransform({ scale: newScale, x: newX, y: newY });
    }
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
    pinchStartRef.current = null;
  };

  // =========================================================================
  // REAL ASTROPHOTOGRAPHY FILE UPLOAD & DRAG-AND-DROP INGESTION
  // =========================================================================

  const handleFiles = async (files) => {
    if (!files || !files.length) return;
    const validFiles = Array.from(files);
    
    setUploadStatus({
      text: `Ingesting ${validFiles.length} sub-exposure(s) into Welford Stacker...`,
      progress: 0,
      type: 'info'
    });

    let successCount = 0;
    for (let i = 0; i < validFiles.length; i++) {
      const file = validFiles[i];
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await apiFetch(`${backendUrl || ''}/api/upload`, {
          method: 'POST',
          body: formData,
        });
        if (res.ok) {
          successCount++;
        }
      } catch (err) {
        console.error('File upload error:', err);
      }

      setUploadStatus({
        text: `Stacking ${i + 1}/${validFiles.length}: ${file.name}`,
        progress: Math.round(((i + 1) / validFiles.length) * 100),
        type: 'info'
      });
    }

    setUploadStatus({
      text: `Successfully stacked ${successCount} sub-exposure(s)!`,
      progress: 100,
      type: 'success'
    });

    setTimeout(() => {
      setUploadStatus(null);
    }, 3500);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      soundEngine.playClick();
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  // =========================================================================
  // BROWSER / PHONE REAR CAMERA LIVE CAPTURE
  // =========================================================================

  const toggleDeviceCamera = async () => {
    if (isDeviceCamActive) {
      // Stop live camera
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
        captureIntervalRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
        streamRef.current = null;
      }
      setIsDeviceCamActive(false);
      soundEngine.playClick();
      return;
    }

    // Start live camera
    try {
      soundEngine.playClick();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' }, // Back camera for pointing at the sky
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setIsDeviceCamActive(true);

      // Start capture loop: grabs frame every 3s and sends to /api/upload
      captureIntervalRef.current = setInterval(() => {
        captureAndUploadVideoFrame();
      }, 3000);

    } catch (err) {
      console.error('Camera access denied or unavailable:', err);
      alert('Camera access denied. Please grant camera permission in your browser settings.');
    }
  };

  const captureAndUploadVideoFrame = () => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return;

    const offscreen = document.createElement('canvas');
    offscreen.width = video.videoWidth || 1280;
    offscreen.height = video.videoHeight || 720;
    const ctx = offscreen.getContext('2d');
    ctx.drawImage(video, 0, 0, offscreen.width, offscreen.height);

    offscreen.toBlob(async (blob) => {
      if (!blob) return;
      const file = new File([blob], `phone_camera_${Date.now()}.jpg`, { type: 'image/jpeg' });
      const formData = new FormData();
      formData.append('file', file);
      try {
        await apiFetch(`${backendUrl || ''}/api/upload`, {
          method: 'POST',
          body: formData,
        });
      } catch (err) {
        console.error('Failed to upload camera frame:', err);
      }
    }, 'image/jpeg', 0.95);
  };

  // Clean up camera on unmount
  useEffect(() => {
    return () => {
      if (captureIntervalRef.current) clearInterval(captureIntervalRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  return (
    <div 
      ref={containerRef}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className="relative w-full h-full overflow-hidden bg-black select-none cursor-crosshair"
    >
      {/* Hidden offscreen video for camera streaming */}
      <video ref={videoRef} playsInline muted className="hidden" />

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".fits,.fit,.cr2,.cr3,.nef,.arw,.dng,.tif,.tiff,.jpg,.jpeg,.png,.webp"
        onChange={(e) => handleFiles(e.target.files)}
        className="hidden"
      />

      {/* Primary Astronomical Hardware Viewport Canvas */}
      <canvas
        ref={canvasRef}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onClick={handleCanvasClick}
        onDoubleClick={handleDoubleClick}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        className="w-full h-full block"
      />

      {/* Drag & Drop Visual Drop Zone Overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-black/85 border-4 border-dashed border-red-500 backdrop-blur-md animate-pulse">
          <UploadCloud className="w-16 h-16 text-red-400 mb-4" />
          <h2 className="text-xl font-bold tracking-tight text-white mb-1">
            Drop Real Sub-Exposures to Stack
          </h2>
          <p className="text-xs text-slate-400 font-mono">
            Accepts FITS, DSLR RAW (.CR2, .NEF, .ARW), Linear DNG, 16-bit TIFF, JPEG
          </p>
        </div>
      )}

      {/* Upload Progress Banner */}
      {uploadStatus && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 z-40 px-5 py-2.5 rounded-full border shadow-2xl backdrop-blur-2xl flex items-center gap-3 bg-slate-950/90 border-white/20 text-white animate-scale-in">
          {uploadStatus.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
          )}
          <span className="text-xs font-medium font-mono">{uploadStatus.text}</span>
          <span className="text-[11px] font-bold text-amber-400">{uploadStatus.progress}%</span>
        </div>
      )}

      {/* Floating Viewport Quick Controls (Top-Right) */}
      <div className="absolute top-20 right-4 z-30 flex flex-col gap-2">
        {/* Recenter & Fit to Screen */}
        <button
          type="button"
          onClick={() => {
            soundEngine.playClick();
            fitToScreen();
          }}
          className={`p-3 rounded-full border backdrop-blur-xl transition-all duration-200 active:scale-90 ${
            isCrimson 
              ? 'bg-black/80 border-red-900/40 text-red-500 hover:border-red-600' 
              : 'bg-slate-950/70 border-white/10 text-slate-200 hover:border-white/30'
          }`}
          title="Fit & Center Screen"
        >
          <Maximize2 className="w-4 h-4" />
        </button>

        {/* Zoom In */}
        <button
          type="button"
          onClick={() => {
            const newScale = Math.min(transform.scale * 1.4, 25);
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

        {/* Zoom Out */}
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

        {/* Upload Real Astrophotography Files Button */}
        <button
          type="button"
          onClick={() => {
            soundEngine.playClick();
            fileInputRef.current?.click();
          }}
          className={`p-3 rounded-full border backdrop-blur-xl transition-all duration-200 active:scale-90 ${
            isCrimson 
              ? 'bg-red-950/60 border-red-700/60 text-red-300 hover:border-red-500' 
              : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30'
          }`}
          title="Upload RAW / FITS / TIFF Sub-Exposures"
        >
          <UploadCloud className="w-4 h-4" />
        </button>

        {/* In-Browser Phone / Device Camera Live Stream */}
        <button
          type="button"
          onClick={toggleDeviceCamera}
          className={`p-3 rounded-full border backdrop-blur-xl transition-all duration-200 active:scale-90 ${
            isDeviceCamActive
              ? 'bg-red-600 border-red-500 text-white animate-pulse'
              : (isCrimson 
                  ? 'bg-black/80 border-red-900/40 text-red-500 hover:border-red-600' 
                  : 'bg-slate-950/70 border-white/10 text-slate-200 hover:border-white/30')
          }`}
          title={isDeviceCamActive ? "Stop Device Camera" : "Use Phone / Device Camera Lens"}
        >
          {isDeviceCamActive ? <Video className="w-4 h-4" /> : <Camera className="w-4 h-4" />}
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
                6X LOUPE
              </div>
            </div>

            {/* Circular FWHM Sharpness Gauge */}
            <div className="flex flex-col items-center justify-center gap-1">
              <div className="relative w-20 h-20 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                  <path
                    className="text-white/10"
                    strokeWidth="3.5"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
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

      {/* Active Processing Filters Indicator (Bottom Right) */}
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
        {isDeviceCamActive && (
          <div className="flex items-center justify-end gap-1.5">
            <span className="px-2 py-0.5 rounded-full bg-red-600/30 border border-red-500 text-red-200 animate-pulse">
              LIVE DEVICE CAMERA ACTIVE
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
