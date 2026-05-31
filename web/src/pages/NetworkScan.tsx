import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

export default function NetworkScan() {
  const [cidr, setCidr] = useState('192.168.1.0/24')
  const [portGroups, setPortGroups] = useState<Record<string, number[]>>({})
  const [selectedPorts, setSelectedPorts] = useState<number[]>([])
  const [jobId, setJobId] = useState('')
  const [scanStatus, setScanStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [actionMsg, setActionMsg] = useState('')
  const [selectedHosts, setSelectedHosts] = useState<Set<string>>(new Set())
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    api.networkScan.ports().then((r) => {
      setPortGroups(r.groups)
      setSelectedPorts(r.quick_ports)
    }).catch(() => {})
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const toggleGroup = (ports: number[]) => {
    const allIn = ports.every((p) => selectedPorts.includes(p))
    setSelectedPorts((prev) =>
      allIn ? prev.filter((p) => !ports.includes(p)) : [...new Set([...prev, ...ports])]
    )
  }

  const startScan = async () => {
    setLoading(true)
    setActionMsg('')
    setJobId('')
    setScanStatus(null)
    setSelectedHosts(new Set())
    try {
      const res = await api.networkScan.start(cidr, selectedPorts.length > 0 ? selectedPorts : undefined)
      setJobId(res.job_id)
      setScanStatus({ ...res, hosts: [] })
    } catch (e: any) {
      setActionMsg(`Error: ${e.message || e}`)
    }
    setLoading(false)
  }

  useEffect(() => {
    if (!jobId || !scanStatus) return
    if (scanStatus.status === 'completed' || scanStatus.status === 'failed') return

    pollRef.current = setInterval(async () => {
      try {
        const res = await api.networkScan.status(jobId)
        setScanStatus(res)
        if (res.status === 'completed' || res.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch { if (pollRef.current) clearInterval(pollRef.current) }
    }, 1500)

    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [jobId])

  const toggleHost = (ip: string) => {
    setSelectedHosts((prev) => {
      const next = new Set(prev)
      if (next.has(ip)) next.delete(ip)
      else next.add(ip)
      return next
    })
  }

  const toggleAll = () => {
    if (!scanStatus?.hosts) return
    if (selectedHosts.size === scanStatus.hosts.length) {
      setSelectedHosts(new Set())
    } else {
      setSelectedHosts(new Set(scanStatus.hosts.map((h: any) => h.ip)))
    }
  }

  const handleDeployAgent = async () => {
    if (!jobId || selectedHosts.size === 0) return
    try {
      const res = await api.networkScan.deployAgent(jobId, Array.from(selectedHosts))
      setActionMsg(`Deploy ready for ${selectedHosts.size} host(s): ` + res.hosts?.map((h: any) => `${h.ip} (${h.status})`).join(', '))
    } catch (e: any) {
      setActionMsg(`Deploy error: ${e.message || e}`)
    }
  }

  const handleAgentless = async () => {
    if (!jobId || selectedHosts.size === 0) return
    try {
      const res = await api.networkScan.connectAgentless(jobId, Array.from(selectedHosts))
      setActionMsg(`Agentless connections ready for ${selectedHosts.size} host(s)`)
    } catch (e: any) {
      setActionMsg(`Agentless error: ${e.message || e}`)
    }
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <div>
        <h2 className="text-xl font-bold">Network Scan</h2>
        <p className="text-sm text-gray-400 mt-1">Scan an IP range to discover servers, services, and connect to them</p>
      </div>

      <div className="bg-gray-800 rounded-lg p-4 space-y-4">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-400 block mb-1">IP Range (CIDR)</label>
            <input
              type="text"
              value={cidr}
              onChange={(e) => setCidr(e.target.value)}
              placeholder="10.0.0.0/24"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div className="flex gap-2">
            {['192.168.1.0/24', '10.0.0.0/24', '172.16.0.0/24'].map((p) => (
              <button key={p} onClick={() => setCidr(p)} className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 px-2 py-1 rounded">{p}</button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-400 block mb-2">Port Groups</label>
          <div className="flex flex-wrap gap-2">
            {Object.entries(portGroups).map(([name, ports]) => {
              const active = ports.every((p) => selectedPorts.includes(p))
              return (
                <button
                  key={name}
                  onClick={() => toggleGroup(ports)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                    active ? 'bg-cyan-700 border-cyan-500 text-white' : 'bg-gray-700 border-gray-600 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  {name} ({ports.length})
                </button>
              )
            })}
          </div>
          <p className="text-xs text-gray-500 mt-1">{selectedPorts.length} ports selected</p>
        </div>

        <button
          onClick={startScan}
          disabled={loading || !cidr}
          className="px-5 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:bg-gray-700 text-white rounded-lg text-sm"
        >
          {loading ? 'Starting Scan...' : 'Start Scan'}
        </button>
      </div>

      {actionMsg && (
        <div className="bg-blue-900/30 border border-blue-800 text-blue-300 px-4 py-3 rounded-lg text-sm">{actionMsg}</div>
      )}

      {scanStatus && (
        <div className="space-y-4">
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <div>
                <span className="text-sm text-gray-400">Scan: </span>
                <span className="text-sm font-mono text-gray-200">{scanStatus.cidr}</span>
                <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                  scanStatus.status === 'completed' ? 'bg-green-700 text-green-200' :
                  scanStatus.status === 'failed' ? 'bg-red-700 text-red-200' :
                  scanStatus.status === 'running' ? 'bg-yellow-700 text-yellow-200' :
                  'bg-gray-700 text-gray-300'
                }`}>{scanStatus.status}</span>
              </div>
              <span className="text-xs text-gray-500">{scanStatus.hosts_found} hosts found / {scanStatus.total_hosts} scanned</span>
            </div>
            {scanStatus.status === 'running' && (
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div className="bg-cyan-500 h-2 rounded-full transition-all" style={{ width: `${scanStatus.progress || 0}%` }} />
              </div>
            )}
            {scanStatus.error && <p className="text-red-400 text-sm mt-2">{scanStatus.error}</p>}
          </div>

          {scanStatus.hosts && scanStatus.hosts.length > 0 && (
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="p-3 flex items-center justify-between border-b border-gray-700">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={scanStatus.hosts.length > 0 && selectedHosts.size === scanStatus.hosts.length}
                    onChange={toggleAll}
                    className="rounded bg-gray-700 border-gray-500"
                  />
                  <span className="text-sm text-gray-300">{scanStatus.hosts_found} host(s)</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleAgentless}
                    disabled={selectedHosts.size === 0}
                    className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 text-xs rounded"
                  >
                    Connect Agentless (SSH)
                  </button>
                  <button
                    onClick={handleDeployAgent}
                    disabled={selectedHosts.size === 0}
                    className="px-3 py-1.5 bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-white text-xs rounded"
                  >
                    Deploy Agent
                  </button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 text-gray-500 text-xs">
                      <th className="p-3 text-left w-8"></th>
                      <th className="p-3 text-left">IP</th>
                      <th className="p-3 text-left">Hostname</th>
                      <th className="p-3 text-left">Status</th>
                      <th className="p-3 text-left">Services</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scanStatus.hosts.map((host: any) => (
                      <tr key={host.ip} className="border-b border-gray-700/50 hover:bg-gray-750">
                        <td className="p-3">
                          <input
                            type="checkbox"
                            checked={selectedHosts.has(host.ip)}
                            onChange={() => toggleHost(host.ip)}
                            className="rounded bg-gray-700 border-gray-500"
                          />
                        </td>
                        <td className="p-3 font-mono text-gray-200">{host.ip}</td>
                        <td className="p-3 text-gray-400">{host.hostname || '-'}</td>
                        <td className="p-3">
                          <span className={`inline-block w-2 h-2 rounded-full ${host.status === 'up' ? 'bg-green-400' : 'bg-gray-500'}`} />
                        </td>
                        <td className="p-3">
                          <div className="flex flex-wrap gap-1">
                            {host.ports.map((p: any) => (
                              <span key={p.port} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded" title={p.service}>
                                {p.port}/{p.service}
                              </span>
                            ))}
                            {host.ports.length === 0 && (
                              <span className="text-xs text-gray-600">No open ports detected</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {scanStatus.hosts && scanStatus.hosts.length === 0 && scanStatus.status === 'completed' && (
            <div className="bg-gray-800 rounded-lg p-6 text-center text-gray-500">
              No live hosts found in {scanStatus.cidr}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
