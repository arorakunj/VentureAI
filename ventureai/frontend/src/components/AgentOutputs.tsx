import { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Globe, Layers, MapPin, TrendingUp, DollarSign, Clock, Target, Loader2, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  StartupProfile,
  MarketAnalysis,
  FounderAnalysis,
  FinancialAnalysis,
  BearCase,
  InvestmentMemo,
  FeedEvent,
} from "@/lib/api";

const CARD_ANIM = { initial: { opacity: 1, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const } };

/* ------------------------------------------------------------------ */
/* ProfileCard                                                         */
/* ------------------------------------------------------------------ */

export function ProfileCard({ profile }: { profile: StartupProfile }) {
  const isInvalid = profile.company_name.toUpperCase().replace(/\s/g, "_") === "INVALID_INPUT";
  const displayName = isInvalid ? "Invalid Input" : profile.company_name;
  const meta = [
    { icon: Layers, label: "Stage", value: profile.stage },
    { icon: Globe, label: "Industry", value: profile.industry },
    { icon: MapPin, label: "Location", value: profile.location },
  ];
  return (
    <motion.article {...CARD_ANIM} className="border border-ink/15">
      <div className="border-b border-ink/15 p-5">
        <h3 className="font-display text-2xl font-bold leading-tight tracking-tight">{displayName}</h3>
        {!isInvalid && profile.one_liner && (
          <p className="mt-1 font-sans text-sm leading-relaxed text-muted-foreground">{profile.one_liner}</p>
        )}
      </div>
      <ScoreHeader score={profile.score} label="Conviction" />
      <MetaGrid items={meta} />
      {(profile.founders ?? []).length > 0 && (
        <div className="border-b border-ink/15 p-5">
          <p className="label-mono mb-3 text-ink/60">Founders</p>
          <div className="flex flex-wrap gap-2">
            {(profile.founders ?? []).map((f, i) => <Tag key={i}>{String(f)}</Tag>)}
          </div>
        </div>
      )}
      {profile.summary && <SummaryBlock text={profile.summary} />}
    </motion.article>
  );
}

/* ------------------------------------------------------------------ */
/* MarketCard                                                          */
/* ------------------------------------------------------------------ */

export function MarketCard({ analysis }: { analysis: MarketAnalysis }) {
  const meta = [
    { icon: Globe, label: "TAM", value: analysis.tam },
    { icon: TrendingUp, label: "Growth", value: analysis.market_growth },
    { icon: Clock, label: "Timing", value: analysis.timing_verdict },
  ];
  return (
    <motion.article {...CARD_ANIM} className="border border-ink/15">
      <ScoreHeader score={analysis.market_score} label="Market score" />
      <MetaGrid items={meta} />
      {(analysis.competitors ?? []).length > 0 && (
        <div className="border-b border-ink/15 p-5">
          <p className="label-mono mb-3 text-ink/60">Competitors</p>
          <div className="flex flex-wrap gap-2">
            {(analysis.competitors ?? []).map((c, i) => <Tag key={i}>{String(c)}</Tag>)}
          </div>
        </div>
      )}
      {analysis.differentiation && (
        <div className="border-b border-ink/15 p-5">
          <p className="label-mono mb-2 text-ink/60">Differentiation</p>
          <p className="font-sans text-sm leading-relaxed text-ink/90">{analysis.differentiation}</p>
        </div>
      )}
      {(analysis.key_risks ?? []).length > 0 && <BulletList label="Key risks" items={analysis.key_risks ?? []} />}
      {analysis.summary && <SummaryBlock text={analysis.summary} />}
    </motion.article>
  );
}

/* ------------------------------------------------------------------ */
/* FounderCard                                                         */
/* ------------------------------------------------------------------ */

