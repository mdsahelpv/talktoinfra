import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Sessions() {
  const [sessions, setSessions] = useState<any[]>([])

  useEffect(() => {
    api.sessions.list().then((r) => setSessions(r.sessions)).catch(() => {})
  }, [])

  return (
    <div className="p-6 space-y-4 overflow-y-auto h-full">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Sessions</h2>
        <button
          onClick={async () => {
            const res = await api.sessions.create()
            setSessions((prev) => [
              { id: res.session_id, description: 'New session', message_count: 0, status: 'active' },
              ...prev,
            ])
          }}
          className="px-3 py-1 bg-cyan-600 hover:bg-cyan-700 text-white text-sm rounded"
        >
          + New Session
        </button>
      </div>

      <div className="space-y-2">
        {sessions.map((s) => (
          <div key={s.id} className="bg-gray-800 rounded-lg p-4 flex justify-between items-center">
            <div>
              <p className="text-sm font-medium text-gray-200">{s.description || 'Unnamed'}</p>
              <p className="text-xs text-gray-500">
                {s.message_count} messages · {s.status}
              </p>
            </div>
            <div className="text-xs text-gray-500">
              {s.last_active ? new Date(s.last_active).toLocaleDateString() : '-'}
            </div>
          </div>
        ))}
        {sessions.length === 0 && (
          <p className="text-gray-500 text-sm text-center py-8">No sessions yet</p>
        )}
      </div>
    </div>
  )
}
