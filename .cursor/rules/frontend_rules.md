---
description: frontend rules
alwaysApply: false
---

# Meridian — Frontend Rules
# Next.js 14 · TypeScript · React · Tailwind CSS

---

## What This Frontend Is

The Meridian frontend is the interface between an engineer and an AI review pipeline.
It is not a marketing site. It is not a dashboard with charts.
It is a **real-time engineering tool** — the kind of UI that engineers will open 10 times a day.

Every decision — layout, color, animation, error state — must be made with that person in mind:
someone who is in flow, opening a PR, wanting to understand what the AI found and move on.

---

## Project Structure

```
src/
  app/                          # Next.js App Router — pages only, no logic
    layout.tsx                  # Root layout: fonts, theme, global providers
    page.tsx                    # Landing page
    dashboard/
      page.tsx                  # Repo list + ingestion status
    repo/
      [owner]/
        [repo]/
          page.tsx              # Repo settings + re-ingestion trigger
    pr/
      [owner]/
        [repo]/
          [number]/
            page.tsx            # 3-panel PR review page (the crown jewel)

  components/
    ui/                         # Primitive components — Button, Badge, Spinner, etc.
    auth/
      github-login-button.tsx
    dashboard/
      repo-card.tsx             # Single repo — status, last review, actions
      ingestion-progress.tsx    # Step-by-step ingestion visualization
    pr/
      diff-panel.tsx            # Left panel: PR diff with syntax highlighting
      pipeline-panel.tsx        # Middle panel: live stage visualization
      review-panel.tsx          # Right panel: structured findings
      stage-indicator.tsx       # Single pipeline stage row
      finding-card.tsx          # Single review finding with severity badge
      summary-bar.tsx           # Bottom bar: counts by severity + category

  lib/
    api/
      client.ts                 # Base fetch wrapper — handles auth, errors, retries
      endpoints.ts              # All API URLs in one place — never inline URLs
      types.ts                  # API response types — generated from backend schemas
    hooks/
      use-review-stream.ts      # SSE connection + event parsing for PR review
      use-ingestion-status.ts   # Polling hook for ingestion job status
      use-repos.ts              # Fetch + cache user's connected repos
    utils/
      diff-parser.ts            # Parse raw diff text into structured hunk objects
      severity.ts               # Severity → color/label/icon mappings
      format.ts                 # Dates, durations, line counts
    constants.ts                # App-wide constants — never magic strings

  types/
    review.ts                   # ReviewOut, Annotation, Finding, PipelineStage
    repo.ts                     # Repo, IngestionJob, IngestStatus
    pr.ts                       # PR, PRStatus
    events.ts                   # SSE event shapes — StageUpdate, GenerationChunk, Complete
```

---

## TypeScript Rules

**Strict mode is non-negotiable.**

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "exactOptionalPropertyTypes": true
  }
}
```

**Type everything that crosses a boundary.**

API responses, SSE events, component props — all typed. No `any`. No `as unknown as X`.
If you need to cast, you have a typing problem, not a casting opportunity.

```typescript
// WRONG
const review = await fetchReview(id) as any

// RIGHT
const review: ReviewOut = await fetchReview(id)
// where ReviewOut is defined in types/review.ts and matches the Pydantic schema exactly
```

**Discriminated unions for state machines.**

The pipeline has stages. Model them as a union, not as flags.

```typescript
type PipelineState =
  | { status: 'idle' }
  | { status: 'queued'; queuedAt: string }
  | { status: 'running'; stage: PipelineStage; progress: number; message: string }
  | { status: 'complete'; reviewId: string; timings: Record<PipelineStage, number> }
  | { status: 'error'; stage: PipelineStage; message: string; retryable: boolean }

// Now exhaustive switch statements are enforced by the compiler.
// You cannot forget the error case. You cannot forget the queued case.
```

**Never use optional chaining to paper over missing types.**

`review?.summary?.findings?.[0]?.comment` means your types are wrong.
Fix the types. The data is either there or it isn't — model that explicitly.

---

## Component Rules

**One job per component.**

A component either fetches data or renders it. Not both.
Data fetching lives in hooks. Components receive props and render.

```typescript
// WRONG — component doing too much
export function ReviewPanel({ prId }: { prId: string }) {
  const [review, setReview] = useState(null)
  useEffect(() => { fetch(`/api/pr/${prId}/review`).then(...) }, [prId])
  return <div>{review?.summary}</div>
}

