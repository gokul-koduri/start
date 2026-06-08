"use client";

import { useState } from "react";
import { MessageSquare, X, Star, Send } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [comment, setComment] = useState("");
  const [entity, setEntity] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!entity.trim() || rating === 0) {
      setError("Entity name and rating are required");
      return;
    }
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v2/feedback/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_name: entity.trim(),
          rating,
          comment: comment.trim(),
        }),
      });
      if (!res.ok) throw new Error("Submit failed");
      setSubmitted(true);
      setTimeout(() => {
        setOpen(false);
        setSubmitted(false);
        setRating(0);
        setComment("");
        setEntity("");
      }, 1500);
    } catch {
      setError("Failed to submit — try again");
    }
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-accent-green/20 border border-accent-green/40
                   flex items-center justify-center hover:bg-accent-green/30 transition-colors shadow-lg"
        aria-label="Submit feedback"
      >
        {open ? (
          <X className="w-5 h-5 text-accent-green" />
        ) : (
          <MessageSquare className="w-5 h-5 text-accent-green" />
        )}
      </button>

      {/* Feedback panel */}
      {open && (
        <div className="fixed bottom-20 right-6 z-50 w-80 bg-surface-card border border-zinc-800 rounded-xl shadow-2xl p-4">
          {submitted ? (
            <div className="text-center py-6">
              <Star className="w-8 h-8 text-accent-green mx-auto mb-2" />
              <p className="text-zinc-200 font-medium">Thanks for your feedback!</p>
            </div>
          ) : (
            <>
              <h3 className="text-sm font-semibold text-zinc-200 mb-3">
                Rate a startup score
              </h3>

              {/* Entity name */}
              <input
                type="text"
                placeholder="Startup name"
                value={entity}
                onChange={(e) => setEntity(e.target.value)}
                className="w-full bg-surface-primary border border-zinc-800 rounded-lg px-3 py-2 text-sm
                           text-zinc-200 placeholder-zinc-600 outline-none focus:border-accent-green/50 mb-3"
              />

              {/* Star rating */}
              <div className="flex gap-1 mb-3">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => setRating(star)}
                    onMouseEnter={() => setHovered(star)}
                    onMouseLeave={() => setHovered(0)}
                    className="p-0.5"
                    aria-label={`${star} star${star > 1 ? "s" : ""}`}
                  >
                    <Star
                      className={`w-6 h-6 transition-colors ${
                        star <= (hovered || rating)
                          ? "text-yellow-400 fill-yellow-400"
                          : "text-zinc-600"
                      }`}
                    />
                  </button>
                ))}
              </div>

              {/* Comment */}
              <textarea
                placeholder="Any additional thoughts? (optional)"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={2}
                className="w-full bg-surface-primary border border-zinc-800 rounded-lg px-3 py-2 text-sm
                           text-zinc-200 placeholder-zinc-600 outline-none focus:border-accent-green/50 resize-none mb-3"
              />

              {error && (
                <p className="text-xs text-red-400 mb-2">{error}</p>
              )}

              {/* Submit */}
              <button
                onClick={handleSubmit}
                disabled={rating === 0 || !entity.trim()}
                className="w-full flex items-center justify-center gap-2 bg-accent-green/20 border border-accent-green/40
                           rounded-lg py-2 text-sm text-accent-green hover:bg-accent-green/30 transition-colors
                           disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
                Submit feedback
              </button>
            </>
          )}
        </div>
      )}
    </>
  );
}
