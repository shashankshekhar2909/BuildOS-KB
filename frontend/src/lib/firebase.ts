"use client";
import { initializeApp, getApps } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from "firebase/auth";
import firebaseConfig from "../../firebase-config.json";

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
export const auth = getAuth(app);

const provider = new GoogleAuthProvider();

export async function loginWithGoogle(): Promise<string> {
  const result = await signInWithPopup(auth, provider);
  return result.user.getIdToken();
}

export async function logoutFirebase(): Promise<void> {
  await signOut(auth);
}

export async function getCurrentFirebaseToken(): Promise<string | null> {
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken();
}
