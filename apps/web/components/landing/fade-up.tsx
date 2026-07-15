"use client"

import { useEffect, useRef, type ReactNode } from "react"

const FADE_UP_IN =
  "opacity-100 translate-y-0 transition-[opacity,transform] duration-900 ease-[cubic-bezier(0.32,0.72,0,1)]"

export function FadeUp({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches

    if (prefersReduced) {
      node.classList.add(...FADE_UP_IN.split(" "))
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add(...FADE_UP_IN.split(" "))
          }
        }
      },
      { threshold: 0.15 },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className="translate-y-8 opacity-0 transition-[opacity,transform] duration-900 ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:translate-y-0 motion-reduce:opacity-100 motion-reduce:transition-none"
    >
      {children}
    </div>
  )
}
