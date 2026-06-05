const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchAPI<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    // Return empty data if backend is unavailable (graceful degradation)
    return {} as T;
  }
  return res.json();
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function formatScore(score: number): string {
  return score.toFixed(1);
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "text-accent-green";
  if (score >= 60) return "text-accent-blue";
  if (score >= 40) return "text-accent-amber";
  return "text-accent-red";
}

export function getScoreBg(score: number): string {
  if (score >= 80) return "bg-green-500/10 border-green-500/20";
  if (score >= 60) return "bg-blue-500/10 border-blue-500/20";
  if (score >= 40) return "bg-amber-500/10 border-amber-500/20";
  return "bg-red-500/10 border-red-500/20";
}

export function getSourceColor(source: string): string {
  const colors: Record<string, string> = {
    github: "text-purple-400 bg-purple-500/10",
    reddit: "text-orange-400 bg-orange-500/10",
    hacker_news: "text-amber-400 bg-amber-500/10",
    sec_edgar: "text-blue-400 bg-blue-500/10",
    patent: "text-cyan-400 bg-cyan-500/10",
    news: "text-green-400 bg-green-500/10",
    job_postings: "text-pink-400 bg-pink-500/10",
    funding: "text-emerald-400 bg-emerald-500/10",
  };
  return colors[source?.toLowerCase()] || "text-zinc-400 bg-zinc-500/10";
}
