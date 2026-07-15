import { FadeUp } from "./fade-up"

const controls = [
  ["Custom rules", "Write your review standards in plain English and attach them to repos or paths."],
  ["Confidence gate", "Findings need evidence, line references, and enough certainty to be useful."],
  ["Advisory mode", "Meridian comments in the PR. Your humans still own the merge decision."],
  ["Repo memory", "The reviewer learns repeated patterns from your codebase instead of starting cold."],
]

export function LandingTrust() {
  return (
    <section id="trust" className="relative px-4 py-24 md:py-36">
      <div className="mx-auto max-w-[1180px]">
        <FadeUp>
          <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
            <div>
              <p className="mb-5 inline-flex rounded-full border border-[rgba(125,245,212,0.22)] bg-[rgba(125,245,212,0.07)] px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">
                Trust and control
              </p>
              <h2 className="font-[family-name:var(--font-display)] text-[clamp(36px,6vw,82px)] font-semibold leading-[0.96] tracking-[-0.07em] text-white">
                Powerful review. No loud autopilot.
              </h2>
            </div>
            <p className="max-w-[560px] text-lg leading-8 text-[var(--text-muted)]">
              The fastest way to lose trust in an automated reviewer is to make it noisy or make it a gate. Meridian is designed to be precise first.
            </p>
          </div>
        </FadeUp>

        <div className="mt-14 grid gap-5 lg:grid-cols-4">
          {controls.map(([title, body], index) => (
            <FadeUp key={title}>
              <div
                className={`rounded-[30px] border border-white/10 bg-white/[0.045] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] ${
                  index === 0 || index === 3 ? "lg:translate-y-8" : ""
                }`}
              >
                <div className="min-h-[240px] rounded-[23px] border border-white/8 bg-[#0b0f12] p-6">
                  <div className="mb-8 h-12 rounded-2xl border border-[rgba(125,245,212,0.16)] bg-[linear-gradient(90deg,rgba(125,245,212,0.12),rgba(255,255,255,0.02))]" />
                  <h3 className="text-xl font-semibold tracking-[-0.03em] text-white">{title}</h3>
                  <p className="mt-4 text-sm leading-7 text-[var(--text-muted)]">{body}</p>
                </div>
              </div>
            </FadeUp>
          ))}
        </div>

        <FadeUp>
          <div className="mt-20 rounded-[34px] border border-[rgba(125,245,212,0.18)] bg-[rgba(125,245,212,0.055)] p-2">
            <div className="rounded-[27px] border border-white/8 bg-[#080b0d] p-6 md:p-8">
              <p className="font-[family-name:var(--font-mono)] text-[12px] uppercase tracking-[0.18em] text-[var(--accent)]">
                Prototype status
              </p>
              <p className="mt-4 max-w-[900px] text-lg leading-8 text-[var(--text-muted)]">
                The current product experience uses hardcoded repo and review examples while the backend integrations mature. The landing page now sells the real direction: full-context AI review for GitHub teams.
              </p>
            </div>
          </div>
        </FadeUp>
      </div>
    </section>
  )
}
