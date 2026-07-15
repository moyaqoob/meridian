import { cookies } from "next/headers"
import { endpoints } from "@/lib/api/endpoints"

export type User = {
  id: string
  github_id: number
  login: string
}

export type Session = {
  authenticated: boolean
  user: User | null
}

function apiBaseUrl(): string {
  return process.env.API_URL ?? "http://localhost:8000"
}

function cookieHeader(jar: Awaited<ReturnType<typeof cookies>>): string {
  return jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ")
}

export async function getSession(): Promise<Session> {
  const jar = await cookies()
  const sessionCookie = jar.get("session")

  if (!sessionCookie) {
    return { authenticated: false, user: null }
  }

  try {
    const res = await fetch(`${apiBaseUrl()}${endpoints.auth.me()}`, {
      headers: { Cookie: cookieHeader(jar) },
      cache: "no-store",
    })

    if (!res.ok) {
      return { authenticated: false, user: null }
    }

    return res.json() as Promise<Session>
  } catch {
    return { authenticated: false, user: null }
  }
}

export function githubAvatarUrl(githubId: number): string {
  return `https://avatars.githubusercontent.com/u/${githubId}?v=4`
}
