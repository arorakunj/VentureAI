import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Loader2, ArrowRight, Check, CircleAlert } from "lucide-react";
import { AGENTS, type AgentConfig } from "@/config/agents";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  startEvaluation,
  openPipeline,
  ApiError,
  type StartupProfile,
  type MarketAnalysis,
  type FounderAnalysis,
  type FinancialAnalysis,
  type BearCase,
  type InvestmentMemo,
} from "@/lib/api";
import {
  ProfileCard,
  MarketCard,
  FounderCard,
  FinancialCard,
  BearCard,
  MemoCard,
} from "@/components/AgentOutputs";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type PipelineOutputs = {
  startup_profile?: StartupProfile;
  market_analysis?: MarketAnalysis;
  founder_analysis?: FounderAnalysis;
  financial_analysis?: FinancialAnalysis;
  bear_case?: BearCase;
  investment_memo?: InvestmentMemo;
};

type PipelineState =
  | { phase: "idle" }
  | { phase: "running"; sessionId: string; outputs: PipelineOutputs }
  | { phase: "done"; sessionId: string; outputs: PipelineOutputs }
  | { phase: "error"; message: string; outputs: PipelineOutputs };

type RunStatus = "queued" | "running" | "done";

const AGENT_OUTPUT_KEYS: Record<string, keyof PipelineOutputs> = {
  sourcing: "startup_profile",
  market: "market_analysis",
  founder: "founder_analysis",
  financial: "financial_analysis",
  bear: "bear_case",
  memo: "investment_memo",
};

function deriveRunStatuses(
  phase: PipelineState["phase"],
  outputs: PipelineOutputs,
): Record<string, RunStatus> {
  if (phase === "idle") return {};

  const has = (k: keyof PipelineOutputs) => outputs[k] !== undefined;
  const sourcingDone = has("startup_profile");
  const marketDone = has("market_analysis");
  const founderDone = has("founder_analysis");
  const financialDone = has("financial_analysis");
  const bearDone = has("bear_case");
  const memoDone = has("investment_memo");
  const diligenceDone = marketDone && founderDone && financialDone;

  return {
    sourcing: sourcingDone ? "done" : "running",
    market: marketDone ? "done" : sourcingDone ? "running" : "queued",
    founder: founderDone ? "done" : sourcingDone ? "running" : "queued",
    financial: financialDone ? "done" : sourcingDone ? "running" : "queued",
    bear: bearDone ? "done" : diligenceDone ? "running" : "queued",
    memo: memoDone ? "done" : bearDone ? "running" : "queued",
  };
}

/* ------------------------------------------------------------------ */
/* AppWorkspace                                                        */
/* ------------------------------------------------------------------ */

