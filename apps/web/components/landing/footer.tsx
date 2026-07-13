import styles from "./landing.module.css"

export function LandingFooter() {
  return (
    <footer className={styles.footer}>
      <div className={`${styles.wrap} ${styles.footerInner}`}>
        <p>MERIDIAN - REFERENCE LINE FOR YOUR CODEBASE</p>
        <p>© {new Date().getFullYear()}</p>
      </div>
    </footer>
  )
}
