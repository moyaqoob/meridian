"use client"

import { useEffect, useRef, type ReactNode } from "react"
import styles from "./landing.module.css"

export function FadeUp({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches

    const inClass = styles.fadeUpIn
    if (!inClass) return

    if (prefersReduced) {
      node.classList.add(inClass)
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add(inClass)
          }
        }
      },
      { threshold: 0.15 },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={ref} className={styles.fadeUp}>
      {children}
    </div>
  )
}
