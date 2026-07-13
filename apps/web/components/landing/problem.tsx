import { FadeUp } from "./fade-up"
import styles from "./landing.module.css"

export function LandingProblem() {
  return (
    <section className={styles.section}>
      <div className={styles.wrap}>
        <FadeUp>
          <div className={styles.sectionHead}>
            <div className={styles.sectionLabel}>
              The problem with diff-only review
            </div>
            <h2 className={`${styles.display} ${styles.sectionTitle}`}>
              A PR diff shows you what changed. It does not show you what
              breaks.
            </h2>
            <p className={styles.sectionBody}>
              Most review tools reason about the eight lines in front of them,
              with no memory of the other forty places those lines are depended
              on. That is not a review, it is a spellcheck.
            </p>
          </div>
        </FadeUp>
        <FadeUp>
          <div className={styles.problemGrid}>
            <div className={`${styles.problemCell} ${styles.problemBad}`}>
              <h3>Diff-only</h3>
              <p>
                Sees the function you changed. Approves it because it is
                internally consistent. Has no idea it is called from a webhook
                handler three directories away that now silently breaks.
              </p>
            </div>
            <div className={`${styles.problemCell} ${styles.problemGood}`}>
              <h3>Meridian</h3>
              <p>
                Pulls the call graph before it comments. Flags what actually
                depends on what changed, and says nothing when nothing does.
                Signal, not noise.
              </p>
            </div>
          </div>
        </FadeUp>
      </div>
    </section>
  )
}
