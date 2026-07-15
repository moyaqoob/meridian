import { redirect } from "next/navigation"
import { ReviewWorkspace } from "@/components/pipeline/review-workspace"
import { getSession } from "@/lib/auth/session"

type PageProps = {
  params: Promise<{ owner: string; repo: string }>
}

export default async function RepoPipelinePage({ params }: PageProps) {
  const session = await getSession()
  const { owner, repo } = await params

  if (!session.authenticated || !session.user) {
    redirect("/")
  }

  return <ReviewWorkspace owner={owner} repo={repo} />
}
