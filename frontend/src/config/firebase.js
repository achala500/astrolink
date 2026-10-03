/**
 * Firebase Client Configuration & Authentication Setup for AstroLink.
 * 
 * Supports:
 * - Google OAuth Sign-In
 * - Email & Password Sign-In / Registration
 * - Offline-first Anonymous Guest Mode (for remote dark-sky field sessions)
 * - Cloud observing log synchronization
 */

import { initializeApp, getApps } from 'firebase/app';
import { 
  getAuth, 
  signInWithPopup, 
  GoogleAuthProvider, 
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInAnonymously,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';

// Default configuration with fallback for zero-setup local field station
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyDummyKeyForOfflineFieldStationAstroLink",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "astrolink-field.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "astrolink-field",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "astrolink-field.appspot.com",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "1029384756",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:1029384756:web:abcdef123456"
};

// Initialize Firebase app singleton
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

export {
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInAnonymously,
  signOut,
  onAuthStateChanged
};
