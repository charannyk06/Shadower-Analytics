import Link from 'next/link'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8">Shadow Analytics</h1>
        <p className="text-xl mb-8">Analytics platform for Shadow agent monitoring</p>

        <div className="grid grid-cols-2 gap-4 max-w-2xl">
          <Link
            href="/executive"
            className="p-6 border border-gray-300 rounded-lg hover:border-gray-400"
          >
            <h2 className="text-2xl font-semibold mb-2">Executive Dashboard</h2>
            <p>View key business metrics and KPIs</p>
          </Link>

          <Link
            href="/agents"
            className="p-6 border border-gray-300 rounded-lg hover:border-gray-400"
          >
            <h2 className="text-2xl font-semibold mb-2">Agent Analytics</h2>
            <p>Monitor agent performance and execution metrics</p>
          </Link>

          <Link
            href="/users"
            className="p-6 border border-gray-300 rounded-lg hover:border-gray-400"
          >
            <h2 className="text-2xl font-semibold mb-2">User Analytics</h2>
            <p>Track user activity and engagement</p>
          </Link>

          <Link
            href="/workspaces"
            className="p-6 border border-gray-300 rounded-lg hover:border-gray-400"
          >
            <h2 className="text-2xl font-semibold mb-2">Workspaces</h2>
            <p>Workspace metrics and statistics</p>
          </Link>
        </div>
      </div>
    </main>
  )
}
