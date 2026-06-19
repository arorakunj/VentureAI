import {
  Crosshair,
  Globe2,
  Users,
  LineChart,
  ShieldAlert,
  FileText,
  type LucideIcon,
} from "lucide-react";

export type FieldKind = "text" | "textarea" | "url";

export interface AgentField {
  /** Key sent to the backend (the sourcing agent reads `input`). */
  key: string;
  label: string;
  placeholder: string;
  kind: FieldKind;
  helper?: string;
}

export interface AgentConfig {
  id: string;
  /** Ledger code shown in the index, e.g. VA-01. */
  code: string;
  name: string;
  role: string;
  /** One-line editorial summary for the bento cell. */
  summary: string;
  /** What the agent produces, in plain language. */
  capability: string;
  icon: LucideIcon;
  /** The Band message_type this agent publishes. */
  outputType: string;
  isAvailable: boolean;
  fields: AgentField[];
}

/**
 * The investment-committee index. Order is the real pipeline order
 * (sourcing -> market -> founder -> financial -> bear -> memo), which is why
 * the UI numbers them — the sequence carries meaning, it isn't decoration.
 */
export const AGENTS: AgentConfig[] = [
  {
    id: "sourcing",
    code: "VA-01",
    name: "Deal Sourcing",
    role: "Intake & structuring",
    summary:
      "Turns a name, URL, or raw blurb into a structured startup profile with a first-pass conviction score.",
    capability: "Structured profile + 0–100 score",
    icon: Crosshair,
    outputType: "startup_profile",
    isAvailable: true,
    fields: [
      {
        key: "input",
        label: "Company signal",
        placeholder:
          "Paste a company name, website, or a few sentences describing the startup…",
        kind: "textarea",
        helper:
          "Anything works — a domain, a one-liner, or a pasted paragraph from a pitch deck.",
      },
    ],
  },
  {
    id: "market",
    code: "VA-02",
    name: "Market Research",
    role: "Opportunity sizing",
    summary:
      "Sizes the TAM, reads the competitive landscape, and renders a verdict on market timing.",
    capability: "TAM, competitors, timing verdict",
    icon: Globe2,
    outputType: "market_analysis",
    isAvailable: true,
    fields: [
      {
        key: "input",
        label: "Company or profile",
        placeholder: "Select a sourced company to analyze its market…",
        kind: "textarea",
      },
    ],
  },
  {
    id: "founder",
    code: "VA-03",
    name: "Founder Diligence",
    role: "Team assessment",
    summary:
      "Evaluates founder–market fit, team completeness, and prior exits — with the red flags left in.",
    capability: "Founder scorecard + flags",
    icon: Users,
    outputType: "founder_analysis",
    isAvailable: true,
    fields: [
      {
        key: "input",
        label: "Founding team",
        placeholder: "Select a sourced company to assess its founders…",
        kind: "textarea",
      },
    ],
  },
  {
    id: "financial",
    code: "VA-04",
    name: "Financial Analysis",
    role: "Model & unit economics",
    summary:
      "Pressure-tests the revenue model, unit economics, burn, and the path to profitability.",
    capability: "Unit economics + red flags",
    icon: LineChart,
    outputType: "financial_analysis",
    isAvailable: true,
    fields: [
      {
        key: "input",
        label: "Business model",
        placeholder: "Select a sourced company to model its economics…",
        kind: "textarea",
      },
    ],
  },
  {
    id: "bear",
    code: "VA-05",
    name: "Bear Case",
    role: "Adversarial review",
    summary:
      "Argues the other side — failure modes, fragilities, and the reasons this deal could break.",
    capability: "Structured failure modes",
    icon: ShieldAlert,
    outputType: "bear_case",
    isAvailable: true,
    fields: [
      {
        key: "input",
        label: "Thesis to stress-test",
        placeholder: "Select a sourced company to build the bear case…",
        kind: "textarea",
      },
    ],
  },
  {
    id: "memo",
    code: "VA-06",
    name: "Investment Memo",
    role: "Synthesis & verdict",
    summary:
      "Synthesizes every agent into one committee-ready memo: a verdict, a score, and the next questions.",
    capability: "PASS · WATCH · INVEST verdict",
    icon: FileText,
    outputType: "investment_memo",
    isAvailable: true,
    fields: [
      {
        key: "input",
        label: "Deal to synthesize",
        placeholder: "Select a completed analysis to compile the memo…",
        kind: "textarea",
      },
    ],
  },
];

export const getAgent = (id: string): AgentConfig | undefined =>
  AGENTS.find((a) => a.id === id);
