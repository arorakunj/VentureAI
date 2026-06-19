/**
 * Thin client for the VentureAI FastAPI backend.
 *
 * In dev, vite.config.ts proxies these paths to http://localhost:8000.
 * Override the base in production with VITE_API_URL.
 */

const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export interface StartupProfile {
  company_name: string;
  one_liner?: string | null;
  stage?: string | null;
  industry?: string | null;
  founders: string[];
  funding_history: Record<string, unknown>[];
  location?: string | null;
  website?: string | null;
  raw_description?: string | null;
  score: number;
  summary?: string | null;
}

export interface BandMessage {
  agent: string;
  type: string;
  data: Record<string, unknown>;
}

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    // Network-level failure — backend is down or unreachable.
    throw new ApiError("Backend unreachable", 0);
  }

  if (!res.ok) {
    throw new ApiError(`Request failed (${res.status})`, res.status);
  }
  return (await res.json()) as T;
}

/** Kick off a sourcing run. Returns a session id to poll against. */
export async function startEvaluation(input: string): Promise<{ session_id: string }> {
  return request("/evaluate", {
    method: "POST",
    body: JSON.stringify({ input }),
  });
}

/** Fetch the message log for a session. */
export async function getStatus(sessionId: string): Promise<{ messages: BandMessage[] }> {
  return request(`/status/${sessionId}`);
}

/**
 * Poll /status until a message of `type` arrives (or we time out).
 * The sourcing agent publishes a `startup_profile` message when it finishes.
 */
export async function pollForMessage(
  sessionId: string,
  type: string,
  { intervalMs = 1200, timeoutMs = 45000 }: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<BandMessage> {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const { messages } = await getStatus(sessionId);
    const hit = messages.find((m) => m.type === type);
    if (hit) return hit;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new ApiError("Timed out waiting for the agent to respond", 408);
}

/** Convenience: run sourcing end-to-end and return the resulting profile. */
export async function runSourcing(input: string): Promise<StartupProfile> {
  const { session_id } = await startEvaluation(input);
  const message = await pollForMessage(session_id, "startup_profile");
  return message.data as unknown as StartupProfile;
}

/* ------------------------------------------------------------------ */
/* Agent output types — mirror ventureai/backend/models.py            */
/* ------------------------------------------------------------------ */

export interface MarketAnalysis {
  tam?: string | null;
  market_growth?: string | null;
  timing_verdict?: string | null;
  competitors: string[];
  differentiation?: string | null;
  market_score: number;
  key_risks: string[];
  summary?: string | null;
}

export interface FounderInfo {
  name?: string;
  background?: string;
  domain_expertise?: string;
  red_flags?: string[];
}

export interface FounderAnalysis {
  founders: FounderInfo[];
  team_completeness?: string | null;
  prior_exits: boolean;
  founder_score: number;
  summary?: string | null;
}

export interface FinancialAnalysis {
  revenue_model?: string | null;
  unit_economics?: Record<string, string>;
  raise_amount?: string | null;
  burn_assessment?: string | null;
  path_to_profitability?: string | null;
  financial_score: number;
  red_flags: string[];
  summary?: string | null;
}

export interface BearCase {
  market_challenges: string[];
  founder_challenges: string[];
  financial_challenges: string[];
  failure_modes: string[];
  bear_case_score: number;
  summary?: string | null;
}

export interface InvestmentMemo {
  verdict: "PASS" | "INVEST" | "WATCH";
  confidence_score: number;
  executive_summary?: string | null;
  market_score: number;
  founder_score: number;
  financial_score: number;
  bear_case_score: number;
  overall_score: number;
  recommendation?: string | null;
  due_diligence_questions: string[];
  suggested_valuation_range?: string | null;
  summary?: string | null;
}

export interface PipelineHandle {
  close(): void;
}

/**
 * Open a WebSocket to /ws/{sessionId} and stream BandMessage events.
 * In dev, vite proxies /ws to ws://localhost:8000.
 * In prod, set VITE_API_URL to the backend base URL (http/https → ws/wss).
 */
export function openPipeline(
  sessionId: string,
  handlers: {
    onMessage: (msg: BandMessage) => void;
    onError?: (e: Event) => void;
    onClose?: () => void;
  },
): PipelineHandle {
  const apiUrl = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
  const wsUrl = apiUrl
    ? `${apiUrl.replace(/^http/, "ws")}/ws/${sessionId}`
    : `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/${sessionId}`;

  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data as string) as BandMessage;
      handlers.onMessage(msg);
    } catch {
      // ignore malformed frames
    }
  };
  ws.onerror = (e) => handlers.onError?.(e);
  ws.onclose = () => handlers.onClose?.();

  return { close: () => ws.close() };
}
