import type { DiffLine, DiffLineType } from "@/lib/api/types"

function lineType(raw: string): DiffLineType {
  if (raw.startsWith("+++") || raw.startsWith("---") || raw.startsWith("diff ") || raw.startsWith("index ")) {
    return "meta"
  }
  if (raw.startsWith("@@")) return "ctx"
  if (raw.startsWith("+")) return "add"
  if (raw.startsWith("-")) return "del"
  return "same"
}

/**
 * Parse a unified diff into display rows.
 * Line numbers track old/new sides; meta/hunk headers have none.
 */
export function parseUnifiedDiff(diff: string): DiffLine[] {
  if (!diff.trim()) return []

  const lines: DiffLine[] = []
  let oldLine: number | null = null
  let newLine: number | null = null

  for (const raw of diff.replace(/\r\n/g, "\n").split("\n")) {
    if (raw.startsWith("@@")) {
      const match = /@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(raw)
      oldLine = match ? Number(match[1]) : null
      newLine = match ? Number(match[2]) : null
      lines.push({ type: "ctx", text: raw, oldLine: null, newLine: null })
      continue
    }

    const type = lineType(raw)

    if (type === "meta") {
      oldLine = null
      newLine = null
      lines.push({ type, text: raw, oldLine: null, newLine: null })
      continue
    }

    if (type === "add") {
      lines.push({ type, text: raw, oldLine: null, newLine })
      if (newLine !== null) newLine += 1
      continue
    }

    if (type === "del") {
      lines.push({ type, text: raw, oldLine, newLine: null })
      if (oldLine !== null) oldLine += 1
      continue
    }

    lines.push({ type: "same", text: raw, oldLine, newLine })
    if (oldLine !== null) oldLine += 1
    if (newLine !== null) newLine += 1
  }

  return lines
}
