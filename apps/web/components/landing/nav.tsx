import Link from "next/link"
import { SignInButton } from "@/components/auth-buttons"

const btnClass =
  "group inline-flex cursor-pointer items-center gap-3 whitespace-nowrap rounded-full border border-[rgba(125,245,212,0.28)] bg-[rgba(125,245,212,0.1)] px-5 py-2.5 text-[13px] font-semibold tracking-[-0.01em] text-[var(--accent-strong)] no-underline transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:border-[rgba(125,245,212,0.55)] hover:bg-[rgba(125,245,212,0.16)] active:scale-[0.98]"

export function LandingNav() {
  return (
    <nav className="fixed inset-x-0 top-0 z-20 px-4 pt-5">
      <div className="mx-auto flex max-w-[1180px] items-center justify-between rounded-full border border-white/12 bg-[#080b0d]/95 px-3 py-3 shadow-[0_18px_54px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-md">
        <Link href="/" className="flex items-center gap-3 pl-3 text-[18px] font-semibold tracking-[-0.03em] text-white">
          <span
            aria-hidden
            className="relative size-7 rounded-full border border-[rgba(125,245,212,0.38)] bg-[radial-gradient(circle_at_35%_30%,rgba(166,255,231,0.95),rgba(125,245,212,0.14)_42%,rgba(255,255,255,0.04)_70%)] shadow-[0_0_32px_rgba(125,245,212,0.22)]"
          />
          <span>Meridian</span>
        </Link>
        <ul className="flex list-none gap-1 text-sm text-[var(--text-muted)] max-[820px]:hidden">
          <li>
            <a className="rounded-full px-4 py-2 transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-white/[0.06] hover:text-white" href="#how">
              How it works
            </a>
          </li>
          <li>
            <a className="rounded-full px-4 py-2 transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-white/[0.06] hover:text-white" href="#trust">
              Trust
            </a>
          </li>
          <li>
            <a className="rounded-full px-4 py-2 transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-white/[0.06] hover:text-white" href="#start">
              Start
            </a>
          </li>
        </ul>
        <SignInButton className={btnClass} label="Install on GitHub" />
      </div>
    </nav>
  )
}
