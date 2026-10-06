import React, { useState, useEffect } from 'react';
import { 
  User, 
  X, 
  LogOut, 
  Mail, 
  Lock, 
  Cloud
} from 'lucide-react';
import { 
  auth, 
  googleProvider, 
  signInWithPopup, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signInAnonymously, 
  signOut, 
  onAuthStateChanged 
} from '../config/firebase';
import { soundEngine } from '../utils/audio';

export default function AuthModal({ isOpen, onClose, isCrimson }) {
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });
    return () => unsubscribe();
  }, []);

  if (!isOpen) return null;

  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError(null);
    soundEngine.playClick();
    try {
      await signInWithPopup(auth, googleProvider);
      onClose();
    } catch (err) {
      console.warn("Google sign-in offline fallback:", err);
      try {
        await signInAnonymously(auth);
      } catch (guestErr) {
        console.warn("Guest sign-in offline fallback:", guestErr);
      }
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    setError(null);
    soundEngine.playClick();
    try {
      if (isRegistering) {
        await createUserWithEmailAndPassword(auth, email, password);
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      onClose();
    } catch (err) {
      setError(err.message?.replace('Firebase: ', '') || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAnonymousSignIn = async () => {
    setLoading(true);
    setError(null);
    soundEngine.playClick();
    try {
      await signInAnonymously(auth);
      onClose();
    } catch (err) {
      console.warn("Anonymous sign-in error:", err);
      setError('Could not start field guest session.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    soundEngine.playClick();
    await signOut(auth);
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Modal Card */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div 
          className={`pointer-events-auto w-full max-w-sm rounded-3xl border shadow-2xl p-6 transition-all duration-300 animate-scale-in ${
            isCrimson 
              ? 'bg-black border-red-900/60 text-red-200 shadow-red-950/40' 
              : 'bg-slate-950 border-white/15 text-slate-100 shadow-black/80'
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                isCrimson ? 'bg-red-950/80 text-red-400' : 'bg-white/10 text-emerald-400'
              }`}>
                <User className="w-4 h-4" />
              </div>
              <h2 className="text-base font-semibold tracking-tight">
                {user ? 'Observing Profile' : 'AstroLink Cloud Auth'}
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-white/10 opacity-70 hover:opacity-100 transition-all focus-visible:ring-2 focus-visible:ring-emerald-400 outline-none"
              aria-label="Close authentication modal"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {user ? (
            /* Logged In View */
            <div className="space-y-4">
              <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold font-mono text-sm">
                  {user.email ? user.email[0].toUpperCase() : 'G'}
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-semibold truncate text-white">
                    {user.email || 'Dark Sky Guest Observer'}
                  </p>
                  <p className="text-[10px] text-slate-400 flex items-center gap-1">
                    <Cloud className="w-3 h-3 text-emerald-400" />
                    <span>Cloud Sync Active (UID: {user.uid.substring(0, 6)}...)</span>
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleSignOut}
                className="w-full h-11 rounded-full flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase border border-red-500/40 text-red-400 hover:bg-red-950/30 transition-all active:scale-95"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          ) : (
            /* Auth Form View */
            <div className="space-y-3.5">
              {/* 100% Offline Field Mode Banner */}
              <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-200 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-300">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>Offline Field Station Active</span>
                  </div>
                  <span className="text-[10px] font-mono opacity-70">100% Local</span>
                </div>
                <p className="text-[11px] opacity-80 leading-relaxed">
                  Cameras connect directly via USB cable or local Wi-Fi. Zero account, cloud login, or internet required in the field.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    soundEngine.playClick();
                    onClose();
                  }}
                  className="w-full h-9 rounded-xl font-bold text-xs uppercase tracking-wider bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-all active:scale-95 shadow-md flex items-center justify-center gap-1.5"
                >
                  <span>Enter Field Station (Zero Cloud)</span>
                </button>
              </div>

              <div className="flex items-center gap-2 opacity-30 pt-1">
                <div className="flex-1 h-px bg-white" />
                <span className="text-[9px] uppercase font-mono">optional cloud backup</span>
                <div className="flex-1 h-px bg-white" />
              </div>

              {/* Google OAuth Button */}
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={loading}
                className="w-full h-10 rounded-full flex items-center justify-center gap-2 font-semibold text-xs tracking-wider uppercase bg-white text-black hover:bg-slate-200 transition-all active:scale-95 shadow-lg disabled:opacity-50"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                Continue with Google
              </button>

              <div className="flex items-center gap-2 opacity-40">
                <div className="flex-1 h-px bg-white" />
                <span className="text-[10px] uppercase font-mono">or email</span>
                <div className="flex-1 h-px bg-white" />
              </div>

              {/* Email / Password Form */}
              <form onSubmit={handleEmailAuth} className="space-y-2.5">
                <div className="relative">
                  <label htmlFor="auth-email" className="sr-only">
                    Astronomer Email
                  </label>
                  <Mail className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" aria-hidden="true" />
                  <input
                    id="auth-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Astronomer Email"
                    className="w-full h-10 pl-10 pr-3 rounded-xl text-xs bg-white/5 border border-white/10 text-white placeholder-slate-500 outline-none focus:border-white/30 focus-visible:ring-2 focus-visible:ring-emerald-400 transition-all"
                  />
                </div>
                <div className="relative">
                  <label htmlFor="auth-password" className="sr-only">
                    Password
                  </label>
                  <Lock className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" aria-hidden="true" />
                  <input
                    id="auth-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Password"
                    className="w-full h-10 pl-10 pr-3 rounded-xl text-xs bg-white/5 border border-white/10 text-white placeholder-slate-500 outline-none focus:border-white/30 focus-visible:ring-2 focus-visible:ring-emerald-400 transition-all"
                  />
                </div>

                {error && (
                  <p className="text-[11px] text-rose-400 font-mono text-center">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={loading || !email || !password}
                  className={`w-full h-10 rounded-full font-semibold text-xs tracking-wider uppercase transition-all active:scale-95 disabled:opacity-40 ${
                    isCrimson 
                      ? 'bg-red-600 text-black hover:bg-red-500' 
                      : 'bg-emerald-500 text-slate-950 hover:bg-emerald-400'
                  }`}
                >
                  {isRegistering ? 'Register Account' : 'Sign In'}
                </button>
              </form>

              {/* Mode switch */}
              <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                <button
                  type="button"
                  onClick={() => setIsRegistering(!isRegistering)}
                  className="hover:underline"
                >
                  {isRegistering ? 'Existing observer? Sign in' : 'New observer? Register'}
                </button>

                <button
                  type="button"
                  onClick={handleAnonymousSignIn}
                  className="text-amber-400 hover:underline font-mono"
                >
                  Offline Field Mode
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
