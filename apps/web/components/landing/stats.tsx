import { FadeUp } from "./fade-up"
import styles from "./landing.module.css"

export function LandingStats() {
  return (
    <section className={styles.section}>
      <div className={styles.wrap}>
        <FadeUp>
          <div className={styles.sectionHead}>
            <div className={styles.sectionLabel}>Where Meridian is today</div>
            <h2 className={`${styles.display} ${styles.sectionTitle}`}>
              Early, and honest about it.
            </h2>
            <p className={styles.sectionBody}>
              Meridian is in active development against real repos. These are
              the numbers we are building toward measuring publicly, filled in
              as they are real, not before.
            </p>
          </div>
        </FadeUp>
        <FadeUp>
          <div className={styles.statGrid}>
            <div className={styles.statCell}>
              <div className={`${styles.statNum} ${styles.statNumPlaceholder}`}>
                [ TBD ]
              </div>
              <div className={styles.statLabel}>
                PRs reviewed in active testing
              </div>
            </div>
            <div className={styles.statCell}>
              <div className={`${styles.statNum} ${styles.statNumPlaceholder}`}>
                [ TBD ]
              </div>
              <div className={styles.statLabel}>
                Cross-file issues caught pre-merge
              </div>
            </div>
            <div className={styles.statCell}>
              <div className={styles.statNum}>&lt; 5 min</div>
              <div className={styles.statLabel}>To install on a new repo</div>
            </div>
            <div className={styles.statCell}>
              <div className={styles.statNum}>0</div>
              <div className={styles.statLabel}>
                Workflow changes required
              </div>
            </div>
          </div>
        </FadeUp>
        <p className={styles.statNote}>
          {"// Replace [TBD] once you have real numbers from repos you've tested on."}
        </p>
      </div>
    </section>
  )
}