export function AppWorkspace() {
  const [activeId, setActiveId] = useState<string>(AGENTS[0].id);
  const [input, setInput] = useState("");
  const [pipeline, setPipeline] = useState<PipelineState>({ phase: "idle" });
  const wsRef = useRef<{ close(): void } | null>(null);
  const reduce = useReducedMotion();

  useEffect(() => () => { wsRef.current?.close(); }, []);

  const active = AGENTS.find((a) => a.id === activeId)!;
  const isRunning = pipeline.phase === "running";
  const outputs: PipelineOutputs =
    pipeline.phase !== "idle" ? pipeline.outputs : {};
  const runStatuses = deriveRunStatuses(pipeline.phase, outputs);

  const submit = async () => {
    if (!input.trim() || isRunning) return;
    setPipeline({ phase: "running", sessionId: "", outputs: {} });
    setActiveId("sourcing");

    try {
      const { session_id } = await startEvaluation(input.trim());
      setPipeline({ phase: "running", sessionId: session_id, outputs: {} });

      wsRef.current?.close();
      wsRef.current = openPipeline(session_id, {
        onMessage: (msg) => {
          setPipeline((prev) => {
            if (prev.phase !== "running") return prev;
            const newOutputs = {
              ...prev.outputs,
              [msg.type]: msg.data,
            } as PipelineOutputs;
            const isDone = newOutputs.investment_memo !== undefined;
            return isDone
              ? { phase: "done", sessionId: prev.sessionId, outputs: newOutputs }
              : { ...prev, outputs: newOutputs };
          });
        },
        onError: () => {
          setPipeline((prev) =>
            prev.phase === "running"
              ? {
                  phase: "error",
                  message: "Connection lost mid-run. Partial results shown below.",
                  outputs: prev.outputs,
                }
              : prev,
          );
        },
        onClose: () => {
          setPipeline((prev) =>
            prev.phase === "running"
              ? { phase: "done", sessionId: prev.sessionId, outputs: prev.outputs }
              : prev,
          );
        },
      });
    } catch (err) {
      const message =
        err instanceof ApiError && (err.status === 0 || err.status >= 500)
          ? "The backend isn't responding. Start the FastAPI server on :8000 and try again."
          : err instanceof Error
            ? err.message
            : "Something went wrong.";
      setPipeline({ phase: "error", message, outputs: {} });
    }
  };

  return (
    <div className="container py-12 sm:py-16">
      <header className="mb-8 flex flex-col gap-4 border-b border-ink/10 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="label-mono mb-3">Workspace — Deal Console</p>
          <h1 className="font-display text-4xl font-bold tracking-tightest sm:text-5xl">
            Run the committee
          </h1>
        </div>
        <p className="max-w-sm font-sans text-sm leading-relaxed text-muted-foreground">
          Paste a company signal and run. All six agents stream results live as
          they finish.
        </p>
      </header>

      {/* Intake */}
      <div className="mb-px border border-ink/10 bg-paper p-6">
        <p className="label-mono mb-4 text-ink/70">Company signal</p>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste a company name, website, or a few sentences describing the startup…"
            disabled={isRunning}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit();
            }}
            className="min-h-[80px] flex-1"
          />
          <div className="flex shrink-0 flex-col gap-3">
            <Button
              onClick={submit}
              disabled={!input.trim() || isRunning}
              size="lg"
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
                  Running
                </>
              ) : (
                <>
                  Run committee
                  <ArrowRight className="h-4 w-4" strokeWidth={1.75} />
                </>
              )}
            </Button>
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground sm:inline">
              ⌘ + Enter
            </span>
          </div>
        </div>
        {pipeline.phase === "error" &&
          Object.keys(pipeline.outputs).length === 0 && (
            <div className="mt-4 flex items-start gap-2 text-muted-foreground">
              <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.75} />
              <p className="font-sans text-sm">{pipeline.message}</p>
            </div>
          )}
      </div>

      {/* Two-pane grid */}
      <div className="grid gap-px bg-ink/10 lg:grid-cols-[300px_1fr]">
        <AgentIndex
          active={activeId}
          onSelect={setActiveId}
          runStatuses={runStatuses}
          pipelinePhase={pipeline.phase}
        />
        <section className="bg-paper p-6 sm:p-10">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeId}
              initial={{ opacity: 0, y: reduce ? 0 : 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            >
              <AgentPanel
                agent={active}
                outputs={outputs}
                pipelinePhase={pipeline.phase}
                runStatus={runStatuses[active.id]}
                errorMessage={
                  pipeline.phase === "error" ? pipeline.message : undefined
                }
              />
            </motion.div>
          </AnimatePresence>
        </section>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* AgentIndex                                                          */
/* ------------------------------------------------------------------ */

function AgentIndex({
  active,
  onSelect,
  runStatuses,
  pipelinePhase,
}: {
  active: string;
  onSelect: (id: string) => void;
  runStatuses: Record<string, RunStatus>;
  pipelinePhase: PipelineState["phase"];
}) {
  return (
    <nav className="bg-paper" aria-label="Agent index">
      <p className="label-mono px-6 pb-4 pt-6">Index</p>
      <ul>
        {AGENTS.map((agent) => {
          const isActive = agent.id === active;
          const runStatus = runStatuses[agent.id];
          return (
            <li key={agent.id}>
              <button
                onClick={() => onSelect(agent.id)}
                aria-current={isActive ? "true" : undefined}
                className={cn(
                  "group flex w-full items-center justify-between gap-3 border-t border-ink/10 px-6 py-5 text-left transition-colors duration-300",
                  isActive ? "bg-ink text-paper" : "hover:bg-ink/[0.04]",
                )}
              >
                <span className="flex flex-col gap-1">
                  <span
                    className={cn(
                      "font-mono text-[10px] tracking-[0.2em]",
                      isActive ? "text-paper/60" : "text-muted-foreground",
                    )}
                  >
                    {agent.code}
                  </span>
                  <span className="font-display text-lg font-bold leading-none tracking-tight">
                    {agent.name}
                  </span>
                </span>
                {isActive ? (
                  <ArrowRight className="h-4 w-4 shrink-0" strokeWidth={1.75} />
                ) : pipelinePhase !== "idle" && runStatus ? (
                  <RunStatusGlyph status={runStatus} />
                ) : (
                  <StatusGlyph available className="shrink-0" />
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/* ------------------------------------------------------------------ */
/* Run-status glyph — ephemeral overlay during an active run          */
/* ------------------------------------------------------------------ */

function RunStatusGlyph({ status }: { status: RunStatus }) {
  if (status === "done") {
    return (
      <span className="inline-flex shrink-0 items-center gap-2">
        <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
        <span className="font-mono text-[10px] uppercase tracking-ledger opacity-70">
          Done
        </span>
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="inline-flex shrink-0 items-center gap-2">
        <Loader2 className="h-3 w-3 animate-spin" strokeWidth={2} />
        <span className="font-mono text-[10px] uppercase tracking-ledger opacity-70">
          Running
        </span>
      </span>
    );
  }
  return (
    <span className="inline-flex shrink-0 items-center gap-2">
      <span aria-hidden className="h-2 w-2 border border-current/40 bg-transparent" />
      <span className="font-mono text-[10px] uppercase tracking-ledger opacity-70">
        Queued
      </span>
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* AgentPanel — header + output area for the selected agent           */
/* ------------------------------------------------------------------ */

function AgentPanel({
  agent,
  outputs,
  pipelinePhase,
  runStatus,
  errorMessage,
}: {
  agent: AgentConfig;
  outputs: PipelineOutputs;
  pipelinePhase: PipelineState["phase"];
  runStatus?: RunStatus;
  errorMessage?: string;
}) {
  return (
    <div>
      <div className="flex flex-col gap-4 border-b border-ink/10 pb-8 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-5">
          <agent.icon className="mt-1 h-8 w-8 shrink-0" strokeWidth={1.3} />
          <div>
            <p className="font-mono text-xs tracking-[0.2em] text-muted-foreground">
              {agent.code} · {agent.role}
            </p>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tightest">
              {agent.name}
            </h2>
            <p className="mt-3 max-w-xl font-sans text-sm leading-relaxed text-muted-foreground">
              {agent.summary}
            </p>
          </div>
        </div>
        {/* Live badge at rest; run-status glyph during/after a run */}
        {pipelinePhase !== "idle" && runStatus ? (
          <RunStatusGlyph status={runStatus} />
        ) : (
          <StatusGlyph available />
        )}
      </div>

      <div className="pt-8">
        <AgentOutput
          agent={agent}
          outputs={outputs}
          pipelinePhase={pipelinePhase}
          runStatus={runStatus}
          errorMessage={errorMessage}
        />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* AgentOutput — dispatches to the right card                         */
/* ------------------------------------------------------------------ */

function AgentOutput({
  agent,
  outputs,
  pipelinePhase,
  runStatus,
  errorMessage,
}: {
  agent: AgentConfig;
  outputs: PipelineOutputs;
  pipelinePhase: PipelineState["phase"];
  runStatus?: RunStatus;
  errorMessage?: string;
}) {
  const outputKey = AGENT_OUTPUT_KEYS[agent.id];
  const output = outputs[outputKey];

  if (pipelinePhase === "idle") {
    return (
      <EmptyState
        headline="Ready"
        body={`Enter a company signal above and run the committee to generate ${agent.name} analysis.`}
        dashed
      />
    );
  }

  if (pipelinePhase === "error" && !output) {
    return (
      <EmptyState
        headline="Run failed"
        body={errorMessage ?? "Something went wrong."}
        icon={<CircleAlert className="h-4 w-4" strokeWidth={1.75} />}
      />
    );
  }

  if (!output) {
    if (runStatus === "running") {
      return <RunningState />;
    }
    return (
      <EmptyState
        headline="Queued"
        body="Waiting for upstream agents to complete."
        dashed
      />
    );
  }

  switch (agent.id) {
    case "sourcing":
      return <ProfileCard profile={output as StartupProfile} />;
    case "market":
      return <MarketCard analysis={output as MarketAnalysis} />;
    case "founder":
      return <FounderCard analysis={output as FounderAnalysis} />;
    case "financial":
      return <FinancialCard analysis={output as FinancialAnalysis} />;
    case "bear":
      return <BearCard bear={output as BearCase} />;
    case "memo":
      return <MemoCard memo={output as InvestmentMemo} />;
    default:
      return null;
  }
}

/* ------------------------------------------------------------------ */
/* State placeholders                                                  */
/* ------------------------------------------------------------------ */

function EmptyState({
  headline,
  body,
  dashed = false,
  icon,
}: {
  headline: string;
  body: string;
  dashed?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex min-h-[220px] flex-col items-start justify-center gap-3 p-8",
        dashed ? "border border-dashed border-ink/15" : "border border-ink/20",
      )}
    >
      {icon && (
        <div className="flex items-center gap-2 text-muted-foreground">{icon}</div>
      )}
      <p className="font-display text-xl tracking-tight">{headline}</p>
      <p className="font-sans text-sm leading-relaxed text-muted-foreground">{body}</p>
    </div>
  );
}

function RunningState() {
  return (
    <div className="flex min-h-[220px] flex-col gap-4 border border-ink/15 p-8">
      <div className="flex items-center gap-3">
        <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
        <span className="label-mono text-ink/70">Reasoning</span>
      </div>
      <div className="flex flex-col gap-3 pt-2">
        {[100, 82, 64].map((w) => (
          <div
            key={w}
            className="h-3 animate-pulse-dot bg-ink/10"
            style={{ width: `${w}%` }}
          />
        ))}
      </div>
    </div>
  );
}
