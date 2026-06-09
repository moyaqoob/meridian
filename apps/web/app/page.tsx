import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/app/api/auth/[...nextauth]/route"
import { SignInButton } from "@/components/auth-buttons"
import styles from "./page.module.css"

export default async function Home() {
  const session = await getServerSession(authOptions)

  if (session) {
    redirect("/dashboard")
  }

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <span className={styles.logo}>Meridian</span>
        <div className={styles.navCta}>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" className={styles.navLink}>
            GitHub
          </a>
        </div>
      </nav>

      <main className={styles.hero}>
        <div className={styles.heroContent}>
          <h1 className={styles.title}>
            Build the future
          </h1>
          <p className={styles.subtitle}>
            The modern platform for developers to build, ship, and scale.
            Simple. Fast. Reliable.
          </p>
          <div className={styles.cta}>
            <SignInButton />
          </div>
        </div>
      </main>

      <footer className={styles.footer}>
        <p>© {new Date().getFullYear()} Meridian. All rights reserved.</p>
      </footer>
    </div>
  )
}
