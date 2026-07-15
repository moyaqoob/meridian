import { redirect } from "next/navigation"
import { getSession } from "@/lib/auth/session"
import {
  LandingClosing,
  LandingFooter,
  LandingGraph,
  LandingHero,
  LandingMarquee,
  LandingNav,
  LandingPipeline,
  LandingProblem,
  LandingStats,
  LandingTrust,
} from "@/components/landing"

export default async function Home() {
  const session = await getSession()

  if (session.authenticated) {
    redirect("/dashboard")
  }

  return (
    <div className="relative min-h-dvh overflow-x-clip bg-[radial-gradient(ellipse_70%_48%_at_72%_0%,rgba(125,245,212,0.1),transparent_56%),radial-gradient(ellipse_42%_34%_at_10%_14%,rgba(246,193,119,0.06),transparent_50%),linear-gradient(180deg,#050607_0%,#080b0d_42%,#050607_100%)] text-[var(--text)]">
      <div className="landing-noise" aria-hidden />
      <LandingNav />
      <LandingHero />
      <LandingMarquee />
      <LandingStats />
      <LandingProblem />
      <LandingGraph />
      <LandingPipeline />
      <LandingTrust />
      <LandingClosing />
      <LandingFooter />
    </div>
  )
}