// RIGHT — hook owns data, component owns rendering
export function ReviewPanel({ review }: { review: ReviewOut }) {
  return <div>{review.summary}</div>
}

// In the page:
const { review, isLoading } = useReview(prId)
return <ReviewPanel review={review} />
```

**Props interfaces are explicit and documented.**

```typescript
interface FindingCardProps {
  finding: ReviewFinding
  /** Whether this card is currently highlighted from a diff annotation click */
  isActive?: boolean
  onDismiss?: (findingId: string) => void
}
```

**Never pass raw objects when a specific type is enough.**

```typescript
// WRONG
<RepoCard repo={repos[0]} />  // where repos is any[]

// RIGHT
<RepoCard repo={repo} />      // where repo is Repo
```

**No prop drilling beyond 2 levels.**

If you're passing a prop through 3 components, use context or lift to the page level.
The PR review page manages its own state via `usePRReview()` — panels receive slices.

---

## The PR Review Page — Special Rules

This is the most important screen in the product. It deserves its own section.

**Three panels. Fixed layout. No scrolling the outer frame.**

```
┌─────────────────┬──────────────┬─────────────────┐
│                 │              │                  │
│   Diff Panel    │  Pipeline    │  Review Panel    │
│   (scrollable)  │   Panel      │  (scrollable)    │
│                 │  (fixed)     │                  │
│                 │              │                  │
└─────────────────┴──────────────┴─────────────────┘
│              Summary Bar (fixed bottom)           │
└───────────────────────────────────────────────────┘
```

The outer frame never scrolls. Each panel scrolls independently.
The pipeline panel is fixed height — it shows stages, not content.

**The SSE connection is owned by the page, not the panels.**

```typescript
// pr/[owner]/[repo]/[number]/page.tsx
export default function PRReviewPage({ params }: PageProps) {
  const { pipeline, review, error } = useReviewStream(params)

  return (
    <div className="pr-review-layout">
      <DiffPanel diff={review?.diff} annotations={review?.annotations} />
      <PipelinePanel state={pipeline} />
      <ReviewPanel review={review} isStreaming={pipeline.status === 'running'} />
      <SummaryBar findings={review?.findings} />
    </div>
  )
}
```

**Stream the review text as it arrives.**

Don't wait for the complete event to render the review panel.
As `generation-chunk` events arrive, append to the displayed text.
The panel should feel alive — like watching someone type.

**Handle the late-connect case explicitly.**

If the user opens the PR page after the review is already complete,
`useReviewStream` must detect this and hydrate from the REST endpoint,
not wait for SSE events that will never come.

```typescript
// use-review-stream.ts
export function useReviewStream(prId: string) {
  // 1. First, check if review already exists (REST call)
  // 2. If yes: hydrate immediately, no SSE needed
  // 3. If no: open SSE connection, consume events
  // 4. On complete event: close SSE, store final state
}
```

---

## SSE Handling

**One hook. One connection. No leaks.**

```typescript
// lib/hooks/use-review-stream.ts

export function useReviewStream(prId: string) {
  const [state, dispatch] = useReducer(reviewStreamReducer, initialState)

  useEffect(() => {
    const es = new EventSource(`/api/pr/${prId}/review/stream`)

    es.addEventListener('stage-update', (e) => {
      const event = StageUpdateSchema.parse(JSON.parse(e.data))
      dispatch({ type: 'STAGE_UPDATE', payload: event })
    })

    es.addEventListener('generation-chunk', (e) => {
      const event = GenerationChunkSchema.parse(JSON.parse(e.data))
      dispatch({ type: 'APPEND_CHUNK', payload: event })
    })

    es.addEventListener('complete', (e) => {
      const event = CompleteEventSchema.parse(JSON.parse(e.data))
      dispatch({ type: 'COMPLETE', payload: event })
      es.close()
    })

    es.addEventListener('error', (e) => {
      dispatch({ type: 'ERROR' })
      es.close()
    })

    return () => es.close()   // cleanup — never leak EventSource connections
  }, [prId])

  return state
}
```

**Validate every SSE event at the boundary.**

Use Zod. Every event shape has a schema. Parse before dispatching.
A malformed event from the backend should never crash the UI.

```typescript
// types/events.ts
import { z } from 'zod'

