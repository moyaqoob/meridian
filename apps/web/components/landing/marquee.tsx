import styles from "./landing.module.css"

const rowA = [
  "TypeScript",
  "Python",
  "Go",
  "Rust",
  "Java",
  "GitHub",
]

const rowB = [
  "Monorepos",
  "Microservices",
  "REST",
  "GraphQL",
  "Event pipelines",
  "SQL & NoSQL",
]

function Track({ items }: { items: string[] }) {
  return (
    <div className={styles.marqueeTrack}>
      {[...items, ...items].map((item, index) => (
        <span key={`${item}-${index}`}>{item}</span>
      ))}
    </div>
  )
}

export function LandingMarquee() {
  return (
    <div className={styles.marqueeSection}>
      <p className={styles.marqueeLabel}>Reads context across</p>
      <div className={`${styles.marqueeRow} ${styles.marqueeLeft}`}>
        <Track items={rowA} />
      </div>
      <div className={`${styles.marqueeRow} ${styles.marqueeRight}`}>
        <Track items={rowB} />
      </div>
    </div>
  )
}
