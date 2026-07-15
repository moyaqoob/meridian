import { SignInButton } from "@/components/auth-buttons"
import { FadeUp } from "./fade-up"

const primaryButton =
  "group inline-flex cursor-pointer items-center gap-4 whitespace-nowrap rounded-full bg-[var(--accent)] py-2.5 pl-5 pr-2 text-sm font-semibold text-[#03100d] shadow-[0_18px_60px_rgba(125,245,212,0.2)] transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-[var(--accent-strong)] active:scale-[0.98]"

const secondaryButton =
  "group inline-flex cursor-pointer items-center gap-4 whitespace-nowrap rounded-full border border-white/12 bg-white/[0.04] py-2.5 pl-5 pr-2 text-sm font-semibold text-white transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:border-white/22 hover:bg-white/[0.075] active:scale-[0.98]"

export function LandingClosing() {
  return (
    <section id="start" className="relative overflow-hidden px-4 py-24 pb-28 md:py-36">
      <div
        aria-hidden
        className="absolute left-1/2 top-1/2 h-[440px] w-[min(86vw,760px)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(125,245,212,0.08),transparent_68%)] blur-xl"
      />
      <div className="relative mx-auto max-w-[1180px] rounded-[42px] border border-white/10 bg-white/[0.045] p-2 shadow-[0_44px_140px_rgba(0,0,0,0.45),inset_0_1px_0_rgba(255,255,255,0.08)]">
        <div className="overflow-hidden rounded-[34px] border border-white/8 bg-[#080b0d] px-6 py-16 text-center md:px-12 md:py-24">
          <FadeUp>
            <p className="mx-auto mb-6 inline-flex rounded-full border border-[rgba(125,245,212,0.22)] bg-[rgba(125,245,212,0.07)] px-3 py-1.5 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]">
              Start with one repo
            </p>
          </FadeUp>
          <FadeUp>
            <h2 className="mx-auto max-w-[900px] font-[family-name:var(--font-display)] text-[clamp(42px,7vw,96px)] font-semibold leading-[0.92] tracking-[-0.075em] text-white">
              Give every PR a reviewer that remembers the whole system.
            </h2>
          </FadeUp>
          <FadeUp>
            <p className="mx-auto mt-7 max-w-[620px] text-lg leading-8 text-[var(--text-muted)]">
              Install Meridian, pick a repo, and watch the prototype review experience come alive with realistic examples.
            </p>
          </FadeUp>
          <FadeUp>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <SignInButton className={primaryButton} label="Install on GitHub">
                <span>Install on GitHub</span>
                <span className="flex size-8 items-center justify-center rounded-full bg-[#03100d]/10 transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-1 group-hover:-translate-y-0.5">
                  <span aria-hidden>&gt;</span>
                </span>
              </SignInButton>
              <a href="mailto:hello@meridian.dev" className={secondaryButton}>
                <span>Talk to the builder</span>
                <span className="flex size-8 items-center justify-center rounded-full bg-white/[0.08] transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-1 group-hover:-translate-y-0.5">
                  <span aria-hidden>&gt;</span>
                </span>
              </a>
            </div>
          </FadeUp>
        </div>
      </div>
    </section>
  )
}
