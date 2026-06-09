import Link from "next/link"
import Image from "next/image"
import { getServerSession } from "next-auth"
import { SignOutButton } from "@/components/auth-buttons"
import styles from "./page.module.css"
import { authOptions } from "../api/auth/[...nextauth]/route"

export default async function Dashboard() {
  const session = await getServerSession(authOptions)
  const user = session?.user

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <span className={styles.logo}>Meridian</span>
        <Link href="/" className={styles.homeLink}>Home</Link>
      </nav>

      <main className={styles.main}>
        <div className={styles.card}>
          {user?.image && (
            <Image
              src={user.image}
              alt={user.name ?? "Avatar"}
              width={80}
              height={80}
              className={styles.avatar}
            />
          )}
          <h1 className={styles.name}>{user?.name ?? "User"}</h1>
          <p className={styles.email}>{user?.email}</p>
          <div className={styles.divider} />
          <p className={styles.text}>
            Signed in with GitHub
          </p>
          <div className={styles.actions}>
            <SignOutButton />
          </div>
        </div>
      </main>
    </div>
  )
}
