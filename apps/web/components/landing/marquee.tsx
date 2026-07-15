const rowA = ["GitHub", "TypeScript", "Python", "Go", "Rust", "GraphQL", "Postgres", "CI pipelines"]
const rowB = ["Call graph", "AST context", "Risk ranking", "Custom rules", "Test gaps", "Security paths", "Review memory"]

function Track({ items }: { items: string[] }) {
  return (
    <div className="flex whitespace-nowrap">
      {[...items, ...items].map((item, index) => (
        <span
          key={`${item}-${index}`}
          className="flex items-center gap-7 px-7 font-[family-name:var(--font-mono)] text-[14px] text-[var(--text-muted)] after:text-[var(--accent-dim)] after:content-['/']"
        >
          {item}
        </span>
      ))}
    </div>
  )
}

export function LandingMarquee() {
  return (
    <div className="relative z-10 overflow-hidden border-y border-white/10 bg-[#07090b] py-8">
      <p className="mb-5 text-center font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.18em] text-[var(--text-faint)]">
        Context sources wired into every review pass
      </p>
      <div className="flex w-[200%] animate-scroll-left motion-reduce:animate-none">
        <Track items={rowA} />
      </div>
      <div className="mt-4 flex w-[200%] animate-scroll-right motion-reduce:animate-none">
        <Track items={rowB} />
      </div>
    </div>
  )
}
