/**
 * AI Analyst Chat Widget
 * Add to site/index.html to enable natural language queries from the dashboard.
 *
 * Usage:
 *   <script src="chat-widget.js"></script>
 *
 * Requirements: API server running at http://localhost:8000
 */
(function () {
  "use strict";

  // ── Configuration ──
  const API_BASE = window.__API_BASE__ || "http://localhost:8000";

  // ── Styles ──
  const styles = document.createElement("style");
  styles.textContent = `
    .chat-widget {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 10000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .chat-toggle {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0d6efd, #0f3460);
      border: none;
      color: white;
      font-size: 24px;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .chat-toggle:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 24px rgba(0,0,0,0.4);
    }
    .chat-panel {
      display: none;
      position: absolute;
      bottom: 72px;
      right: 0;
      width: 420px;
      max-height: 560px;
      background: var(--bg, #fff);
      border: 1px solid var(--border, #dee2e6);
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.2);
      flex-direction: column;
      overflow: hidden;
    }
    .chat-panel.open {
      display: flex;
    }
    [data-theme="dark"] .chat-panel {
      background: #1a1a2e;
      border-color: #2a2a4a;
    }
    .chat-header {
      padding: 16px 20px;
      background: linear-gradient(135deg, #0d6efd, #0f3460);
      color: white;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .chat-header h3 {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
    }
    .chat-header span {
      font-size: 11px;
      opacity: 0.8;
    }
    .chat-close {
      background: none;
      border: none;
      color: white;
      font-size: 20px;
      cursor: pointer;
      opacity: 0.8;
      padding: 0 4px;
    }
    .chat-close:hover { opacity: 1; }
    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 380px;
    }
    .chat-msg {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.5;
      word-wrap: break-word;
    }
    .chat-msg.user {
      align-self: flex-end;
      background: #0d6efd;
      color: white;
      border-bottom-right-radius: 4px;
    }
    .chat-msg.bot {
      align-self: flex-start;
      background: var(--bg-secondary, #f0f0f0);
      color: var(--text, #212529);
      border-bottom-left-radius: 4px;
    }
    [data-theme="dark"] .chat-msg.bot {
      background: #16213e;
      color: #e8e8e8;
    }
    .chat-msg.bot pre {
      background: rgba(0,0,0,0.1);
      padding: 8px;
      border-radius: 6px;
      overflow-x: auto;
      font-size: 12px;
      margin: 6px 0;
    }
    .chat-msg.error {
      background: #dc3545;
      color: white;
    }
    .chat-msg.typing {
      opacity: 0.6;
      font-style: italic;
    }
    .chat-input-area {
      display: flex;
      padding: 12px 16px;
      border-top: 1px solid var(--border, #dee2e6);
      gap: 8px;
    }
    .chat-input-area input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--border, #dee2e6);
      border-radius: 20px;
      font-size: 13px;
      outline: none;
      background: var(--bg, #fff);
      color: var(--text, #212529);
    }
    .chat-input-area input:focus {
      border-color: #0d6efd;
    }
    .chat-input-area button {
      padding: 10px 18px;
      background: #0d6efd;
      color: white;
      border: none;
      border-radius: 20px;
      font-size: 13px;
      cursor: pointer;
      font-weight: 600;
    }
    .chat-input-area button:hover { background: #0b5ed7; }
    .chat-input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
    .chat-suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 0 16px 12px;
    }
    .chat-suggestions button {
      padding: 5px 10px;
      font-size: 11px;
      border: 1px solid var(--border, #dee2e6);
      border-radius: 12px;
      background: var(--bg-secondary, #f0f0f0);
      color: var(--text-secondary, #6c757d);
      cursor: pointer;
    }
    .chat-suggestions button:hover {
      background: var(--accent-light, #e7f1ff);
      color: #0d6efd;
      border-color: #0d6efd;
    }
    @media (max-width: 480px) {
      .chat-panel {
        width: calc(100vw - 32px);
        right: -8px;
      }
    }
  `;
  document.head.appendChild(styles);

  // ── DOM ──
  const widget = document.createElement("div");
  widget.className = "chat-widget";
  widget.innerHTML = `
    <div class="chat-panel" id="chatPanel">
      <div class="chat-header">
        <div>
          <h3>🤖 AI Analyst</h3>
          <span>Ask about startup failures, trends & opportunities</span>
        </div>
        <button class="chat-close" id="chatClose">&times;</button>
      </div>
      <div class="chat-messages" id="chatMessages">
        <div class="chat-msg bot">
          👋 Hi! I can answer questions about startup failures, survival rates, revival opportunities, and more. What would you like to know?
        </div>
      </div>
      <div class="chat-suggestions" id="chatSuggestions">
        <button data-q="What are the top 10 failure reasons?">Top failures</button>
        <button data-q="Which manufacturing sectors have the best revival potential?">Revival sectors</button>
        <button data-q="Compare startup survival rates by industry">Survival rates</button>
        <button data-q="What are the recent funding trends in EV startups?">EV trends</button>
        <button data-q="Which regions have the most startup failures?">By region</button>
      </div>
      <div class="chat-input-area">
        <input type="text" id="chatInput" placeholder="Ask a question..." autocomplete="off" />
        <button id="chatSend">Send</button>
      </div>
    </div>
    <button class="chat-toggle" id="chatToggle" title="AI Analyst">💬</button>
  `;
  document.body.appendChild(widget);

  // ── Elements ──
  const panel = document.getElementById("chatPanel");
  const toggleBtn = document.getElementById("chatToggle");
  const closeBtn = document.getElementById("chatClose");
  const messages = document.getElementById("chatMessages");
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSend");
  const suggestions = document.getElementById("chatSuggestions");

  // ── State ──
  let isLoading = false;

  // ── Toggle ──
  toggleBtn.addEventListener("click", () => {
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) input.focus();
  });
  closeBtn.addEventListener("click", () => panel.classList.remove("open"));

  // ── Suggestions ──
  suggestions.addEventListener("click", (e) => {
    if (e.target.dataset.q) {
      input.value = e.target.dataset.q;
      sendMessage();
    }
  });

  // ── Send ──
  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  function addMessage(text, type = "bot") {
    const msg = document.createElement("div");
    msg.className = `chat-msg ${type}`;
    msg.innerHTML = text;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
    return msg;
  }

  async function sendMessage() {
    const query = input.value.trim();
    if (!query || isLoading) return;

    // Show user message
    addMessage(query, "user");
    input.value = "";
    isLoading = true;
    sendBtn.disabled = true;

    // Show typing indicator
    const typing = addMessage("Analyzing your question...", "bot typing");

    try {
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      typing.remove();

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        addMessage(
          `⚠️ Error: ${err.detail || resp.statusText}. Make sure the API server is running at ${API_BASE}`,
          "error"
        );
        return;
      }

      const data = await resp.json();

      // Format answer with markdown-like rendering
      let answer = data.answer || "No answer generated.";
      answer = answer
        .replace(/```sql\n([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");

      addMessage(answer, "bot");

      // Show metadata
      if (data.intent || data.rows) {
        const meta = [];
        if (data.intent) meta.push(`Intent: ${data.intent}`);
        if (data.rows !== undefined) meta.push(`${data.rows} rows`);
        addMessage(`<small style="opacity:0.6">${meta.join(" · ")}</small>`, "bot");
      }
    } catch (err) {
      typing.remove();
      addMessage(
        `⚠️ Cannot reach API server at ${API_BASE}. Start it with: <code>python api_server.py</code>`,
        "error"
      );
    } finally {
      isLoading = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }
})();
