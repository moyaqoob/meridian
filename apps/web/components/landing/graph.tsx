import { FadeUp } from "./fade-up"

const nodes = [
  ["changed file", "charge.ts", "12%", "44%"],
  ["caller", "invoice.ts", "44%", "18%"],
  ["side effect", "webhook.ts", "58%", "56%"],
  ["test gap", "fees.spec.ts", "24%", "72%"],
  ["schema", "billing.ts", "76%", "28%"],
]

export function LandingGraph() {
  return (
    <section className="relative px-4 py-24 md:py-36">
      <div className="mx-auto max-w-[1180px]">
        <FadeUp>
          <div className="mx-auto max-w-[820px] text-center">
            <p className="mb-5 inline-flex rounded-full border border-[rgba(125,245,212,0.22)] bg-[rgba(125,245,212,0.07)] px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">
              Repo-wide context
            </p>
            <h2 className="font-[family-name:var(--font-display)] text-[clamp(36px,6vw,82px)] font-semibold leading-[0.96] tracking-[-0.07em] text-white">
              It reads the graph before it writes the comment.
            </h2>
          </div>
        </FadeUp>

        <FadeUp>
          <div className="mt-14 rounded-[38px] border border-white/10 bg-white/[0.045] p-2 shadow-[0_36px_120px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.08)]">
            <div className="relative min-h-[560px] overflow-hidden rounded-[30px] border border-white/8 bg-[#07090b]">
              <div
                aria-hidden
                className="absolute inset-0 opacity-35 [background-image:radial-gradient(rgba(125,245,212,0.38)_1px,transparent_1.4px)] [background-size:18px_18px] [mask-image:radial-gradient(ellipse_620px_340px_at_52%_46%,black,transparent_75%)]"
              />
              <div className="absolute left-[18%] top-[46%] h-px w-[34%] origin-left -rotate-[34deg] bg-[linear-gradient(90deg,transparent,rgba(125,245,212,0.66),transparent)]" />
              <div className="absolute left-[18%] top-[47%] h-px w-[45%] origin-left rotate-[12deg] bg-[linear-gradient(90deg,transparent,rgba(125,245,212,0.62),transparent)]" />
              <div className="absolute left-[18%] top-[47%] h-px w-[30%] origin-left rotate-[44deg] bg-[linear-gradient(90deg,transparent,rgba(246,193,119,0.58),transparent)]" />
              <div className="absolute left-[60%] top-[56%] h-px w-[22%] origin-left -rotate-[47deg] bg-[linear-gradient(90deg,transparent,rgba(125,245,212,0.52),transparent)]" />

              {nodes.map(([kind, file, left, top], index) => (
                <div
                  key={file}
                  className="absolute w-[180px] rounded-2xl border border-white/10 bg-[#0c1013]/95 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.08)] transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-2"
                  style={{
                    left,
                    top,
                    animation: `meridian-rise ${5.6 + index * 0.42}s var(--ease-premium) infinite`,
                  }}
                >
                  <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.14em] text-[var(--accent)]">
                    {kind}
                  </p>
                  <p className="mt-2 truncate font-[family-name:var(--font-mono)] text-sm text-white">{file}</p>
                </div>
              ))}

              <div className="absolute bottom-5 left-5 right-5 grid gap-3 md:grid-cols-3">
                {["AST references", "Semantic search", "Review memory"].map((label) => (
                  <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
                    <p className="font-[family-name:var(--font-mono)] text-[11px] text-white/42">{label}</p>
                    <p className="mt-1 text-sm text-white">attached to every finding</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </FadeUp>
      </div>
    </section>
  )
}
