import { SignInButton } from "@/components/auth-buttons"
import { FadeUp } from "./fade-up"
import styles from "./landing.module.css"

export function LandingHero() {
  return (
    <header className={styles.hero}>
      <div className={styles.heroGridBg} aria-hidden />
      <div className={styles.heroGlow} aria-hidden />
      <div className={`${styles.wrap} ${styles.heroInner}`}>
        <div className={styles.eyebrow}>
          <span className={styles.eyebrowDot} aria-hidden />
          Now reviewing PRs against full repo context
        </div>
        <h1 className={`${styles.display} ${styles.title}`}>
          Code review that reads the{" "}
          <em className={styles.titleEm}>whole map,</em>
          <br />
          not just the diff.
        </h1>
        <p className={styles.lede}>
          Meridian traces every change through the repo it actually lives in:
          call sites, dependents, and the code your reviewers did not have time
          to reopen. It comments where it is sure. It stays quiet everywhere
          else.
        </p>
        <div className={styles.ctaRow}>
          <SignInButton
            className={`${styles.btn} ${styles.btnSolid}`}
            label="Install on GitHub"
          />
          <a href="#how" className={styles.btn}>
            See how it reasons
          </a>
        </div>
        <p className={styles.ctaNote}>
          Advisory by default. Your team merges. Meridian just makes sure you
          are not blind.
        </p>

        <FadeUp>
          <div className={styles.heroArtifact}>
            <div className={styles.artifactHead}>
              <div className={styles.artifactHeadLeft}>
                <span className={styles.artifactAvatar} aria-hidden />
                meridian-bot commented on{" "}
                <strong style={{ color: "var(--text-muted)" }}>
                  payments/charge.ts
                </strong>
              </div>
              <span className={styles.artifactTag}>repo-context</span>
            </div>
            <div className={styles.artifactBody}>
              <p className={styles.artifactStrong}>
                This changes the return shape of{" "}
                <span className={styles.mono} style={{ color: "var(--accent)" }}>
                  calculateFee()
                </span>
                .
              </p>
              <div className={styles.codeRef}>
                - return <span className={styles.fn}>fee</span>: number
                <br />+ return {"{ "}
                <span className={styles.fn}>fee</span>: number, breakdown:
                FeeBreakdown {"}"}
              </div>
              <p>
                Not a problem in this file, but{" "}
                <span className={styles.mono} style={{ color: "var(--text)" }}>
                  calculateFee
                </span>{" "}
                is called in 4 other places, and 2 destructure the old shape
                directly. Those fail silently at runtime, not at the type layer.
              </p>
              <div className={styles.callSites}>
                <span className={styles.callSite}>invoices/generate.ts:88</span>
                <span className={styles.callSite}>billing/webhook.ts:41</span>
                <span className={styles.callSite}>+ 2 more, unaffected</span>
              </div>
            </div>
          </div>
        </FadeUp>
      </div>
    </header>
  )
}