export const StageUpdateSchema = z.object({
  stage: z.enum(['validation', 'retrieval', 'generation', 'citation-mapping', 'complete']),
  progress: z.number().min(0).max(1),
  message: z.string(),
  duration_ms: z.number().optional(),
})

export type StageUpdate = z.infer<typeof StageUpdateSchema>
```

---

## API Client

**All API calls go through one client. No raw fetch calls in components.**

```typescript
// lib/api/client.ts

class MeridianClient {
  private baseUrl = process.env.NEXT_PUBLIC_API_URL

  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      credentials: 'include',   // always send session cookie
    })
    if (!res.ok) throw new APIError(res.status, await res.json())
    return res.json()
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new APIError(res.status, await res.json())
    return res.json()
  }
}

export const api = new MeridianClient()
```

**All endpoint paths live in one file.**

```typescript
// lib/api/endpoints.ts
export const endpoints = {
  repos: {
    list: () => '/api/repos',
    connect: () => '/api/repos/connect',
    ingestStatus: (jobId: string) => `/api/ingest/${jobId}`,
  },
  pr: {
    reviewStream: (owner: string, repo: string, number: number) =>
      `/api/pr/${owner}/${repo}/${number}/review/stream`,
    triggerReview: () => '/api/review/trigger',
  },
  auth: {
    github: () => '/api/auth/github',
    logout: () => '/api/auth/logout',
  },
} as const
```

---

## State Management

**No global state library. React state + hooks is enough.**

The app has three meaningful pieces of state:
- Auth state — whether the user is logged in (server-side via session, not client state)
- Repo list — fetched once on dashboard mount
- PR review stream — lives on the PR page only

None of these need Redux, Zustand, or Jotai. If you find yourself reaching for a global store,
you have a component hierarchy problem, not a state management problem.

**Server components for data that doesn't change during a session.**

Repo list, PR metadata, user info — fetch these as React Server Components.
Only hydrate to client components when you need interactivity or SSE.

---

## Error Handling

**Every async boundary has an error state. No exceptions.**

```typescript
// Every data-fetching hook returns this shape:
interface AsyncState<T> {
  data: T | null
  isLoading: boolean
  error: string | null
}
```

**Error boundaries wrap each panel independently.**

If the review panel crashes, the diff panel still works.
If the pipeline panel crashes, the review still renders.
The three panels are failure-isolated.

```typescript
<ErrorBoundary fallback={<PanelError message="Review failed to load" />}>
  <ReviewPanel review={review} />
</ErrorBoundary>
```

**Errors shown to users are human, not technical.**

```typescript
// WRONG
"Error: 503 Service Unavailable"

