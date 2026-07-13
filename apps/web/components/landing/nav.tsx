import { SignInButton } from "@/components/auth-buttons"
import styles from "./landing.module.css"

export function LandingNav() {
  return (
    <nav className={styles.nav}>
      <div className={`${styles.wrap} ${styles.navInner}`}>
        <a href="/" className={styles.logo}>
          <span className={styles.logoMark} aria-hidden />
          <span>Meridian</span>
        </a>
        <ul className={styles.navList}>
          <li>
            <a href="#how">How it works</a>
          </li>
          <li>
            <a href="#trust">Trust &amp; control</a>
          </li>
          <li>
            <a href="#start">Get started</a>
          </li>
        </ul>
        <SignInButton className={styles.btn} label="Install on GitHub" />
      </div>
    </nav>
  )
}
