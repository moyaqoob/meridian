import { FadeUp } from "./fade-up"
import styles from "./landing.module.css"

const cells = [
  {
    title: "Advisory, not blocking",
    body: "Meridian comments on the PR. It does not hold your merge button hostage.",
  },
  {
    title: "Confidence-gated",
    body: "It only posts findings it can point to a specific call site or dependency for.",
  },
  {
    title: "Fits your PR flow",
    body: "No new dashboard. Comments land where your team already reads them.",
  },
]

export function LandingTrust() {
  return (
    <section id="trust" className={styles.section}>
      <div className={styles.wrap}>
        <FadeUp>
          <div className={styles.sectionHead}>
            <div className={styles.sectionLabel}>Trust &amp; control</div>
            <h2 className={`${styles.display} ${styles.sectionTitle}`}>
              It advises. Your team still decides.
            </h2>
            <p className={styles.sectionBody}>
              The fastest way to lose a team&apos;s trust in an automated
              reviewer is to make it loud, or make it a gate. Meridian is built
              to be neither by default.
            </p>
          </div>
        </FadeUp>
        <FadeUp>
          <div className={styles.trustGrid}>
            {cells.map((cell) => (
              <div key={cell.title} className={styles.trustCell}>
                <span className={styles.trustMark} aria-hidden>
                  →
                </span>
                <h3>{cell.title}</h3>
                <p>{cell.body}</p>
              </div>
            ))}
          </div>
        </FadeUp>
        <FadeUp>
          <div className={styles.honestNote}>
            <strong>Where we are today:</strong> Meridian is in active
            development on GitHub repos with an event-driven pipeline. Formal
            data-handling and hosting documentation is on the roadmap, not yet
            published. If that is a blocker for your org, reach out and we will
            tell you honestly where it stands.
          </div>
        </FadeUp>
      </div>
    </section>
  )
}