// RIGHT
"Review generation is taking longer than expected. We'll retry automatically."
```

---

## Styling — Tailwind CSS

**Dark theme. Always. This is an engineering tool, not a marketing page.**

The design language: dark backgrounds, muted text, bright accents for status.
Reference the architecture doc's color palette — it's already right.

```
Background:      #0b1220  (panels)   #0f172a  (cards)   #020617  (code)
Borders:         #1f2937
Primary text:    #e5e7eb
Muted text:      #64748b  #94a3b8
Accent blue:     #2563eb  #60a5fa
Success green:   #4ade80  #16a34a
Warning amber:   #fbbf24  #f59e0b
Error red:       #f87171  #dc2626
```

**Severity colors are semantic and consistent everywhere.**

```typescript
// lib/utils/severity.ts
export const severityConfig = {
  high:   { color: 'text-red-400',    bg: 'bg-red-400/10',    label: 'High' },
  medium: { color: 'text-amber-400',  bg: 'bg-amber-400/10',  label: 'Medium' },
  low:    { color: 'text-blue-400',   bg: 'bg-blue-400/10',   label: 'Low' },
} as const
```

Use these. Never hardcode severity colors inline.

**Monospace font for all code, diffs, file paths, line numbers.**

```
font-family: 'JetBrains Mono', monospace
```

Applied via Tailwind class `font-mono` on any element that shows code or paths.

**No inline styles. No style props. Tailwind classes only.**

Exception: dynamic values that Tailwind cannot express (e.g. progress bar width from a percentage).
In that case: CSS custom property via `style={{ '--progress': `${n}%` }}` and a CSS rule.

---

## Pipeline Panel — Visual Spec

The pipeline panel is the "heartbeat" of the product. It must feel alive.

```
✓  Validation          complete    (0.8s)
✓  Retrieval           complete    (1.2s) · 20 chunks
⟳  Generation          running...
◌  Citation Mapping    waiting
◌  Complete            waiting
```

Stage states: `waiting | running | complete | error`

- `waiting` — muted gray, hollow circle
- `running` — blue, spinning indicator, pulsing
- `complete` — green checkmark, duration shown
- `error` — red X, error message shown inline

**The generation stage shows live streamed text below it** as `generation-chunk` events arrive.
Small, muted, monospace. It should look like a terminal output, not a chat bubble.

**Transitions are smooth but fast.** 150ms ease-in for stage state changes. No bouncing. No delay.

---

## Diff Panel — Visual Spec

Render the diff as a proper code diff viewer:

- Added lines: `bg-green-400/10` with `+` prefix in `text-green-400`
- Removed lines: `bg-red-400/10` with `-` prefix in `text-red-400`
- Context lines: no background, muted text
- Line numbers: fixed-width, muted, monospace, right-aligned
- File path headers: `bg-slate-800`, full path in amber

When a review annotation targets a line in the diff,
that line gets a left border highlight in the severity color:

```
52 │  result = self.llm.generate(context)   ← amber left border for medium severity
```

Clicking that highlighted line scrolls the review panel to the matching finding.
Clicking a finding in the review panel scrolls the diff to the matching line.
**The two panels are linked.** That's the magic of the product.

---

## Ingestion Progress — Visual Spec

```
Indexing yaqoob/freellmapi

  Cloning repository         ✓ Complete (12s)
  Parsing file tree          ✓ Complete (2s)
  Chunking with tree-sitter  ✓ Complete (8s) · 1,247 chunks
  Embedding + storing        ⟳ 68% · 847 / 1,247 chunks
  Finalizing index           ◌ Waiting
```

This is polled via `GET /api/ingest/{job_id}` every 2 seconds.
Stop polling when status is `ready` or `failed`.
Show a subtle progress bar at the top of the panel for the current step.

---

## Loading States

**Every async operation has a skeleton, not a spinner.**

Spinners say "something is happening, I don't know what."
Skeletons say "content is coming, here's where it will land."

The dashboard repo list: skeleton cards matching the repo-card shape.
The review panel: skeleton lines matching the findings layout.
The diff panel: skeleton code lines.

**The pipeline panel is the one place a live indicator is appropriate.**

The spinning `⟳` on the active stage is the live indicator for the whole review.
Everything else loads silently behind skeletons.

---

## Performance

**The PR page must be interactive in under 2 seconds on a fast connection.**

- Route-level code splitting is automatic with Next.js App Router — don't undo it
- The diff panel uses virtual scrolling for large diffs (react-virtual or similar)
  A 500-line diff should not render 500 DOM nodes
- SSE events are batched via `requestAnimationFrame` before dispatching to state
  Never dispatch one React state update per SSE chunk — batch them

**Images and icons:**

- Use `next/image` for any raster images
- Use Lucide React for icons — tree-shakeable, consistent, no bundle bloat
- No icon fonts

---

## Testing

**Test behavior, not implementation.**

```typescript
// WRONG — testing implementation
expect(component.state.isLoading).toBe(true)

// RIGHT — testing behavior
expect(screen.getByText('Indexing repository...')).toBeInTheDocument()
```

**What to test:**

- `useReviewStream` — mock EventSource, assert state transitions are correct
- `diff-parser.ts` — pure function, unit test all edge cases (empty diff, binary file, rename)
- `ReviewPanel` — snapshot + interaction: clicking a finding highlights the correct diff line
- `PipelinePanel` — renders correct stage state for each `PipelineState` variant

**What not to test:**

- Styling (CSS classes in snapshots are fragile and meaningless)
- Third-party library behavior
- API responses (mock at the boundary, don't test the mock)

---

## What Not To Build (MVP Scope)

These are real features. Build them later.

- Inline diff annotation overlay — show review as text in the panel first
- PR history and past reviews list — the table exists, the UI can wait
- Repo settings page with custom rules — connect + ingest is enough
- Dark/light theme toggle — dark only for now
- Mobile layout — this is a desktop tool, responsive is a v2 concern
- Keyboard shortcuts — ship the mouse-first experience first
