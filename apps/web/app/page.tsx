import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/app/api/auth/[...nextauth]/route"
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
import styles from "@/components/landing/landing.module.css"

export default async function Home() {
  const session = await getServerSession(authOptions)

  if (session) {
    redirect("/dashboard")
  }

  return (
    <div className={styles.page}>
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
