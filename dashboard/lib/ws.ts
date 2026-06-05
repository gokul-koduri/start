const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type SignalEvent = {
  id: number;
  signal_type: string;
  title: string;
  body_text: string;
  source_name: string;
  collected_at: string;
  composite_score: number;
};

export function connectSSE(
  onSignal: (signal: SignalEvent) => void,
  onError?: () => void
): EventSource | null {
  const url = `${API_BASE}/ws/stats`;
  // Fallback: use polling if SSE not available
  if (typeof EventSource === "undefined") {
    if (onError) onError();
    return null;
  }

  const es = new EventSource(url);
  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onSignal(data);
    } catch {
      // ignore parse errors
    }
  };
  es.onerror = () => {
    if (onError) onError();
  };

  return es;
}

export function getWebSocketURL(): string {
  return API_BASE.replace(/^http/, "ws") + "/ws/live";
}
