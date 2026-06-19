# VentureAI — Frontend

The copilot for high-conviction venture capital. A strict monochrome, editorial
React interface for the VentureAI agent committee.

## Stack

- **React 18 + TypeScript + Vite**
- **Tailwind CSS** — strict achromatic design system (no accent hue)
- **Framer Motion** — scroll-triggered reveals and stagger
- **Lucide React** — iconography (no emoji, ever)
- Self-contained shadcn-style primitives in `src/components/ui`

## Run

```bash
cd ventureai/frontend
npm install
npm run dev          # http://localhost:5173
```

The dev server proxies `/evaluate`, `/status`, `/memo`, and `/ws` to the FastAPI
backend on `http://localhost:8000`. Start the backend separately:

```bash
# from the repo root
uvicorn ventureai.backend.main:app --reload
```

## Structure

| File | Role |
| --- | --- |
| `src/components/Layout.tsx` | Global masthead/footer + theme boundary |
| `src/components/LandingPage.tsx` | Hero, scroll-animated bento index, CTA |
| `src/components/AppWorkspace.tsx` | Multi-pane deal console |
| `src/config/agents.ts` | Agent registry + `isAvailable` flags |
| `src/lib/api.ts` | Typed client for the FastAPI backend |

## Agent availability

`src/config/agents.ts` is the single source of truth. Only **Deal Sourcing**
(`isAvailable: true`) is wired into the backend REST surface today; the rest
render an elegant "deployment pending" state. Flip a flag to `true` once its
endpoint is live and the workspace upgrades automatically.

## Design notes

- **Type:** Nunito (display + body, weight carries hierarchy) · IBM Plex Mono (data labels)
- **Color:** dark, strictly achromatic — status is shown with shape + motion, never color
- Respects `prefers-reduced-motion`; keyboard focus is always visible
