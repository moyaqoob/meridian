import { FadeUp } from "./fade-up"

const steps = [
  ["PR event", "GitHub sends the changed files, metadata, branch, author, and review history."],
  ["Graph retrieval", "Meridian pulls callers, dependents, schema edges, tests, and style rules."],
  ["Agent review", "Specialized passes look for runtime risk, auth issues, data contracts, and missing tests."],
  ["Quiet publish", "Only high-confidence findings become PR comments. Everything else stays internal."],
]

export function LandingPipeline() {
  return (
    <section id="how" className="relative px-4 py-24 md:py-36">
      <div className="mx-auto max-w-[1180px]">
        <FadeUp>
          <div className="max-w-[780px]">
            <p className="mb-5 inline-flex rounded-full border border-[rgba(125,245,212,0.22)] bg-[rgba(125,245,212,0.07)] px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">
              How it works
            </p>
            <h2 className="font-[family-name:var(--font-display)] text-[clamp(36px,6vw,82px)] font-semibold leading-[0.96] tracking-[-0.07em] text-white">
              One PR enters. Four review passes run in parallel.
            </h2>
          </div>
        </FadeUp>

        <div className="mt-14 grid gap-5 lg:grid-cols-4">
          {steps.map(([title, body], index) => (
            <FadeUp key={title}>
              <div className="relative rounded-[30px] border border-white/10 bg-white/[0.045] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
                <div className="min-h-[260px] rounded-[23px] border border-white/8 bg-[#0b0f12] p-6">
                  <div className="mb-8 flex items-center justify-between">
                    <span className="flex size-11 items-center justify-center rounded-full bg-[rgba(125,245,212,0.1)] font-[family-name:var(--font-mono)] text-sm text-[var(--accent)] ring-1 ring-[rgba(125,245,212,0.22)]">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="h-px flex-1 translate-x-6 bg-[linear-gradient(90deg,rgba(125,245,212,0.5),transparent)] max-lg:hidden" />
                  </div>
                  <h3 className="text-xl font-semibold tracking-[-0.03em] text-white">{title}</h3>
                  <p className="mt-4 text-sm leading-7 text-[var(--text-muted)]">{body}</p>
                </div>
              </div>
            </FadeUp>
          ))}
        </div>
      </div>
    </section>
  )
}
