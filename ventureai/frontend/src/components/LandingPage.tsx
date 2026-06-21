import { Link } from "react-router-dom";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { ArrowUpRight, ArrowDown } from "lucide-react";
import { AGENTS } from "@/config/agents";
import { StatusGlyph } from "@/components/ui/status-glyph";

export function LandingPage() {
  return (
    <>
      <Hero />
      <IndexGrid />
      <CallToAction />
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Hero — centered editorial thesis, scroll-reveal, grid backdrop.    */
/* ------------------------------------------------------------------ */

function Hero() {
  const reduce = useReducedMotion();

  const rise: Variants = {
    hidden: { opacity: 1, y: reduce ? 0 : 28 },
    show: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: i * 0.1 },
    }),
  };

  return (
    <section className="relative overflow-hidden border-b border-ink/10">
      {/* Hairline grid backdrop with radial fade */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-50"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,0,0,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.04) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
          maskImage:
            "radial-gradient(120% 90% at 50% 30%, #000 30%, transparent 75%)",
          WebkitMaskImage:
            "radial-gradient(120% 90% at 50% 30%, #000 30%, transparent 75%)",
        }}
      />

      <div className="container relative flex flex-col items-center pb-28 pt-36 text-center sm:pb-36 sm:pt-44">
        {/* Status pill */}
        <motion.span
          custom={0}
          initial="hidden"
          animate="show"
          variants={rise}
          className="mb-12 inline-flex items-center gap-2.5 border border-ink/15 px-4 py-2"
        >
          <StatusGlyph available showLabel={false} />
          <span className="label-mono">VentureAI — Investment Copilot</span>
        </motion.span>

        {/* Headline */}
        <motion.h1
          custom={1}
          initial="hidden"
          animate="show"
          variants={rise}
          className="max-w-[16ch] font-display text-[clamp(3rem,11vw,9rem)] font-bold leading-[0.92] tracking-tightest"
        >
          Venture
          <span className="block italic font-medium">conviction,</span>
          <span className="block">at speed.</span>
        </motion.h1>

        {/* Display paragraph */}
        <motion.p
          custom={2}
          initial="hidden"
          animate="show"
          variants={rise}
          className="mt-9 max-w-[760px] font-display text-xl leading-snug tracking-tight sm:text-2xl lg:text-3xl"
        >
          The copilot for high-conviction venture capital — a committee of
          specialist agents that source, vet, and stress-test a deal
          before you ever take the meeting.
        </motion.p>

        {/* Body text */}
        <motion.p
          custom={3}
          initial="hidden"
          animate="show"
          variants={rise}
          className="mt-6 max-w-[520px] font-sans text-base leading-relaxed text-muted-foreground"
        >
          Six agents, one pipeline. Each renders its own verdict; you keep every
          one of them.
        </motion.p>

        {/* CTAs */}
        <motion.div
          custom={4}
          initial="hidden"
          animate="show"
          variants={rise}
          className="mt-12 flex flex-wrap justify-center gap-4"
        >
          <Link
            to="/app"
            className="inline-flex items-center gap-2.5 bg-ink px-9 py-5 font-mono text-xs uppercase tracking-[0.2em] text-paper transition-all duration-300 ease-out hover:bg-transparent hover:text-ink hover:shadow-[inset_0_0_0_1px_theme(colors.ink)]"
          >
            Enter the workspace
            <ArrowUpRight className="h-4 w-4" strokeWidth={1.75} />
          </Link>
          <a
            href="#va-index"
            onClick={(e) => {
              e.preventDefault();
              document
                .getElementById("va-index")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
            className="inline-flex items-center gap-2.5 border border-ink/20 px-9 py-5 font-mono text-xs uppercase tracking-[0.2em] text-ink transition-all duration-300 ease-out hover:border-ink"
          >
            Meet the committee
          </a>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 1 }}
          animate={{ opacity: 1 }}
          className="mt-20 flex flex-col items-center gap-3 text-muted-foreground"
        >
          <ArrowDown
            className="h-[18px] w-[18px] animate-bounce"
            strokeWidth={1.5}
          />
          <span className="label-mono">The index — six agents</span>
        </motion.div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Index grid — centered header, bento ledger, scroll-staggered.      */
