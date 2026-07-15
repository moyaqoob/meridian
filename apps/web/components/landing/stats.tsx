import { FadeUp } from "./fade-up"

const stats = [
  ["91%", "prototype confidence gate"],
  ["19", "references traced before comment"],
  ["4", "review agents in the pipeline"],
  ["0", "new workflow steps for your team"],
]

export function LandingStats() {
  return (
    <section className="relative px-4 py-24 md:py-32">
      <div className="mx-auto max-w-[1180px]">
        <FadeUp>
          <div className="grid gap-5 md:grid-cols-4">
            {stats.map(([value, label], index) => (
              <div
                key={label}
                className={`rounded-[28px] border border-white/10 bg-white/[0.045] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] ${
                  index === 1 ? "md:-translate-y-6" : index === 2 ? "md:translate-y-8" : ""
                }`}
              >
                <div className="rounded-[22px] border border-white/8 bg-[#080b0d] px-6 py-7">
                  <div className="font-[family-name:var(--font-display)] text-[clamp(38px,5vw,70px)] font-semibold leading-none tracking-[-0.07em] text-white">
                    {value}
                  </div>
                  <p className="mt-4 max-w-[180px] text-sm leading-6 text-[var(--text-muted)]">{label}</p>
                </div>
              </div>
            ))}
          </div>
        </FadeUp>
      </div>
    </section>
  )
}
