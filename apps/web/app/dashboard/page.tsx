import { redirect } from "next/navigation"
import { RepoPicker } from "@/components/dashboard/repo-picker"
import { getSession } from "@/lib/auth/session"

export default async function Dashboard() {
  const session = await getSession()

  if (!session.authenticated || !session.user) {
    redirect("/")
  }

  return <RepoPicker user={session.user} />
}
