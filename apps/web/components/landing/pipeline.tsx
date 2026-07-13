import { FadeUp } from "./fade-up"
import styles from "./landing.module.css"

const steps = [
  {
    num: "01",
    title: "PR opens",
    body: "Meridian picks up the event the moment a pull request is opened or updated. No polling, no manual trigger.",
  },
  {
    num: "02",
    title: "Context retrieval",
    body: "It resolves what the changed symbols touch across the repo: callers, dependents, adjacent tests.",
  },
  {
    num: "03",
    title: "Reasoning",
    body: "It weighs what it found against the actual change, and drops anything it cannot defend with a specific line reference.",
  },
  {
    num: "04",
    title: "Comment or silence",
    body: "High-confidence findings post as PR comments. Everything else is discarded.",
  },
]

export function LandingPipeline() {
  return (
    <section id="how" className={styles.section}>
      <div className={styles.wrap}>
        <FadeUp>
          <div className={styles.sectionHead}>
            <div className={styles.sectionLabel}>How it reasons</div>
            <h2 className={`${styles.display} ${styles.sectionTitle}`}>
              Four steps, every time a PR opens.
            </h2>
            <p className={styles.sectionBody}>
              No new workflow to learn. It lives in the PR you already have
              open.
            </p>
          </div>
        </FadeUp>
        <FadeUp>
          <div className={styles.pipeline}>
            {steps.map((step) => (
              <div key={step.num} className={styles.pipeStep}>
                <span className={styles.pipeNum}>{step.num}</span>
                <div className={styles.pipeConnector} aria-hidden />
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            ))}
          </div>
        </FadeUp>
      </div>
    </section>
  )
}
