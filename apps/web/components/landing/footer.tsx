export function LandingFooter() {
  return (
    <footer className="border-t border-white/10 bg-[#030405] px-4 py-9">
      <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-3">
        <p className="font-[family-name:var(--font-mono)] text-[12px] uppercase tracking-[0.16em] text-[var(--text-faint)]">
          Meridian / AI code review with repo context
        </p>
        <p className="font-[family-name:var(--font-mono)] text-[12px] text-[var(--text-faint)]">
          Copyright {new Date().getFullYear()}
        </p>
      </div>
    </footer>
  )
}
