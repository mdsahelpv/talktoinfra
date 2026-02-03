import { useState, useEffect } from 'react';
import { Server, CheckCircle, Clock, Globe, Scan, Plus, Loader2 } from 'lucide-react';
import { Button, Badge, Progress } from '@/components/ui';
import Dialog, { DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog';
import { hostApi, discoveryApi } from '@/api/client';
import toast from 'react-hot-toast';
import type { ScanJob, DiscoveredHost } from '@/types';

interface ScanDetailModalProps {
  scan: ScanJob | null;
  open: boolean;
  onClose: () => void;
  onAddToManaged?: (host: DiscoveredHost) => void;
}

export default function ScanDetailModal({ 
  scan, 
  open, 
  onClose,
  onAddToManaged 
}: ScanDetailModalProps) {
  const [hosts, setHosts] = useState<DiscoveredHost[]>([]);
  const [loading, setLoading] = useState(false);
  const [addingHosts, setAddingHosts] = useState<Set<string>>(new Set());
  const [addedHosts, setAddedHosts] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (open && scan) {
      loadScanResults();
    }
  }, [open, scan]);

  const loadScanResults = async () => {
    if (!scan) return;
    
    setLoading(true);
    try {
      const results = await discoveryApi.getScanResults(scan.id, false);
      const hosts = results.hosts.map(h => ({ ...h, added_to_hosts: false })) as DiscoveredHost[];
      setHosts(hosts);
      
      const alreadyAdded = new Set(
        hosts.filter(h => h.added_to_hosts).map(h => h.id)
      );
      setAddedHosts(alreadyAdded);
    } catch (error) {
      console.error('Failed to load scan results:', error);
      toast.error('Failed to load scan results');
    } finally {
      setLoading(false);
    }
  };

  const handleAddToManaged = async (host: DiscoveredHost) => {
    if (addedHosts.has(host.id) || addingHosts.has(host.id)) return;

    setAddingHosts(prev => new Set(prev).add(host.id));
    
    try {
      await hostApi.addHost({
        name: host.hostname || host.ip_address,
        ip_address: host.ip_address,
        ports: host.ports.filter(p => p.status === 'open').map(p => p.port),
        services: host.ports.filter(p => p.service).map(p => p.service!) || [],
      });
      
      setAddedHosts(prev => new Set(prev).add(host.id));
      toast.success(`Added ${host.ip_address} to managed hosts`);
      
      if (onAddToManaged) {
        onAddToManaged(host);
      }
    } catch (error) {
      console.error('Failed to add host:', error);
      toast.error('Failed to add host to managed list');
    } finally {
      setAddingHosts(prev => {
        const next = new Set(prev);
        next.delete(host.id);
        return next;
      });
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (!scan) return null;

  const aliveHosts = hosts.filter(h => h.status === 'alive');
  const totalOpenPorts = aliveHosts.reduce((sum, h) => 
    sum + h.ports.filter(p => p.status === 'open').length, 0
  );

  return (
    <Dialog open={open} onClose={onClose} className="max-w-4xl">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Scan className="h-5 w-5" />
          Scan Details
        </DialogTitle>
        <DialogDescription>
          Scan ID: {scan.id} • Created by: {scan.created_by}
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-6 mt-4">
        {/* Scan Configuration */}
        <div className="grid grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
          <div>
            <label className="text-sm font-medium text-muted-foreground">Status</label>
            <div className="mt-1">
              <Badge 
                variant={scan.status === 'completed' ? 'success' : scan.status === 'failed' ? 'destructive' : 'pending'}
                className="capitalize"
              >
                {scan.status}
              </Badge>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Progress</label>
            <div className="mt-1 flex items-center gap-2">
              <Progress value={scan.progress} className="flex-1 h-2" />
              <span className="text-sm">{scan.progress}%</span>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Started</label>
            <p className="text-sm">{formatDate(scan.started_at)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Completed</label>
            <p className="text-sm">{scan.completed_at ? formatDate(scan.completed_at) : '—'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Hosts Scanned</label>
            <p className="text-sm">{scan.scanned_hosts} / {scan.total_hosts}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Hosts Found</label>
            <p className="text-sm text-green-600 font-medium">{scan.found_hosts}</p>
          </div>
        </div>

        {scan.error_message && (
          <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm text-destructive font-medium">Error occurred during scan:</p>
            <p className="text-sm text-destructive/80 mt-1">{scan.error_message}</p>
          </div>
        )}

        {/* Discovered Hosts */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Server className="h-4 w-4" />
            Discovered Hosts
            <Badge variant="secondary">{aliveHosts.length}</Badge>
          </h3>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : aliveHosts.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground border rounded-lg">
              <Globe className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No hosts discovered</p>
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3 font-medium">Host</th>
                    <th className="text-left p-3 font-medium">Open Ports</th>
                    <th className="text-left p-3 font-medium">Services</th>
                    <th className="text-left p-3 font-medium">Response Time</th>
                    <th className="text-right p-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {aliveHosts.map((host) => {
                    const openPorts = host.ports.filter(p => p.status === 'open');
                    const isAdding = addingHosts.has(host.id);
                    const isAdded = addedHosts.has(host.id) || host.added_to_hosts;

                    return (
                      <tr key={host.id} className="hover:bg-muted/30">
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <Server className="h-4 w-4 text-muted-foreground" />
                            <div>
                              <p className="font-medium">{host.ip_address}</p>
                              {host.hostname && (
                                <p className="text-xs text-muted-foreground">{host.hostname}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex flex-wrap gap-1">
                            {openPorts.slice(0, 5).map(port => (
                              <Badge key={port.port} variant="outline" className="text-xs">
                                <CheckCircle className="h-3 w-3 mr-1" />
                                {port.port}
                              </Badge>
                            ))}
                            {openPorts.length > 5 && (
                              <Badge variant="outline" className="text-xs">
                                +{openPorts.length - 5}
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex flex-wrap gap-1">
                            {openPorts
                              .filter(p => p.service)
                              .slice(0, 3)
                              .map((port, idx) => (
                                <Badge key={idx} variant="secondary" className="text-xs">
                                  {port.service}
                                </Badge>
                              ))}
                          </div>
                        </td>
                        <td className="p-3">
                          {host.response_time_ms ? (
                            <span className="flex items-center gap-1 text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              {host.response_time_ms}ms
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="p-3 text-right">
                          <Button
                            size="sm"
                            variant={isAdded ? 'secondary' : 'default'}
                            disabled={isAdded || isAdding}
                            onClick={() => handleAddToManaged(host)}
                            className="gap-1"
                          >
                            {isAdding ? (
                              <>
                                <Loader2 className="h-3 w-3 animate-spin" />
                                Adding...
                              </>
                            ) : isAdded ? (
                              <>
                                <CheckCircle className="h-3 w-3" />
                                Added
                              </>
                            ) : (
                              <>
                                <Plus className="h-3 w-3" />
                                Add
                              </>
                            )}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {!loading && aliveHosts.length > 0 && (
            <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Total open ports discovered: <strong>{totalOpenPorts}</strong>
              </span>
              <span>
                {addedHosts.size} of {aliveHosts.length} hosts added to managed list
              </span>
            </div>
          )}
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