export function FounderCard({ analysis }: { analysis: FounderAnalysis }) {
  return (
    <motion.article {...CARD_ANIM} className="border border-ink/15">
      <ScoreHeader score={analysis.founder_score} label="Founder score" />
      <div className="grid grid-cols-2 border-b border-ink/15">
        <div className="border-r border-ink/15 p-4">
          <p className="label-mono mb-1.5 text-muted-foreground">Team completeness</p>
          <p className="font-sans text-sm text-ink">{analysis.team_completeness || "—"}</p>
        </div>
        <div className="p-4">
          <p className="label-mono mb-1.5 text-muted-foreground">Prior exits</p>
          <p className="font-sans text-sm text-ink">{analysis.prior_exits ? "Yes" : "No"}</p>
        </div>
      </div>
      {analysis.founders.map((f, i) => {
        const redFlags = Array.isArray(f.red_flags) ? f.red_flags : [];
        return (
          <div key={i} className="border-b border-ink/15 p-5 last:border-b-0">
            <p className="label-mono mb-2 text-ink/60">{f.name || `Founder ${i + 1}`}</p>
            {f.background && <p className="mb-1 font-sans text-sm text-ink/80">{f.background}</p>}
            {f.domain_expertise && (
              <p className="mb-1 font-sans text-xs text-muted-foreground">
                Expertise: {f.domain_expertise}
              </p>
            )}
            {redFlags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {redFlags.map((flag, j) => (
                  <span key={j} className="border border-ink/30 px-2 py-0.5 font-mono text-[10px] tracking-wide text-ink/70">
                    {flag}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
      {analysis.summary && <SummaryBlock text={analysis.summary} />}
    </motion.article>
  );
}

/* ------------------------------------------------------------------ */
/* FinancialCard                                                       */
/* ------------------------------------------------------------------ */

export function FinancialCard({ analysis }: { analysis: FinancialAnalysis }) {
  const meta = [
    { icon: DollarSign, label: "Raise", value: analysis.raise_amount },
    { icon: TrendingUp, label: "Burn", value: analysis.burn_assessment },
    { icon: Target, label: "Path", value: analysis.path_to_profitability },
  ];
  const unitEcon = analysis.unit_economics;
  const hasUnitEcon = unitEcon && Object.keys(unitEcon).length > 0;
  return (
    <motion.article {...CARD_ANIM} className="border border-ink/15">
      <ScoreHeader score={analysis.financial_score} label="Financial score" />
      {analysis.revenue_model && (
        <div className="border-b border-ink/15 p-5">
          <p className="label-mono mb-2 text-ink/60">Revenue model</p>
          <p className="font-sans text-sm leading-relaxed text-ink/90">{analysis.revenue_model}</p>
        </div>
      )}
      <MetaGrid items={meta} />
      {hasUnitEcon && (
        <div className="border-b border-ink/15 p-5">
          <p className="label-mono mb-3 text-ink/60">Unit economics</p>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Object.entries(unitEcon!).map(([k, v]) => (
              <div key={k}>
                <dt className="font-mono text-[10px] uppercase tracking-ledger text-muted-foreground">{k}</dt>
                <dd className="mt-1 font-sans text-sm text-ink">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
      {(analysis.red_flags ?? []).length > 0 && <BulletList label="Red flags" items={analysis.red_flags ?? []} />}
      {analysis.summary && <SummaryBlock text={analysis.summary} />}
    </motion.article>
  );
}

/* ------------------------------------------------------------------ */
/* BearCard                                                            */
/* ------------------------------------------------------------------ */

export function BearCard({ bear }: { bear: BearCase }) {
  return (
    <motion.article {...CARD_ANIM} className="border border-ink/15">
      <ScoreHeader score={bear.bear_case_score} label="Risk score" />
      {(bear.market_challenges ?? []).length > 0 && <BulletList label="Market challenges" items={bear.market_challenges ?? []} />}
      {(bear.founder_challenges ?? []).length > 0 && <BulletList label="Founder challenges" items={bear.founder_challenges ?? []} />}
      {(bear.financial_challenges ?? []).length > 0 && <BulletList label="Financial challenges" items={bear.financial_challenges ?? []} />}
      {(bear.failure_modes ?? []).length > 0 && <BulletList label="Failure modes" items={bear.failure_modes ?? []} />}
      {bear.summary && <SummaryBlock text={bear.summary} />}
    </motion.article>
  );
}

/* ------------------------------------------------------------------ */
/* MemoCard                                                            */
/* ------------------------------------------------------------------ */

export function MemoCard({ memo, sourcingScore }: { memo: InvestmentMemo; sourcingScore?: number }) {
  const scores = [
    ...(sourcingScore !== undefined ? [{ label: "Sourcing", value: sourcingScore }] : []),
    { label: "Market", value: memo.market_score },
    { label: "Founder", value: memo.founder_score },
    { label: "Financial", value: memo.financial_score },
    { label: "Bear risk", value: memo.bear_case_score },
  ];
  return (
    <motion.article {...CARD_ANIM} className="border border-ink/15">
      {/* Verdict */}
      <div className="flex flex-col items-center justify-center border-b border-ink/15 bg-ink py-7 text-paper text-center">
        <span className="font-display text-4xl font-bold leading-none tracking-tightest">{memo.verdict}</span>
        <span className="mt-2 font-mono text-[9px] uppercase tracking-ledger text-paper/60">Verdict</span>
      </div>
      {/* Confidence */}
      <div className="flex flex-col items-center justify-center border-b border-ink/15 py-5 text-center">
        <p className="font-display text-3xl font-bold leading-none tracking-tightest">
          {memo.confidence_score}
          <span className="ml-1 font-sans text-sm font-normal text-muted-foreground">/100</span>
        </p>
        <p className="mt-2 font-mono text-[9px] uppercase tracking-ledger text-muted-foreground">Confidence</p>
      </div>

      {/* Sub-scores */}
      <div className={`grid ${scores.length === 5 ? "grid-cols-5" : "grid-cols-4"} border-b border-ink/15`}>
        {scores.map(({ label, value }) => (
          <div key={label} className="flex flex-col items-center border-r border-ink/15 py-4 last:border-r-0">
            <span className="font-display text-2xl font-bold">{value}</span>
            <span className="mt-1 font-mono text-[9px] uppercase tracking-ledger text-muted-foreground">{label}</span>
          </div>
        ))}
      </div>

      {memo.executive_summary && (
        <div className="border-b border-ink/15 p-5">
          <p className="label-mono mb-2 text-ink/60">Executive summary</p>
          <p className="font-sans text-sm leading-relaxed text-ink/90">{memo.executive_summary}</p>
        </div>
      )}
      {memo.recommendation && (
        <div className="border-b border-ink/15 p-5">
          <p className="label-mono mb-2 text-ink/60">Recommendation</p>
          <p className="font-sans text-sm leading-relaxed text-ink/90">{memo.recommendation}</p>
        </div>
      )}
      {(memo.due_diligence_questions ?? []).length > 0 && (
        <BulletList label="Due diligence questions" items={memo.due_diligence_questions ?? []} />
      )}
      {memo.suggested_valuation_range && (
        <div className="border-b border-ink/15 p-5">
          <p className="label-mono mb-1.5 text-ink/60">Suggested valuation range</p>
          <p className="font-sans text-sm text-ink">{memo.suggested_valuation_range}</p>
        </div>
      )}
      {memo.summary && <SummaryBlock text={memo.summary} />}
    </motion.article>
  );
}

/* ------------------------------------------------------------------ */
/* Shared primitives                                                   */
/* ------------------------------------------------------------------ */

function ScoreHeader({
  score,
  label,
  name,
  subtitle,
}: {
  score: number;
  label: string;
  name?: string;
  subtitle?: string | null;
}) {
  if (!name) {
    return (
      <div className="flex flex-col items-center justify-center border-b border-ink/15 bg-ink py-7 text-paper text-center">
        <span className="font-display text-5xl font-bold leading-none tracking-tightest">{score}</span>
        <span className="mt-2 font-mono text-[9px] uppercase tracking-ledger text-paper/60">{label}</span>
      </div>
    );
  }
  return (
    <div className="flex items-stretch border-b border-ink/15">
      <div className="flex w-32 shrink-0 flex-col items-center justify-center border-r border-ink/15 bg-ink py-6 text-paper text-center">
        <span className="font-display text-5xl font-bold leading-none tracking-tightest">{score}</span>
        <span className="mt-2 font-mono text-[9px] uppercase tracking-ledger text-paper/60">{label}</span>
      </div>
      <div className="flex flex-col justify-center p-6">
        <h3 className="font-display text-2xl font-bold leading-tight tracking-tight">{name}</h3>
        {subtitle && (
          <p className="mt-1 font-sans text-sm leading-relaxed text-muted-foreground">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

function MetaGrid({
  items,
}: {
  items: Array<{ icon: LucideIcon; label: string; value?: string | null }>;
}) {
  const cols = items.length === 2 ? "grid-cols-2" : "grid-cols-3";
  return (
    <dl className={cn("grid border-b border-ink/15", cols)}>
      {items.map(({ icon: Icon, label, value }) => (
        <div key={label} className="flex flex-col gap-2 border-r border-ink/15 p-4 last:border-r-0">
          <dt className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-ledger text-muted-foreground">
            <Icon className="h-3 w-3" strokeWidth={1.5} />
            {label}
          </dt>
          <dd className="font-sans text-sm text-ink">{value || "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

function BulletList({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="border-b border-ink/15 p-5 last:border-b-0">
      <p className="label-mono mb-3 text-ink/60">{label}</p>
      <ul className="flex flex-col gap-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 font-sans text-sm text-ink/90">
            <span className="mt-0.5 shrink-0 font-mono text-[10px] text-muted-foreground">→</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SummaryBlock({ text }: { text: string }) {
  return (
    <div className="p-5">
      <p className="label-mono mb-3 text-ink/60">Analyst summary</p>
      <p className="font-sans text-sm leading-relaxed text-ink/90">{text}</p>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="border border-ink/20 px-3 py-1 font-mono text-[11px] tracking-wide">
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* DebateRoom                                                          */
/* ------------------------------------------------------------------ */

export function DebateRoom({
  events,
  memo,
  runStatus,
  sourcingScore,
}: {
  events: FeedEvent[];
  memo?: InvestmentMemo;
  runStatus?: "queued" | "running" | "done";
  sourcingScore?: number;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  const isDevil = (speaker: string) => speaker === "Devil's Advocate";

  const phaseLabel = (phase: FeedEvent["phase"]) => {
    if (phase === "pipeline") return null;
    if (phase === "challenge") return "Challenge";
    if (phase === "rebuttal") return "Rebuttal";
    return "Evaluation";
  };

  return (
    <div className="flex flex-col gap-0 border border-ink/15">
      {/* Chat feed */}
      <div className="flex min-h-[300px] max-h-[520px] flex-col gap-4 overflow-y-auto p-5">
        {events.length === 0 && (
          <div className="flex items-center gap-3 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
            <span className="font-mono text-xs uppercase tracking-ledger">
              {runStatus === "done" ? "No events recorded." : "Starting pipeline…"}
            </span>
          </div>
        )}

        {events.map((msg, i) => {
          const devil = isDevil(msg.speaker);
          const label = phaseLabel(msg.phase);
          const isPipeline = msg.phase === "pipeline";
          const showRoundHeader = msg.phase === "challenge" && msg.round !== undefined &&
            (i === 0 || events.slice(0, i).every(e => e.phase !== "challenge") || events[i - 1].round !== msg.round);
          return (
            <div key={i}>
              {showRoundHeader && (
                <div className="my-2 flex items-center gap-3">
                  <div className="h-px flex-1 bg-ink/10" />
                  <span className="font-mono text-[9px] uppercase tracking-ledger text-muted-foreground">
                    Debate — Round {msg.round}
                  </span>
                  <div className="h-px flex-1 bg-ink/10" />
                </div>
              )}
              <motion.div
                initial={{ opacity: 1, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className="flex max-w-[88%] flex-col gap-1 items-start"
              >
                <span className="font-mono text-[9px] uppercase tracking-ledger text-muted-foreground">
                  {msg.speaker}{label ? ` · ${label}` : ""}
                </span>
                <div
                  className={cn(
                    "px-4 py-3 font-sans text-sm leading-relaxed whitespace-pre-wrap w-full",
                    devil && !isPipeline
                      ? "border-l-2 border-l-ink border border-ink/30 text-ink"
                      : isPipeline
                        ? "border border-dashed border-ink/20 text-ink/70"
                        : "border border-ink/20 text-ink",
                  )}
                >
                  {msg.content}
                </div>
              </motion.div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Final scorecard — appears once committee memo is ready */}
      {memo && <DebateScorecard memo={memo} sourcingScore={sourcingScore} />}
    </div>
  );
}

function DebateScorecard({ memo, sourcingScore }: { memo: InvestmentMemo; sourcingScore?: number }) {
  const scores = [
    ...(sourcingScore !== undefined ? [{ label: "Sourcing", value: sourcingScore }] : []),
    { label: "Market", value: memo.market_score },
    { label: "Founder", value: memo.founder_score },
    { label: "Financial", value: memo.financial_score },
    { label: "Bear Risk", value: memo.bear_case_score },
  ];
  return (
    <motion.div
      initial={{ opacity: 1, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="border-t border-ink/15"
    >
      <div className="flex items-stretch border-b border-ink/15">
        <div className="flex w-36 shrink-0 flex-col items-center justify-center border-r border-ink/15 bg-ink py-5 text-paper">
          <span className="font-display text-2xl font-bold tracking-tightest">{memo.verdict}</span>
          <span className="mt-1 font-mono text-[9px] uppercase tracking-ledger text-paper/60">Verdict</span>
        </div>
        <div className="flex items-center gap-3 px-6">
          <span className="font-display text-3xl font-bold">{memo.confidence_score}</span>
          <div className="flex flex-col">
            <span className="font-sans text-xs text-muted-foreground">/100 confidence</span>
            <span className="font-mono text-[9px] uppercase tracking-ledger text-muted-foreground">
              overall: {memo.overall_score}
            </span>
          </div>
        </div>
      </div>

      <div className={`grid ${scores.length === 5 ? "grid-cols-5" : "grid-cols-4"} border-b border-ink/15`}>
        {scores.map(({ label, value }) => (
          <div
            key={label}
            className="flex flex-col items-center border-r border-ink/15 py-3 last:border-r-0"
          >
            <span className="font-display text-xl font-bold">{value}</span>
            <span className="mt-0.5 font-mono text-[9px] uppercase tracking-ledger text-muted-foreground">
              {label}
            </span>
          </div>
        ))}
      </div>

      {memo.executive_summary && (
        <div className="p-5">
          <p className="label-mono mb-2 text-ink/60">Committee verdict</p>
          <p className="font-sans text-sm leading-relaxed text-ink/90">{memo.executive_summary}</p>
        </div>
      )}
    </motion.div>
  );
}
