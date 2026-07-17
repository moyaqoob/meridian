import { SignInButton } from "@/components/auth-buttons"
import { FadeUp } from "./fade-up"

const primaryButton =
  "group inline-flex cursor-pointer items-center gap-4 whitespace-nowrap rounded-full bg-[var(--accent)] py-2.5 pl-5 pr-2 text-sm font-semibold text-[#03100d] shadow-[0_18px_60px_rgba(125,245,212,0.2)] transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-[var(--accent-strong)] active:scale-[0.98]"

const secondaryButton =
  "group inline-flex cursor-pointer items-center gap-4 whitespace-nowrap rounded-full border border-white/12 bg-white/[0.04] py-2.5 pl-5 pr-2 text-sm font-semibold text-white transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:border-white/22 hover:bg-white/[0.075] active:scale-[0.98]"

const reviewRows = [
  ["critical", "billing/webhook.ts", "Return shape breaks async retry handler"],
  ["medium", "auth/session.ts", "Fallback path bypasses backend outage signal"],
  ["low", "ui/review-panel.tsx", "Duplicate empty state copy across branches"],
]

const diffRows = [
  "-  const fee = calculateFee(invoice)",
  "+  const { fee, breakdown } = calculateFee(invoice)",
  "+  await auditTrail.write({ fee, breakdown })",
  "   return capturePayment({ fee })",
]

const proofPoints = [
  ["Graph first", "Callers, contracts, and tests before comments"],
  ["Noise gated", "Only evidence-backed findings reach the PR"],
  ["Review native", "Works where your team already merges code"],
]

