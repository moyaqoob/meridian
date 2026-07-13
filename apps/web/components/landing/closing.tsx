import { SignInButton } from "@/components/auth-buttons"
import { FadeUp } from "./fade-up"
import styles from "./landing.module.css"

export function LandingClosing() {
  return (
    <section className={styles.closing} id="start">
      <div className={styles.closingBg} aria-hidden />
      <div className={`${styles.wrap} ${styles.closingInner}`}>
        <FadeUp>
          <h2 className={`${styles.display} ${styles.sectionTitle}`}>
            Give your reviewers the context they do not have time to dig up.
          </h2>
        </FadeUp>
        <FadeUp>
          <p className={styles.closingLead}>
            Install Meridian on a repo in under five minutes. It stays quiet
            until it has something worth saying.
          </p>
        </FadeUp>
        <FadeUp>
          <div className={`${styles.ctaRow} ${styles.closingCta}`}>
            <SignInButton
              className={`${styles.btn} ${styles.btnSolid}`}
              label="Install on GitHub"
            />
            <a href="mailto:hello@meridian.dev" className={styles.btn}>
              Talk to us directly
            </a>
          </div>
        </FadeUp>
        <FadeUp>
          <p className={styles.closingCoord}>
            FIXED POSITION · REPO-WIDE CONTEXT · ADVISORY BY DESIGN
          </p>
        </FadeUp>
      </div>
    </section>
  )
}
