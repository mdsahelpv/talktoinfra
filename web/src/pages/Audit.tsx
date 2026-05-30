import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Audit() {
  const [entries, setEntries] = useState<any[]>([])

  useEffect(() => {
    api.audit.list().then((r) => setEntries(r.entries)).catch(() => {})
  }, [])

  return (
    <div className="p-6 space-y-4 overflow-y-auto h-full">
      <h2 className="text-xl font-bold">Audit Log</h2>

      <div className="space-y-1">
        {entries.map((e) => (
          <div key={e.id} className="bg-gray-800 rounded px-3 py-2 flex items-center gap-3 text-sm">
            <span className={`w-2 h-2 rounded-full ${e.approved ? 'bg-green-400' : 'bg-red-400'}`} />
            <span className="text-gray-400 w-40 text-xs">
              {e.timestamp ? new Date(e.timestamp).toLocaleString() : '-'}
            </span>
            <span className="font-mono text-cyan-300 w-40">{e.action}</span>
            <span className={`text-xs w-16 ${e.tier === 'read' ? 'text-green-400' : e.tier === 'mutate' ? 'text-yellow-400' : 'text-red-400'}`}>
              {e.tier}
            </span>
            <span className="text-gray-500 text-xs">{e.approved_by || '-'}</span>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-gray-500 text-sm text-center py-8">No audit entries yet</p>
        )}
      </div>
    </div>
  )
}
