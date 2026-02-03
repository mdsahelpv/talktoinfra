import { useState, useMemo } from 'react';
import { Server, Activity, Clock, CheckCircle2, XCircle, AlertCircle, TrendingUp, TrendingDown, Minus, Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from '@/components/ui';
import { cn } from '@/utils';
import type { ManagedHost } from '@/types';

interface HealthDataPoint {
  timestamp: string;
  status: 'online' | 'offline' | 'unknown';
  response_time_ms?: number;
}

interface HostDetailViewProps {
  host: ManagedHost;
  healthHistory?: HealthDataPoint[];
  onAddToManaged?: () => void;
  onRemoveFromManaged?: () => void;
  className?: string;
}

type TimeRange = '24h' | '7d' | '30d';

const STATUS_ICONS = {
  online: <CheckCircle2 className="h-5 w-5 text-green-500" />,
  offline: <XCircle className="h-5 w-5 text-red-500" />,
  unknown: <AlertCircle className="h-5 w-5 text-yellow-500" />,
};

const STATUS_COLORS = {
  online: 'bg-green-500',
  offline: 'bg-red-500',
  unknown: 'bg-yellow-500',
};

export default function HostDetailView({ 
  host, 
  healthHistory = [],
  onAddToManaged,
  onRemoveFromManaged,
  className 
}: HostDetailViewProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');

  const filteredHistory = useMemo(() => {
    const now = new Date();
    const cutoff = new Date();
    
    switch (timeRange) {
      case '24h':
        cutoff.setHours(now.getHours() - 24);
        break;
      case '7d':
        cutoff.setDate(now.getDate() - 7);
        break;
      case '30d':
        cutoff.setDate(now.getDate() - 30);
        break;
    }
    
    return healthHistory.filter(h => new Date(h.timestamp) >= cutoff);
  }, [healthHistory, timeRange]);

  const stats = useMemo(() => {
    if (filteredHistory.length === 0) {
      return {
        uptime: 0,
        avgResponseTime: 0,
        minResponseTime: 0,
        maxResponseTime: 0,
        statusChanges: 0,
      };
    }

    const onlineCount = filteredHistory.filter(h => h.status === 'online').length;
    const uptime = (onlineCount / filteredHistory.length) * 100;
    
    const responseTimes = filteredHistory
      .filter(h => h.response_time_ms !== undefined)
      .map(h => h.response_time_ms!);
    
    const avgResponseTime = responseTimes.length > 0 
      ? Math.round(responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length)
      : 0;
    const minResponseTime = responseTimes.length > 0 ? Math.min(...responseTimes) : 0;
    const maxResponseTime = responseTimes.length > 0 ? Math.max(...responseTimes) : 0;

    let statusChanges = 0;
    for (let i = 1; i < filteredHistory.length; i++) {
      if (filteredHistory[i].status !== filteredHistory[i - 1].status) {
        statusChanges++;
      }
    }

    return {
      uptime,
      avgResponseTime,
      minResponseTime,
      maxResponseTime,
      statusChanges,
    };
  }, [filteredHistory]);

  const responseTimeTrend = useMemo(() => {
    if (filteredHistory.length < 2) return null;
    
    const mid = Math.floor(filteredHistory.length / 2);
    const firstHalf = filteredHistory.slice(0, mid);
    const secondHalf = filteredHistory.slice(mid);
    
    const firstAvg = firstHalf
      .filter(h => h.response_time_ms !== undefined)
      .reduce((sum, h) => sum + (h.response_time_ms || 0), 0) / firstHalf.length || 0;
    const secondAvg = secondHalf
      .filter(h => h.response_time_ms !== undefined)
      .reduce((sum, h) => sum + (h.response_time_ms || 0), 0) / secondHalf.length || 0;
    
    if (secondAvg > firstAvg * 1.1) return 'up';
    if (secondAvg < firstAvg * 0.9) return 'down';
    return 'stable';
  }, [filteredHistory]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Host Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary/10 rounded-lg">
                <Server className="h-8 w-8 text-primary" />
              </div>
              <div>
                <CardTitle className="text-xl">{host.name}</CardTitle>
                <p className="text-muted-foreground">{host.ip_address}</p>
                <div className="flex items-center gap-2 mt-2">
                  <Badge 
                    variant={host.status === 'online' ? 'default' : host.status === 'offline' ? 'destructive' : 'secondary'}
                    className="gap-1"
                  >
                    {STATUS_ICONS[host.status]}
                    {host.status.charAt(0).toUpperCase() + host.status.slice(1)}
                  </Badge>
                  {host.last_checked_at && (
                    <span className="text-xs text-muted-foreground">
                      Last checked: {formatDate(host.last_checked_at)}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            <div className="flex gap-2">
              {onAddToManaged && (
                <Button onClick={onAddToManaged} className="gap-1">
                  <Plus className="h-4 w-4" />
                  Add to Managed
                </Button>
              )}
              {onRemoveFromManaged && (
                <Button variant="destructive" onClick={onRemoveFromManaged} className="gap-1">
                  Remove
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground">Open Ports</p>
              <p className="text-2xl font-semibold">{host.ports.length}</p>
            </div>
            <div className="p-3 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground">Services</p>
              <p className="text-2xl font-semibold">{host.services.length}</p>
            </div>
            <div className="p-3 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground">Added</p>
              <p className="text-sm font-medium">{formatDate(host.added_at)}</p>
            </div>
            <div className="p-3 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground">Added By</p>
              <p className="text-sm font-medium">{host.added_by}</p>
            </div>
          </div>
          
          {host.services.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium mb-2">Detected Services:</p>
              <div className="flex flex-wrap gap-2">
                {host.services.map((service, idx) => (
                  <Badge key={idx} variant="outline">{service}</Badge>
                ))}
              </div>
            </div>
          )}
          
          {host.ports.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium mb-2">Open Ports:</p>
              <div className="flex flex-wrap gap-2">
                {host.ports.map((port) => (
                  <Badge key={port} variant="secondary">{port}</Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Health History */}
      {healthHistory.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Activity className="h-5 w-5" />
              Health History
            </CardTitle>
            
            <div className="flex gap-1">
              {(['24h', '7d', '30d'] as TimeRange[]).map((range) => (
                <Button
                  key={range}
                  variant={timeRange === range ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTimeRange(range)}
                >
                  {range === '24h' ? '24 Hours' : range === '7d' ? '7 Days' : '30 Days'}
                </Button>
              ))}
            </div>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-3 bg-muted/50 rounded-lg text-center">
                <p className="text-xs text-muted-foreground mb-1">Uptime</p>
                <p className={cn(
                  'text-xl font-semibold',
                  stats.uptime >= 99 ? 'text-green-600' : stats.uptime >= 95 ? 'text-yellow-600' : 'text-red-600'
                )}>
                  {stats.uptime.toFixed(1)}%
                </p>
              </div>
              
              <div className="p-3 bg-muted/50 rounded-lg text-center">
                <p className="text-xs text-muted-foreground mb-1">Avg Response</p>
                <div className="flex items-center justify-center gap-1">
                  <p className="text-xl font-semibold">{stats.avgResponseTime}ms</p>
                  {responseTimeTrend === 'up' && <TrendingUp className="h-4 w-4 text-red-500" />}
                  {responseTimeTrend === 'down' && <TrendingDown className="h-4 w-4 text-green-500" />}
                  {responseTimeTrend === 'stable' && <Minus className="h-4 w-4 text-yellow-500" />}
                </div>
              </div>
              
              <div className="p-3 bg-muted/50 rounded-lg text-center">
                <p className="text-xs text-muted-foreground mb-1">Min Response</p>
                <p className="text-xl font-semibold">{stats.minResponseTime}ms</p>
              </div>
              
              <div className="p-3 bg-muted/50 rounded-lg text-center">
                <p className="text-xs text-muted-foreground mb-1">Max Response</p>
                <p className="text-xl font-semibold">{stats.maxResponseTime}ms</p>
              </div>
              
              <div className="p-3 bg-muted/50 rounded-lg text-center">
                <p className="text-xs text-muted-foreground mb-1">Status Changes</p>
                <p className={cn(
                  'text-xl font-semibold',
                  stats.statusChanges === 0 ? 'text-green-600' : 'text-yellow-600'
                )}>
                  {stats.statusChanges}
                </p>
              </div>
            </div>

            {/* Simple Timeline */}
            <div>
              <p className="text-sm font-medium mb-3">Status Timeline</p>
              <div className="relative">
                <div className="flex items-center gap-1 h-8">
                  {filteredHistory.map((point, idx) => (
                    <div
                      key={idx}
                      className={cn(
                        'flex-1 h-full rounded-sm transition-all',
                        STATUS_COLORS[point.status]
                      )}
                      title={`${formatDate(point.timestamp)} - ${point.status}${point.response_time_ms ? ` (${point.response_time_ms}ms)` : ''}`}
                    />
                  ))}
                </div>
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>Oldest</span>
                  <span>Most Recent</span>
                </div>
              </div>
            </div>

            {/* Recent History Table */}
            <div>
              <p className="text-sm font-medium mb-3">Recent Checks</p>
              <div className="border rounded-lg overflow-hidden max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 sticky top-0">
                    <tr>
                      <th className="text-left p-2 font-medium">Time</th>
                      <th className="text-left p-2 font-medium">Status</th>
                      <th className="text-left p-2 font-medium">Response Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {filteredHistory.slice(-20).reverse().map((point, idx) => (
                      <tr key={idx} className="hover:bg-muted/30">
                        <td className="p-2 text-muted-foreground">
                          {new Date(point.timestamp).toLocaleTimeString()}
                        </td>
                        <td className="p-2">
                          <Badge 
                            variant={point.status === 'online' ? 'default' : point.status === 'offline' ? 'destructive' : 'secondary'}
                            className="text-xs"
                          >
                            {point.status}
                          </Badge>
                        </td>
                        <td className="p-2">
                          {point.response_time_ms ? (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {point.response_time_ms}ms
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
