import { Link, useLocation } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Global wrapper. Establishes the strict black/paper boundary, the fixed
 * editorial masthead, and the ledger footer. Every page lives inside this.
 */
export function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const onWorkspace = pathname.startsWith("/app");

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      {/* Skip link for keyboard users. */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-6 focus:top-6 focus:z-50 focus:bg-ink focus:px-4 focus:py-2 focus:font-mono focus:text-xs focus:uppercase focus:tracking-[0.2em] focus:text-paper"
      >
        Skip to content
      </a>

      <Masthead onWorkspace={onWorkspace} />

      <main id="main" className="flex-1">
        {children}
      </main>

      <Footer />
    </div>
  );
}

function Masthead({ onWorkspace }: { onWorkspace: boolean }) {
  return (
    <header className="sticky top-0 z-40 border-b border-ink/10 bg-paper/85 backdrop-blur-sm">
      <div className="container flex h-16 items-center justify-between">
        <Link to="/" className="group flex items-baseline gap-3">
          <span className="font-display text-lg font-bold tracking-tightest">
            VentureAI
          </span>
          <span className="hidden label-mono sm:inline">Investment Copilot</span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          <NavLink to="/" active={!onWorkspace}>
            Overview
          </NavLink>
          <NavLink to="/app" active={onWorkspace}>
            Workspace
          </NavLink>
          <Link
            to="/app"
            className="ml-2 hidden items-center gap-1.5 border border-ink bg-ink px-4 py-2 font-mono text-[11px] uppercase tracking-[0.2em] text-paper transition-all duration-300 ease-out hover:bg-transparent hover:text-ink sm:inline-flex"
          >
            Launch
            <ArrowUpRight className="h-3.5 w-3.5" strokeWidth={1.75} />
          </Link>
        </nav>
      </div>
    </header>
  );
}

function NavLink({
  to,
  active,
  children,
}: {
  to: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      className={cn(
        "px-3 py-2 font-mono text-[11px] uppercase tracking-[0.2em] transition-colors duration-300",
        active ? "text-ink" : "text-muted-foreground hover:text-ink",
      )}
    >
      {children}
    </Link>
  );
}

function Footer() {
  return (
    <footer className="border-t border-ink/10">
      <div className="container flex flex-col gap-6 py-10 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-base font-bold tracking-tightest">
            VentureAI
          </span>
          <span className="label-mono">© {new Date().getFullYear()}</span>
        </div>
        <p className="max-w-sm font-sans text-sm leading-relaxed text-muted-foreground">
          A research copilot. Not investment advice. Every agent output is a
          draft for the committee, not a decision.
        </p>
      </div>
    </footer>
  );
}
