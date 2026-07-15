import { FadeUp } from "./fade-up"

const problems = [
  {
    title: "AI writes more code than humans can review",
    body: "The bottleneck moved. Teams can generate changes all day, but review still depends on a tired engineer reconstructing context from memory.",
  },
  {
    title: "Diff-only tools miss the real failure mode",
    body: "The risky part is usually outside the changed hunk: a caller, a schema contract, an async side effect, or the test nobody opened.",
  },
  {
    title: "Noisy reviewers train teams to ignore them",
    body: "Meridian is confidence-gated. If it cannot attach the finding to repo evidence, it does not post the comment.",
  },
]

export function LandingProblem() {
  return (
    <section className="relative px-4 py-24 md:py-36">
      <div className="mx-auto max-w-[1180px]">
        <FadeUp>
          <div className="max-w-[860px]">
            <p className="mb-5 inline-flex rounded-full border border-[rgba(125,245,212,0.22)] bg-[rgba(125,245,212,0.07)] px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">
              The review bottleneck
            </p>
            <h2 className="font-[family-name:var(--font-display)] text-[clamp(36px,6vw,82px)] font-semibold leading-[0.96] tracking-[-0.07em] text-white">
              The PR is small. The blast radius is not.
            </h2>
          </div>
        </FadeUp>

        <div className="mt-14 grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <FadeUp>
            <div className="rounded-[34px] border border-white/10 bg-white/[0.045] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
              <div className="rounded-[27px] border border-white/8 bg-[#080b0d] p-6 md:p-8">
                <div className="font-[family-name:var(--font-mono)] text-[12px] text-white/40">pull_request.diff</div>
                <div className="mt-5 space-y-3 font-[family-name:var(--font-mono)] text-sm">
                  <p className="rounded-xl border border-[rgba(255,138,154,0.15)] bg-[rgba(255,138,154,0.06)] px-4 py-3 text-[var(--danger)]">
                    {'- return user.plan === "pro"'}
                  </p>
                  <p className="rounded-xl border border-[rgba(125,245,212,0.16)] bg-[rgba(125,245,212,0.07)] px-4 py-3 text-[var(--accent-strong)]">
                    {'+ return entitlement.includes("pro")'}
                  </p>
                  <p className="rounded-xl border border-white/8 bg-white/[0.025] px-4 py-3 text-white/44">
                    {"// Looks safe in isolation"}
                  </p>
                </div>
                <div className="mt-8 rounded-2xl border border-[rgba(246,193,119,0.22)] bg-[rgba(246,193,119,0.08)] p-5">
                  <p className="text-sm font-semibold text-[var(--warning)]">Meridian opens the surrounding system.</p>
                  <p className="mt-2 text-sm leading-6 text-white/56">
                    It checks billing, webhooks, feature flags, tests, and the routes that still depend on the old contract.
                  </p>
                </div>
              </div>
            </div>
          </FadeUp>

          <div className="grid gap-5">
            {problems.map((item, index) => (
              <FadeUp key={item.title}>
                <div className="group rounded-[28px] border border-white/10 bg-white/[0.04] p-2 transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1">
                  <div className="rounded-[22px] border border-white/8 bg-[#0b0f12] p-6">
                    <div className="mb-5 flex size-10 items-center justify-center rounded-full border border-[rgba(125,245,212,0.22)] bg-[rgba(125,245,212,0.08)] font-[family-name:var(--font-mono)] text-xs text-[var(--accent)]">
                      {String(index + 1).padStart(2, "0")}
                    </div>
                    <h3 className="text-xl font-semibold tracking-[-0.03em] text-white">{item.title}</h3>
                    <p className="mt-3 max-w-[620px] text-sm leading-7 text-[var(--text-muted)]">{item.body}</p>
                  </div>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
