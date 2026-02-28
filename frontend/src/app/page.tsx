"use client";

import React, { useState, useEffect } from "react";
import {
  StreamVideo,
  StreamVideoClient,
  StreamCall,
  SpeakerLayout,
  CallControls,
  useCallStateHooks,
} from "@stream-io/video-react-sdk";

// ──────────────────────────────────────────────
// Configuration
// ──────────────────────────────────────────────
const API_KEY = process.env.NEXT_PUBLIC_STREAM_API_KEY!;
const USER_ID = process.env.NEXT_PUBLIC_STREAM_USER_ID ?? "demo-user";
const CALL_ID = process.env.NEXT_PUBLIC_STREAM_CALL_ID ?? "echosight-demo";

/**
 * Fetch a fresh token from our server-side API route.
 * The SDK calls this automatically whenever the current token expires.
 */
async function tokenProvider(): Promise<string> {
  const res = await fetch(`/api/token?user_id=${USER_ID}`);
  if (!res.ok) throw new Error(`Token fetch failed: ${res.statusText}`);
  const { token } = await res.json();
  return token;
}

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────
type Priority = "urgent" | "high" | "normal";

interface SocialCue {
  text: string;
  time: string;
  priority: Priority;
}

// ──────────────────────────────────────────────
// Page
// ──────────────────────────────────────────────
export default function EchoSightPage() {
  const [client, setClient] = useState<StreamVideoClient | undefined>();
  const [call, setCall] = useState<ReturnType<StreamVideoClient["call"]> | undefined>();
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    // Local vars captured by the cleanup closure — no refs needed.
    let videoClient: StreamVideoClient | undefined;
    let videoCall: ReturnType<StreamVideoClient["call"]> | undefined;

    const init = async () => {
      const user = { id: USER_ID, name: "Demo User" };

      // Explicitly await connectUser so auth is fully complete before join().
      // Passing tokenProvider (not a raw token) means the SDK will auto-refresh
      // whenever the token expires — no more manual token rotation.
      videoClient = new StreamVideoClient({ apiKey: API_KEY });
      await videoClient.connectUser(user, tokenProvider);

      videoCall = videoClient.call("default", CALL_ID);
      await videoCall.join({ create: true });

      setClient(videoClient);
      setCall(videoCall);
    };

    init().catch((err) => {
      console.error("EchoSight init failed:", err);
      setError(err?.message ?? String(err));
    });

    return () => {
      videoCall?.leave();
      videoClient?.disconnectUser();
    };
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-white">
        <div className="text-center max-w-md px-4">
          <div className="text-4xl mb-4">⚠️</div>
          <p className="text-lg font-semibold mb-2">Connection failed</p>
          <p className="text-sm text-gray-400 font-mono break-all">{error}</p>
          <p className="text-xs text-gray-600 mt-4">
            Check that NEXT_PUBLIC_STREAM_API_KEY and NEXT_PUBLIC_STREAM_USER_TOKEN
            are set in .env.local and that the token has not expired.
          </p>
        </div>
      </div>
    );
  }

  if (!client || !call) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-white">
        <div className="text-center">
          <div className="animate-pulse text-4xl mb-4">👁</div>
          <p className="text-xl font-light">Connecting EchoSight...</p>
        </div>
      </div>
    );
  }

  return (
    <StreamVideo client={client}>
      <StreamCall call={call}>
        <EchoSightUI />
      </StreamCall>
    </StreamVideo>
  );
}

// ──────────────────────────────────────────────
// Main UI Component
// ──────────────────────────────────────────────
function EchoSightUI() {
  const { useParticipantCount } = useCallStateHooks();
  const participantCount = useParticipantCount();
  const [cueHistory, setCueHistory] = useState<SocialCue[]>([]);

  // EchoSight speaks via audio — cueHistory is populated when captions
  // are surfaced from the agent's text back-channel (wired in later).
  // For now it's ready to receive cues from a WebSocket or custom event.

  return (
    <div className="h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">👁</span>
          <h1 className="text-white text-lg font-semibold">EchoSight</h1>
          <span className="bg-green-500/20 text-green-400 text-xs px-2 py-0.5 rounded-full">
            LIVE
          </span>
        </div>
        <div className="text-gray-400 text-sm">
          {participantCount} participant{participantCount !== 1 ? "s" : ""}
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Video area */}
        <div className="flex-1 relative">
          <SpeakerLayout />

          {/* Social cue overlay — subtle caption above the call controls */}
          <div className="absolute bottom-24 left-0 right-0 flex justify-center px-4 pointer-events-none">
            <div className="bg-black/70 backdrop-blur-sm rounded-lg px-4 py-2 max-w-md">
              <p className="text-white text-center text-sm font-medium">
                {cueHistory.length > 0
                  ? cueHistory[cueHistory.length - 1].text
                  : "EchoSight active — listening..."}
              </p>
            </div>
          </div>
        </div>

        {/* Social cue feed sidebar */}
        <aside className="w-80 bg-gray-900 border-l border-gray-800 flex flex-col">
          <div className="p-4 border-b border-gray-800">
            <h2 className="text-white font-medium">Social Cues</h2>
            <p className="text-gray-500 text-xs mt-1">
              Real-time updates from EchoSight
            </p>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {cueHistory.length === 0 ? (
              <p className="text-gray-600 text-sm text-center mt-8">
                Cues will appear here as EchoSight detects social signals...
              </p>
            ) : (
              [...cueHistory].reverse().map((cue, i) => (
                <div
                  key={i}
                  className={`rounded-lg p-3 text-sm ${
                    cue.priority === "urgent"
                      ? "bg-red-500/10 border border-red-500/30 text-red-300"
                      : cue.priority === "high"
                      ? "bg-yellow-500/10 border border-yellow-500/30 text-yellow-300"
                      : "bg-gray-800 text-gray-300"
                  }`}
                >
                  <p>{cue.text}</p>
                  <span className="text-xs text-gray-500 mt-1 block">
                    {cue.time}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* Quick voice commands */}
          <div className="p-4 border-t border-gray-800">
            <p className="text-gray-500 text-xs mb-2">Say aloud to EchoSight:</p>
            <div className="flex flex-wrap gap-1">
              {[
                "What's happening?",
                "Who's talking?",
                "How many people?",
                "Go quiet",
              ].map((cmd) => (
                <span
                  key={cmd}
                  className="bg-gray-800 text-gray-400 text-xs px-2 py-1 rounded"
                >
                  &ldquo;{cmd}&rdquo;
                </span>
              ))}
            </div>
          </div>
        </aside>
      </div>

      {/* Call controls */}
      <div className="bg-gray-900 border-t border-gray-800 py-3">
        <CallControls />
      </div>
    </div>
  );
}