export function LandingHero() {
  return (
    <header className="relative overflow-hidden px-4 pt-32 md:pt-36">
      <div
        aria-hidden
        className="absolute left-1/2 top-20 h-[520px] w-[min(88vw,1040px)] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(125,245,212,0.1),transparent_64%)] blur-xl"
      />
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-[740px] opacity-25 [background-image:linear-gradient(rgba(125,245,212,0.12)_1px,transparent_1px),linear-gradient(90deg,rgba(125,245,212,0.1)_1px,transparent_1px)] [background-size:72px_72px] [mask-image:radial-gradient(ellipse_760px_520px_at_55%_18%,black,transparent_74%)]"
      />

      <div className="relative mx-auto grid max-w-[1360px] items-center gap-12 pb-24 lg:grid-cols-[0.88fr_1.12fr] lg:pb-32">
        <div className="max-w-[720px]">
          <FadeUp>
            <div className="mb-6 inline-flex items-center gap-3 rounded-full border border-[rgba(125,245,212,0.24)] bg-[rgba(125,245,212,0.08)] px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.18em] text-[var(--accent-strong)]">
              <span className="size-1.5 rounded-full bg-[var(--accent)] shadow-[0_0_18px_rgba(125,245,212,0.8)]" />
              AI reviewer for codebases that move fast
            </div>
          </FadeUp>

          <FadeUp>
            <h1 className="font-[family-name:var(--font-display)] text-[clamp(48px,7vw,104px)] font-semibold leading-[0.9] tracking-[-0.07em] text-white">
              Review the blast radius before it ships.
            </h1>
          </FadeUp>

          <FadeUp>
            <p className="mt-7 max-w-[610px] text-[18px] leading-8 text-[var(--text-muted)] md:text-[20px]">
              Meridian reads the PR, traces the code graph, ranks the risk, and comments only when it can prove the issue with repo context.
            </p>
          </FadeUp>

          <FadeUp>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <SignInButton className={primaryButton} label="Install on GitHub">
                <span>Install on GitHub</span>
                <span className="flex size-8 items-center justify-center rounded-full bg-[#03100d]/10 transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-1 group-hover:-translate-y-0.5">
                  <span aria-hidden>&gt;</span>
                </span>
              </SignInButton>
              <a href="#how" className={secondaryButton}>
                <span>Watch the review path</span>
                <span className="flex size-8 items-center justify-center rounded-full bg-white/[0.08] transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-1 group-hover:-translate-y-0.5">
                  <span aria-hidden>v</span>
                </span>
              </a>
            </div>
          </FadeUp>

          <FadeUp>
            <div className="mt-10 grid max-w-[680px] gap-3 sm:grid-cols-3">
              {proofPoints.map(([label, body]) => (
                <div
                  key={label}
                  className="rounded-2xl border border-white/10 bg-[#0b0f12]/90 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
                >
                  <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-[var(--accent)]">
                    {label}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-white/68">{body}</p>
                </div>
              ))}
            </div>
          </FadeUp>
        </div>

        <FadeUp>
          <div className="relative min-h-[620px] lg:min-h-[680px]">
            <div
              aria-hidden
              className="absolute right-4 top-4 h-[88%] w-[80%] rounded-[36px] border border-[rgba(125,245,212,0.12)] bg-[linear-gradient(135deg,rgba(125,245,212,0.08),transparent_34%),rgba(255,255,255,0.025)] shadow-[0_0_90px_rgba(125,245,212,0.08)]"
            />
            <div className="relative rounded-[34px] border border-white/12 bg-white/[0.04] p-2 shadow-[0_30px_86px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.12)] [animation:meridian-float_7s_var(--ease-premium)_infinite]">
              <div className="overflow-hidden rounded-[27px] border border-white/12 bg-[#080b0d] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
                <div className="flex items-center justify-between border-b border-white/10 bg-[#0d1115] px-5 py-4">
                  <div>
                    <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.16em] text-[var(--accent)]">
                      Meridian review cockpit
                    </p>
                    <p className="mt-1 text-sm text-white/62">yaqoob/meridian / PR #184</p>
                  </div>
                  <div className="rounded-full border border-[rgba(125,245,212,0.24)] bg-[rgba(125,245,212,0.1)] px-3 py-1 font-[family-name:var(--font-mono)] text-[11px] text-[var(--accent-strong)]">
                    live scan
                  </div>
                </div>

                <div className="grid min-h-[500px] grid-cols-1 lg:grid-cols-[1.05fr_0.95fr]">
                  <div className="relative border-b border-white/10 bg-[#07090b] p-5 lg:border-b-0 lg:border-r">
                    <div className="absolute inset-x-5 top-20 h-px overflow-hidden bg-white/10">
                      <span className="block h-px w-2/3 bg-[linear-gradient(90deg,transparent,var(--accent),transparent)] [animation:meridian-scan_4s_var(--ease-premium)_infinite]" />
                    </div>
                    <div className="mb-4 flex items-center justify-between">
                      <p className="font-[family-name:var(--font-mono)] text-[12px] text-white/58">diff</p>
                      <p className="font-[family-name:var(--font-mono)] text-[12px] text-[var(--accent)]">7 files</p>
                    </div>
                    <div className="space-y-2 font-[family-name:var(--font-mono)] text-[12px] leading-6">
                      {diffRows.map((row) => (
                        <div
                          key={row}
                          className={`rounded-xl border px-3 py-2 ${row.startsWith("+")
                              ? "border-[rgba(125,245,212,0.16)] bg-[rgba(125,245,212,0.07)] text-[var(--accent-strong)]"
                              : row.startsWith("-")
                                ? "border-[rgba(255,138,154,0.16)] bg-[rgba(255,138,154,0.07)] text-[var(--danger)]"
                                : "border-white/10 bg-white/[0.035] text-white/62"
                            }`}
                        >
                          {row}
                        </div>
                      ))}
                    </div>

                    <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                      <div className="mb-3 flex items-center justify-between">
                        <p className="text-sm font-semibold text-white">Context graph</p>
                        <p className="font-[family-name:var(--font-mono)] text-[11px] text-white/55">19 references</p>
                      </div>
                      <div className="relative h-44 overflow-hidden rounded-xl bg-[#050607]">
                        <div className="absolute left-[18%] top-[24%] h-px w-[48%] origin-left rotate-[19deg] bg-[linear-gradient(90deg,rgba(125,245,212,0.12),rgba(125,245,212,0.62),rgba(125,245,212,0.08))]" />
                        <div className="absolute left-[24%] top-[68%] h-px w-[42%] origin-left -rotate-[24deg] bg-[linear-gradient(90deg,rgba(125,245,212,0.08),rgba(125,245,212,0.5),rgba(125,245,212,0.08))]" />
                        <div className="absolute left-[50%] top-[22%] h-px w-[30%] origin-left rotate-[42deg] bg-[linear-gradient(90deg,rgba(246,193,119,0.08),rgba(246,193,119,0.54),rgba(246,193,119,0.05))]" />
                        {["api", "fees", "webhook", "tests", "audit"].map((node, index) => (
                          <span
                            key={node}
                            className="absolute rounded-full border border-[rgba(125,245,212,0.24)] bg-[rgba(125,245,212,0.09)] px-3 py-1 font-[family-name:var(--font-mono)] text-[11px] text-[var(--accent-strong)] shadow-[0_0_28px_rgba(125,245,212,0.08)]"
                            style={{
                              left: ["10%", "54%", "24%", "64%", "42%"][index],
                              top: ["18%", "30%", "64%", "70%", "45%"][index],
                              animation: `meridian-pulse ${3 + index * 0.34}s var(--ease-premium) infinite`,
                            }}
                          >
                            {node}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="bg-[#0b0f12] p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <p className="font-[family-name:var(--font-mono)] text-[12px] text-white/58">findings</p>
                      <p className="font-[family-name:var(--font-mono)] text-[12px] text-[var(--accent)]">confidence 91%</p>
                    </div>
                    <div className="space-y-3">
                      {reviewRows.map(([level, file, title], index) => (
                        <div
                          key={title}
                          className="rounded-2xl border border-white/10 bg-white/[0.035] p-4 transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1"
                          style={{ animation: `meridian-rise ${5 + index * 0.55}s var(--ease-premium) infinite` }}
                        >
                          <div className="mb-3 flex items-center justify-between gap-3">
                            <span
                              className={`rounded-full px-2 py-1 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.12em] ${level === "critical"
                                  ? "bg-[rgba(255,138,154,0.12)] text-[var(--danger)]"
                                  : level === "medium"
                                    ? "bg-[rgba(246,193,119,0.12)] text-[var(--warning)]"
                                    : "bg-[rgba(125,245,212,0.1)] text-[var(--accent)]"
                                }`}
                            >
                              {level}
                            </span>
                            <span className="truncate font-[family-name:var(--font-mono)] text-[11px] text-white/52">
                              {file}
                            </span>
                          </div>
                          <p className="text-sm font-semibold leading-5 text-white">{title}</p>
                          <p className="mt-2 text-sm leading-6 text-white/65">
                            Cited against 4 call sites and 2 adjacent tests before comment draft.
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </FadeUp>
      </div>
    </header>
  )
}