/* ------------------------------------------------------------------ */

function IndexGrid() {
  const reduce = useReducedMotion();

  const container: Variants = {
    hidden: {},
    show: {
      transition: { staggerChildren: reduce ? 0 : 0.09, delayChildren: 0.05 },
    },
  };

  const cell: Variants = {
    hidden: { opacity: 0, y: reduce ? 0 : 36 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] },
    },
  };

  const spans = [
    "sm:col-span-2 lg:col-span-2",
    "",
    "",
    "",
    "",
    "sm:col-span-2 lg:col-span-2",
  ];

  return (
    <section id="va-index" className="border-b border-paper/10 bg-ink text-paper">
      <div className="container py-24 sm:py-32">
        {/* Centered section header */}
        <motion.div
          initial={{ opacity: 0, y: reduce ? 0 : 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mb-16 flex flex-col items-center gap-5 text-center"
        >
          <span className="label-mono">The committee</span>
          <h2 className="font-display text-4xl font-bold leading-tight tracking-tightest sm:text-5xl">
            Six specialists,<br />one pipeline
          </h2>
          <p className="max-w-[520px] font-sans text-base leading-relaxed text-muted-foreground">
            Each agent is a numbered entry in the deal ledger. The order is the
            pipeline order — intake to verdict.
          </p>
        </motion.div>

        <motion.ol
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          className="grid grid-cols-1 gap-px bg-paper/10 sm:grid-cols-2 lg:grid-cols-3"
        >
          {AGENTS.map((agent, i) => {
            const Icon = agent.icon;
            return (
              <motion.li
                key={agent.id}
                variants={cell}
                className={`group relative flex flex-col justify-between gap-10 bg-ink p-8 transition-colors duration-300 hover:bg-paper hover:text-ink sm:min-h-[280px] ${spans[i]}`}
              >
                <Link to="/app" className="absolute inset-0" aria-label={`Open ${agent.name} in workspace`} />
                <div className="flex items-start justify-between">
                  <span className="font-mono text-xs tracking-[0.2em] text-muted-foreground transition-colors duration-300 group-hover:text-ink/60">
                    {agent.code}
                  </span>
                  <Icon
                    className="h-6 w-6 text-paper transition-colors duration-300 group-hover:text-ink"
                    strokeWidth={1.4}
                  />
                </div>

                <div>
                  <div className="mb-4">
                    <StatusGlyph available={agent.isAvailable} />
                  </div>
                  <h3 className="font-display text-2xl font-bold tracking-tight">
                    {agent.name}
                  </h3>
                  <p className="mt-3 font-sans text-sm leading-relaxed text-muted-foreground transition-colors duration-300 group-hover:text-ink/70">
                    {agent.summary}
                  </p>
                  <p className="mt-5 font-mono text-[11px] uppercase tracking-[0.18em] text-paper transition-colors duration-300 group-hover:text-ink">
                    {agent.capability}
                  </p>
                </div>
              </motion.li>
            );
          })}
        </motion.ol>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* CTA — centered, inverted, stark single statement.                  */
/* ------------------------------------------------------------------ */

function CallToAction() {
  const reduce = useReducedMotion();

  return (
    <section className="bg-paper text-ink">
      <div className="container py-32 sm:py-40">
        <motion.div
          initial={{ opacity: 0, y: reduce ? 0 : 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center gap-12 text-center"
        >
          <span className="label-mono text-ink/50">Begin a memo</span>
          <h2 className="max-w-[12ch] font-display text-[clamp(2.75rem,8vw,7rem)] font-bold leading-[0.95] tracking-tightest">
            Bring a deal.
            <span className="block italic font-medium text-ink/80">
              Leave with a verdict.
            </span>
          </h2>
          <Link
            to="/app"
            className="group inline-flex items-center gap-3 border border-ink/30 px-9 py-5 font-mono text-xs uppercase tracking-[0.2em] text-ink transition-all duration-300 ease-out hover:bg-ink hover:text-paper"
          >
            Open the workspace
            <ArrowUpRight
              className="h-4 w-4 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
              strokeWidth={1.75}
            />
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
