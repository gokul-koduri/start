"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  fetchAPI,
  formatScore,
  getScoreColor,
  getScoreBg,
  getSourceColor,
} from "@/lib/api";
import { Search as SearchIcon, Sparkles, FileText, Zap } from "lucide-react";

interface SearchResult {
  entity_name?: string;
  title?: string;
  score?: number;
  source?: string;
  signal_type?: string;
  snippet?: string;
  highlights?: string[];
  id?: number;
  composite_score?: number;
}

type SearchMode = "semantic" | "fulltext" | "hybrid";

export default function SearchPage() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const performSearch = useCallback(
    async (q: string, m: SearchMode) => {
      if (!q.trim()) return;
      setLoading(true);
      setSearched(true);
      try {
        const data = await fetchAPI<{ results: SearchResult[] }>(
          `/api/search?q=${encodeURIComponent(q)}&mode=${m}&limit=50`
        );
        setResults(data.results || []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Auto-search on initial query
  useEffect(() => {
    if (initialQuery) {
      performSearch(initialQuery, mode);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-search on mode change if query exists
  useEffect(() => {
    if (searched && query) {
      performSearch(query, mode);
    }
  }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="max-w-3xl mx-auto">
      {/* Search Input (centered, prominent) */}
      <div className="py-8">
        <div className="relative max-w-2xl mx-auto">
          <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") performSearch(query, mode);
            }}
            placeholder="Search companies, technologies, signals..."
            autoFocus
            className="w-full bg-surface-card border border-zinc-800 rounded-xl pl-12 pr-4 py-3.5 text-sm text-zinc-200 placeholder-zinc-600 outline-none focus:border-accent-blue/50 focus:ring-1 focus:ring-accent-blue/20 transition-all"
          />
          {query && (
            <button
              onClick={() => {
                setQuery("");
                setResults([]);
                setSearched(false);
              }}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] text-zinc-600 hover:text-zinc-400 transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        {/* Mode Tabs */}
        <div className="flex items-center justify-center gap-1 mt-4">
          {(
            [
              {
                key: "hybrid",
                label: "Hybrid",
                icon: Zap,
                desc: "Best results",
              },
              {
                key: "semantic",
                label: "Semantic",
                icon: Sparkles,
                desc: "Meaning-based",
              },
              {
                key: "fulltext",
                label: "Full-Text",
                icon: FileText,
                desc: "Keyword match",
              },
            ] as const
          ).map((m) => (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                mode === m.key
                  ? "bg-accent-blue/15 text-accent-blue border border-accent-blue/20"
                  : "text-zinc-500 hover:text-zinc-300 border border-transparent"
              }`}
            >
              <m.icon className="w-3 h-3" />
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Results */}
      {!loading && searched && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-zinc-600 font-mono">
            {results.length} results for &ldquo;{query}&rdquo;
          </p>
          {results.map((result, i) => {
            // Determine if it's an opportunity (has composite_score) or a signal
            const isOpportunity = result.composite_score !== undefined;
            const score = isOpportunity
              ? result.composite_score!
              : result.score || 0;
            const title = result.entity_name || result.title || "Unknown";
            const snippet = result.snippet || result.highlights?.join(" ") || "";

            return (
              <div
                key={i}
                className={`bg-surface-card border border-zinc-800 rounded-lg p-4 card-hover ${
                  !isOpportunity ? "cursor-default" : ""
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Score or Source Badge */}
                  {isOpportunity ? (
                    <div
                      className={`flex items-center justify-center w-10 h-10 rounded-lg border shrink-0 text-sm font-bold font-mono ${getScoreBg(
                        score
                      )} ${getScoreColor(score)}`}
                    >
                      {formatScore(score)}
                    </div>
                  ) : (
                    <div
                      className={`flex items-center justify-center w-10 h-10 rounded-lg border shrink-0 text-[10px] font-mono font-medium px-1 ${getSourceColor(
                        result.source || ""
                      )}`}
                    >
                      {(result.source || "SIG").slice(0, 4).toUpperCase()}
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    {isOpportunity ? (
                      <Link
                        href={`/opportunities/${result.id}`}
                        className="text-sm font-medium text-zinc-200 hover:text-accent-blue transition-colors"
                      >
                        {title}
                      </Link>
                    ) : (
                      <p className="text-sm font-medium text-zinc-200">
                        {title}
                      </p>
                    )}

                    {result.signal_type && (
                      <span className="text-[10px] text-zinc-600 font-mono ml-2">
                        {result.signal_type}
                      </span>
                    )}

                    {snippet && (
                      <p className="text-xs text-zinc-500 mt-1.5 line-clamp-2">
                        {snippet}
                      </p>
                    )}
                  </div>

                  {/* Relevance */}
                  {!isOpportunity && result.score !== undefined && (
                    <span className="text-[10px] text-zinc-600 font-mono shrink-0">
                      {(result.score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty States */}
      {!loading && searched && results.length === 0 && (
        <div className="text-center py-20">
          <p className="text-zinc-500 text-sm">
            No results found for &ldquo;{query}&rdquo;
          </p>
          <p className="text-zinc-700 text-xs mt-1">
            Try switching to Full-Text mode or adjusting your query.
          </p>
        </div>
      )}

      {!loading && !searched && (
        <div className="text-center py-16">
          <SearchIcon className="w-8 h-8 text-zinc-800 mx-auto mb-3" />
          <p className="text-zinc-600 text-sm">
            Enter a query to search across companies, signals, and technologies
          </p>
          <p className="text-zinc-700 text-xs mt-1">
            Hybrid mode combines semantic understanding with keyword matching
          </p>
        </div>
      )}
    </div>
  );
}
