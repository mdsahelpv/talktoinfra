import { useState, useEffect, useCallback } from 'react';
import { Scan, Play, Square, Plus, Trash2, Server, Activity, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';
import { Button, Input, Card, CardContent, CardHeader, CardTitle, Badge, Progress } from '@/components/ui';
import { hostApi, discoveryApi } from '@/api/client';
// import { useAuthStore } from '@/stores';  // TODO: Re-enable when implementing proper authorization
import ScanHistoryList from './ScanHistoryList';
import ScanDetailModal from './ScanDetailModal';
import ScanTypeSelector from './ScanTypeSelector';
import HostDetailView from './HostDetailView';
import type { DiscoveredHost, ManagedHost, ScanJob, DiscoveredPort } from '@/types';

const PORT_PRESETS: Record<string, number[]> = {
  common: [22, 80, 443, 5432, 6379, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 6443],
  talkai: [8000, 8001, 8002, 8003, 8004, 8005, 8006],
  databases: [5432, 3306, 27017, 6379, 9200, 5433, 3307],
  kubernetes: [6443, 10250, 10251, 10252, 2379, 2380, 10255, 10256],
  web: [80, 443, 8080, 8443, 3000, 3001, 8000, 9000],
  ssh: [22, 2222, 8022],
};

const POLLING_INTERVAL = 1500;

// CIDR validation helper
function validateCIDR(cidr: string): boolean {
  const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
  if (!cidrRegex.test(cidr)) return false;
  const [ip, mask] = cidr.split('/');
  const maskNum = parseInt(mask, 10);
  const parts = ip.split('.').map(Number);
  return maskNum >= 0 && maskNum <= 32 && parts.every(p => p >= 0 && p <= 255);
}

// Calculate network size from CIDR
function getNetworkSize(cidr: string): number {
  const [, mask] = cidr.split('/');
  const maskNum = parseInt(mask, 10);
  return Math.pow(2, 32 - maskNum);
}

export default function InfrastructureDiscovery() {
  const [ipRange, setIpRange] = useState('');
  const [selectedPorts, setSelectedPorts] = useState<number[]>(PORT_PRESETS.talkai);
  const [customPorts, setCustomPorts] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanJobId, setScanJobId] = useState<string | null>(null);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanStatus, setScanStatus] = useState<string>('');
  const [discoveredHosts, setDiscoveredHosts] = useState<DiscoveredHost[]>([]);
  const [managedHosts, setManagedHosts] = useState<ManagedHost[]>([]);
  const [selectedHosts, setSelectedHosts] = useState<Set<string>>(new Set());
  const [activePreset, setActivePreset] = useState<string>('talkai');
  const [selectedScanner, setSelectedScanner] = useState<'python' | 'fast' | 'detailed' | 'hybrid'>('python');
  const [showScannerSelector, setShowScannerSelector] = useState(false);
  const [scanHistory, setScanHistory] = useState<ScanJob[]>([]);
  const [selectedScan, setSelectedScan] = useState<ScanJob | null>(null);
  const [showScanModal, setShowScanModal] = useState(false);
  const [selectedManagedHost, setSelectedManagedHost] = useState<ManagedHost | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  // TODO: Implement proper authorization in future
  // Currently all authenticated users can access infrastructure discovery
  // The isAdmin check has been bypassed to allow all authenticated users access

  const loadManagedHosts = useCallback(async () => {
    try {
      const hosts = await hostApi.listHosts();
      setManagedHosts(hosts as ManagedHost[]);
    } catch (error) {
      console.error('Failed to load managed hosts:', error);
    }
  }, []);

  const loadScanHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const response = await discoveryApi.getScans(undefined, 50);
      setScanHistory(response.items as ScanJob[]);
    } catch (error) {
      console.error('Failed to load scan history:', error);
      toast.error('Failed to load scan history');
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    loadManagedHosts();
    loadScanHistory();
  }, [loadManagedHosts, loadScanHistory]);

  useEffect(() => {
    if (!scanJobId || !isScanning) return;

    const interval = setInterval(async () => {
      try {
        const status = await discoveryApi.getScanStatus(scanJobId);
        setScanProgress(status.progress);
        setScanStatus(status.status);

        if (status.status === 'completed') {
          setIsScanning(false);
          const results = await discoveryApi.getScanResults(scanJobId, true);
          const hosts = results.hosts.map(h => ({
            ...h,
            ports: h.ports.map(p => ({ ...p, status: p.status as 'open' | 'closed' | 'filtered' })),
            status: h.status as 'alive' | 'unreachable' | 'filtered',
            discovered_at: h.discovered_at,
          })) as DiscoveredHost[];
          setDiscoveredHosts(hosts);
          toast.success(`Scan completed! Found ${results.found_hosts} host(s)`);
          loadScanHistory();
          clearInterval(interval);
        } else if (status.status === 'failed' || status.status === 'cancelled') {
          setIsScanning(false);
          toast.error(`Scan ${status.status}`);
          loadScanHistory();
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to get scan status:', error);
        setIsScanning(false);
        clearInterval(interval);
      }
    }, POLLING_INTERVAL);

    return () => clearInterval(interval);
  }, [scanJobId, isScanning, loadScanHistory]);

  const validateIPRange = (range: string): { valid: boolean; format: 'cidr' | 'range' | 'single' | 'invalid'; count: number } => {
    const trimmed = range.trim();
    
    // CIDR notation: 192.168.1.0/24
    const cidrRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:3[0-2]|[1-2]?[0-9])$/;
    if (cidrRegex.test(trimmed)) {
      const [ip, prefix] = trimmed.split('/');
      const prefixNum = parseInt(prefix);
      if (prefixNum >= 16 && prefixNum <= 32) {
        const octets = ip.split('.').map(Number);
        if (octets.every(o => o >= 0 && o <= 255)) {
          const count = prefixNum === 32 ? 1 : Math.pow(2, 32 - prefixNum) - 2;
          return { valid: true, format: 'cidr', count: Math.max(1, count) };
        }
      }
    }
    
    // IP range: 192.168.1.1-192.168.1.100
    const rangeRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)-(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    if (rangeRegex.test(trimmed)) {
      const [start, end] = trimmed.split('-');
      const startOctets = start.split('.').map(Number);
      const endOctets = end.split('.').map(Number);
      
      // Calculate number of hosts
      let count = 0;
      for (let i = 0; i < 4; i++) {
        count = count * 256 + (endOctets[i] - startOctets[i]);
      }
      count = Math.abs(count) + 1;
      
      return { valid: true, format: 'range', count };
    }
    
    // Single IP: 192.168.1.1
    const singleRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    if (singleRegex.test(trimmed)) {
      return { valid: true, format: 'single', count: 1 };
    }
    
    return { valid: false, format: 'invalid', count: 0 };
  };

  const getNetworkSize = (range: string): number => {
    const validation = validateIPRange(range);
    return validation.count;
  };

  const startScan = async () => {
    const validation = validateIPRange(ipRange);
    if (!validation.valid) {
      toast.error('Invalid IP range. Use CIDR (192.168.1.0/24), range (192.168.1.1-192.168.1.100), or single IP (192.168.1.1)');
      return;
    }
    
    if (validation.count > 65536) {
      toast.error('IP range too large. Maximum is 65,536 hosts (/16 network)');
      return;
    }

    if (selectedPorts.length === 0) {
      toast.error('Please select at least one port to scan');
      return;
    }

    try {
      setIsScanning(true);
      setScanProgress(0);
      setScanStatus('pending');
      setDiscoveredHosts([]);
      setSelectedHosts(new Set());

      const response = await discoveryApi.startScan({
        ip_range: ipRange,
        ports: selectedPorts,
        scan_type: selectedScanner,
        timeout: 2.0,
        concurrent_limit: 50,
        service_detection: true,
      });

      setScanJobId(response.job_id);
      toast.success('Scan started!');
    } catch (error) {
      setIsScanning(false);
      toast.error(error instanceof Error ? error.message : 'Failed to start scan');
    }
  };

  const stopScan = async () => {
    if (!scanJobId) return;

    try {
      await discoveryApi.stopScan(scanJobId);
      setIsScanning(false);
      toast.success('Scan stopped');
      loadScanHistory();
    } catch (error) {
      toast.error('Failed to stop scan');
    }
  };

  const handlePresetChange = (preset: string) => {
    setActivePreset(preset);
    setSelectedPorts(PORT_PRESETS[preset] || []);
    setCustomPorts('');
  };

  const handleCustomPortsChange = (value: string) => {
    setCustomPorts(value);
    setActivePreset('custom');

    const ports = value
      .split(/[,\s]+/)
      .map(p => parseInt(p.trim()))
      .filter(p => !isNaN(p) && p > 0 && p <= 65535);

    setSelectedPorts(ports);
  };

  const toggleHostSelection = (hostId: string) => {
    const newSelected = new Set(selectedHosts);
    if (newSelected.has(hostId)) {
      newSelected.delete(hostId);
    } else {
      newSelected.add(hostId);
    }
    setSelectedHosts(newSelected);
  };

  const addSelectedHosts = async () => {
    const hostsToAdd = discoveredHosts.filter(h => selectedHosts.has(h.id));
    let addedCount = 0;

    for (const host of hostsToAdd) {
      try {
        await hostApi.addHost({
          name: host.hostname || host.ip_address,
          ip_address: host.ip_address,
          ports: host.ports.filter((p: DiscoveredPort) => p.status === 'open').map((p: DiscoveredPort) => p.port),
          services: host.ports.filter((p: DiscoveredPort) => p.service).map((p: DiscoveredPort) => p.service!) || [],
        });
        addedCount++;
      } catch (error) {
        console.error(`Failed to add host ${host.ip_address}:`, error);
      }
    }

    toast.success(`Added ${addedCount} of ${hostsToAdd.length} host(s) to managed list`);
    setSelectedHosts(new Set());
    loadManagedHosts();
    
    setDiscoveredHosts(prev => prev.map(h => 
      selectedHosts.has(h.id) ? { ...h, added_to_hosts: true } : h
    ));
  };

  const deleteHost = async (hostId: string) => {
    try {
      await hostApi.deleteHost(hostId);
      toast.success('Host removed');
      loadManagedHosts();
    } catch (error) {
      toast.error('Failed to remove host');
    }
  };

  const handleViewScan = (scan: ScanJob) => {
    setSelectedScan(scan);
    setShowScanModal(true);
  };

  const handleDeleteScan = async (scanId: string) => {
    try {
      await discoveryApi.deleteScan(scanId);
      toast.success('Scan deleted');
      loadScanHistory();
    } catch (error) {
      toast.error('Failed to delete scan');
    }
  };

  const handleAddHostToManaged = async (host: DiscoveredHost) => {
    try {
      await hostApi.addHost({
        name: host.hostname || host.ip_address,
        ip_address: host.ip_address,
        ports: host.ports.filter((p: DiscoveredPort) => p.status === 'open').map((p: DiscoveredPort) => p.port),
        services: host.ports.filter((p: DiscoveredPort) => p.service).map((p: DiscoveredPort) => p.service!) || [],
      });
      toast.success(`Added ${host.ip_address} to managed hosts`);
      loadManagedHosts();
    } catch (error) {
      console.error('Failed to add host:', error);
      toast.error('Failed to add host');
    }
  };

  return (
    <div className="space-y-6">
      {/* Scan Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scan className="h-5 w-5" />
            Network Scan
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* IP Range Input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">IP Range</label>
            <Input
              placeholder="192.168.1.0/24 or 192.168.1.1-192.168.1.100 or 192.168.1.1"
              value={ipRange}
              onChange={(e) => setIpRange(e.target.value)}
              disabled={isScanning}
            />
            <p className="text-xs text-muted-foreground">
              Enter IP range in CIDR notation (192.168.1.0/24), range format (192.168.1.1-192.168.1.100), or single IP (192.168.1.1)
            </p>
          </div>

          {/* Scanner Type Selection */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Scanner Type</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowScannerSelector(!showScannerSelector)}
                className="gap-1"
              >
                {showScannerSelector ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                {showScannerSelector ? 'Hide' : 'Change'}
              </Button>
            </div>
            
            {!showScannerSelector && (
              <div className="flex items-center gap-2 p-3 border rounded-lg bg-muted/30">
                <div className="p-2 bg-primary/10 rounded">
                  <Scan className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="font-medium capitalize">{selectedScanner.replace('_', ' ')} Scanner</p>
                  <p className="text-xs text-muted-foreground">
                    {ipRange && validateCIDR(ipRange) 
                      ? `Recommended for /${ipRange.split('/')[1]} networks`
                      : 'Select scanner based on network size'}
                  </p>
                </div>
              </div>
            )}
            
            {showScannerSelector && (
              <ScanTypeSelector
                selected={selectedScanner}
                onSelect={setSelectedScanner}
                networkSize={ipRange && validateCIDR(ipRange) ? getNetworkSize(ipRange) : undefined}
              />
            )}
          </div>

          {/* Port Presets */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Port Selection</label>
            <div className="flex flex-wrap gap-2">
              {Object.keys(PORT_PRESETS).map((preset) => (
                <Button
                  key={preset}
                  variant={activePreset === preset ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handlePresetChange(preset)}
                  disabled={isScanning}
                >
                  {preset.charAt(0).toUpperCase() + preset.slice(1)}
                </Button>
              ))}
              <Button
                variant={activePreset === 'custom' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActivePreset('custom')}
                disabled={isScanning}
              >
                Custom
              </Button>
            </div>
          </div>

          {/* Custom Ports Input */}
          {activePreset === 'custom' && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Custom Ports</label>
              <Input
                placeholder="8000, 8001, 5432, 6379"
                value={customPorts}
                onChange={(e) => handleCustomPortsChange(e.target.value)}
                disabled={isScanning}
              />
              <p className="text-xs text-muted-foreground">
                Enter comma-separated port numbers
              </p>
            </div>
          )}

          {/* Selected Ports Display */}
          <div className="flex flex-wrap gap-1">
            {selectedPorts.slice(0, 10).map((port) => (
              <Badge key={port} variant="secondary" className="text-xs">
                {port}
              </Badge>
            ))}
            {selectedPorts.length > 10 && (
              <Badge variant="secondary" className="text-xs">
                +{selectedPorts.length - 10} more
              </Badge>
            )}
          </div>

          {/* Scan Controls */}
          <div className="flex items-center gap-4">
            {!isScanning ? (
              <Button onClick={startScan} className="gap-2">
                <Play className="h-4 w-4" />
                Start Scan
              </Button>
            ) : (
              <Button onClick={stopScan} variant="destructive" className="gap-2">
                <Square className="h-4 w-4" />
                Stop Scan
              </Button>
            )}

            {isScanning && (
              <div className="flex-1 space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Scanning with {selectedScanner}...</span>
                  <span>{scanProgress}%</span>
                </div>
                <Progress value={scanProgress} />
                <p className="text-xs text-muted-foreground capitalize">
                  Status: {scanStatus}
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Scan History */}
      <ScanHistoryList
        scans={scanHistory}
        onViewScan={handleViewScan}
        onDeleteScan={handleDeleteScan}
        loading={loadingHistory}
      />

      {/* Scan Results */}
      {discoveredHosts.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Current Scan Results
              <Badge variant="secondary">{discoveredHosts.length}</Badge>
            </CardTitle>
            <Button
              onClick={addSelectedHosts}
              disabled={selectedHosts.size === 0}
              size="sm"
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Add Selected ({selectedHosts.size})
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {discoveredHosts.map((host) => (
                <div
                  key={host.id}
                  className="flex items-start gap-4 p-3 rounded-lg border hover:bg-accent/50 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedHosts.has(host.id)}
                    onChange={() => toggleHostSelection(host.id)}
                    className="mt-1"
                    disabled={host.added_to_hosts}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Server className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{host.ip_address}</span>
                      {host.hostname && (
                        <span className="text-sm text-muted-foreground">
                          ({host.hostname})
                        </span>
                      )}
                      {host.response_time_ms && (
                        <Badge variant="outline" className="text-xs gap-1">
                          <Clock className="h-3 w-3" />
                          {host.response_time_ms}ms
                        </Badge>
                      )}
                      {host.added_to_hosts && (
                        <Badge variant="success" className="text-xs">Added</Badge>
                      )}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {host.ports
                        .filter((p) => p.status === 'open')
                        .map((port) => (
                          <Badge
                            key={port.port}
                            variant="default"
                            className="text-xs gap-1"
                          >
                            {port.port}
                            {port.service && `: ${port.service}`}
                          </Badge>
                        ))}
                    </div>
                  </div>
                  {!host.added_to_hosts && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAddHostToManaged(host)}
                      className="gap-1"
                    >
                      <Plus className="h-3 w-3" />
                      Add
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Managed Hosts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            Managed Hosts
            <Badge variant="secondary">{managedHosts.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {managedHosts.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No managed hosts. Run a scan and add discovered hosts.
            </p>
          ) : (
            <div className="space-y-2">
              {managedHosts.map((host) => (
                <div
                  key={host.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/30 transition-colors cursor-pointer"
                  onClick={() => setSelectedManagedHost(host)}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Server className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{host.name}</span>
                      <Badge
                        variant={
                          host.status === 'online'
                            ? 'default'
                            : host.status === 'offline'
                            ? 'destructive'
                            : 'secondary'
                        }
                        className="text-xs"
                      >
                        {host.status}
                      </Badge>
                    </div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      {host.ip_address} • {host.ports.length} port(s) • Added by{' '}
                      {host.added_by}
                    </div>
                    {host.services.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {host.services.slice(0, 5).map((svc) => (
                          <Badge key={svc} variant="outline" className="text-xs">
                            {svc}
                          </Badge>
                        ))}
                        {host.services.length > 5 && (
                          <Badge variant="outline" className="text-xs">
                            +{host.services.length - 5}
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteHost(host.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scan Detail Modal */}
      <ScanDetailModal
        scan={selectedScan}
        open={showScanModal}
        onClose={() => {
          setShowScanModal(false);
          setSelectedScan(null);
        }}
        onAddToManaged={handleAddHostToManaged}
      />

      {/* Host Detail Modal */}
      {selectedManagedHost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div 
            className="fixed inset-0 bg-black/50 backdrop-blur-sm" 
            onClick={() => setSelectedManagedHost(null)}
          />
          <div className="relative z-50 w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-lg border bg-card p-6 shadow-lg m-4">
            <HostDetailView
              host={selectedManagedHost}
              onRemoveFromManaged={() => {
                deleteHost(selectedManagedHost.id);
                setSelectedManagedHost(null);
              }}
            />
            <div className="flex justify-end mt-6">
              <Button onClick={() => setSelectedManagedHost(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
