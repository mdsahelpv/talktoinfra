import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Dashboard() {
  const [health, setHealth] = useState<any>(null)
  const [tools, setTools] = useState<any[]>([])
  const [agents, setAgents] = useState<any[]>([])

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ healthy: false }))
    api.tools.list().then((r) => setTools(r.tools)).catch(() => {})
    api.agents.list().then((r) => setAgents(r.agents)).catch(() => {})
  }, [])

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <h2 className="text-xl font-bold">Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-400">Orchestrator</p>
          <p className={`text-lg font-bold ${health?.healthy ? 'text-green-400' : 'text-red-400'}`}>
            {health?.healthy ? 'Online' : 'Offline'}
          </p>
          <p className="text-xs text-gray-500">{health?.version || '-'}</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-400">Available Tools</p>
          <p className="text-lg font-bold text-cyan-400">{tools.length}</p>
          <p className="text-xs text-gray-500">
            {tools.filter((t) => t.tier === 'read').length} read ·{' '}
            {tools.filter((t) => t.tier === 'mutate').length} mutate ·{' '}
            {tools.filter((t) => t.tier === 'destructive').length} destructive
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-400">Connected Agents</p>
          <p className="text-lg font-bold text-cyan-400">{agents.length}</p>
          <p className="text-xs text-gray-500">
            {agents.map((a) => a.name).join(', ') || 'None'}
          </p>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">Tool Categories</h3>
        <div className="space-y-2">
          {['kubernetes', 'network', 'cloud', 'ad', 'onprem', 'database', 'monitoring'].map((cat) => {
            const count = tools.filter((t) => t.category === cat).length
            if (count === 0) return null
            return (
              <div key={cat} className="flex justify-between text-sm">
                <span className="capitalize text-gray-300">{cat}</span>
                <span className="text-gray-500">{count} tools</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
