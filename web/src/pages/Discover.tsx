import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Discover() {
  const [scan, setScan] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const runScan = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.discover.scan()
      setScan(res.scan)
    } catch {
      setError('Scan failed — is the orchestrator running?')
    }
    setLoading(false)
  }

  useEffect(() => { runScan() }, [])

  const totalResources = scan
    ? Object.values(scan).reduce((sum: number, cat: any) => {
        return sum + Object.values(cat.resources).reduce((s: number, r: any) => s + r.count, 0)
      }, 0)
    : 0

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Infrastructure Discovery</h2>
          <p className="text-sm text-gray-400 mt-1">
            {scan ? `${Object.keys(scan).length} categories · ${totalResources} resources found` : 'Scan your infrastructure to discover resources'}
          </p>
        </div>
        <button
          onClick={runScan}
          disabled={loading}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:bg-gray-700 text-white rounded-lg text-sm flex items-center gap-2"
        >
          {loading ? (
            <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <span>⟳</span>
          )}
          {loading ? 'Scanning...' : 'Scan Now'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {!scan && !loading && (
        <div className="text-center text-gray-500 mt-20">
          <p className="text-5xl mb-4">🔍</p>
          <p>Click "Scan Now" to discover infrastructure resources</p>
        </div>
      )}

      {scan && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(scan).map(([key, cat]: [string, any]) => {
            const resourceEntries = Object.entries(cat.resources)
            const totalForCat = resourceEntries.reduce((s: number, [, r]: any) => s + r.count, 0)
            const isExpanded = expanded === key
            return (
              <div key={key} className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
                <button
                  onClick={() => setExpanded(isExpanded ? null : key)}
                  className="w-full p-4 flex items-center justify-between hover:bg-gray-750 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{cat.icon}</span>
                    <div>
                      <p className="font-semibold capitalize text-gray-100">{key}</p>
                      <p className="text-xs text-gray-400">{cat.description}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-cyan-400">{totalForCat}</p>
                    <p className="text-xs text-gray-500">resources</p>
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 space-y-2 border-t border-gray-700 pt-3">
                    {resourceEntries.map(([rkey, rval]: [string, any]) => (
                      <div key={rkey} className="flex justify-between text-sm">
                        <span className="text-gray-300">{rkey.replace(/_/g, ' ')}</span>
                        <span className={`font-mono ${rval.count > 0 ? 'text-green-400' : 'text-gray-500'}`}>
                          {rval.count}
                        </span>
                      </div>
                    ))}
                    {cat.tools.length > 0 && (
                      <div className="pt-2 border-t border-gray-700">
                        <p className="text-xs text-gray-500 mb-1">Available actions:</p>
                        <div className="flex flex-wrap gap-1">
                          {cat.tools.map((t: string) => (
                            <span key={t} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-xs pt-1">
                      <span className={`inline-block w-2 h-2 rounded-full ${cat.status === 'connected' ? 'bg-green-400' : 'bg-gray-500'}`} />
                      <span className="text-gray-400">{cat.status}</span>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
