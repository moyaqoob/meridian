import { FadeUp } from "./fade-up"
import styles from "./landing.module.css"

/** Accent = file in the PR diff. Others = retrieved neighbors Meridian would pull in. */
const nodes = [
  { top: "48%", left: "58%", labelTop: "44%", labelLeft: "62%", label: "routers/webhook.py", accent: true },
  { top: "22%", left: "34%", labelTop: "18%", labelLeft: "37%", label: "workers/review_worker.py", accent: false },
  { top: "68%", left: "28%", labelTop: "72%", labelLeft: "30%", label: "services/retrieval.py", accent: false },
  { top: "28%", left: "78%", labelTop: "24%", labelLeft: "80%", label: "models/schemas.py", accent: false },
  { top: "74%", left: "68%", labelTop: "78%", labelLeft: "70%", label: "services/pipeline_events.py", accent: false },
]

export function LandingGraph() {
  return (
    <section className={styles.section}>
      <div className={styles.wrap}>
        <FadeUp>
          <div className={styles.sectionHead}>
            <div className={styles.sectionLabel}>
              Repo-wide context, visualized
            </div>
            <h2 className={`${styles.display} ${styles.sectionTitle}`}>
              It is not reading your file. It is reading your graph.
            </h2>
            <p className={styles.sectionBody}>
              Every symbol Meridian touches gets resolved against where else it
              is used, before a single comment gets written.
            </p>
          </div>
        </FadeUp>
        <FadeUp>
          <div className={styles.graphVisual}>
            <div className={styles.graphDots} aria-hidden />
            <div className={styles.graphNodes}>
              {nodes.map((node) => (
                <div key={node.label}>
                  <div
                    className={
                      node.accent
                        ? `${styles.gnode} ${styles.gnodeAccent}`
                        : styles.gnode
                    }
                    style={{ top: node.top, left: node.left }}
                  />
                  <div
                    className={styles.glabel}
                    style={{ top: node.labelTop, left: node.labelLeft }}
                  >
                    {node.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </FadeUp>
      </div>
    </section>
  )
}
