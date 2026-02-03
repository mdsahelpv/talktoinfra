import React, { useState, useEffect } from 'react';
import { History, Trash2, ChevronRight, AlertCircle, CheckCircle2, Loader2, XCircle, Calendar, Filter } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, Progress } from '@/components/ui';
import Pagination from '@/components/ui/Pagination';
import type { ScanJob } from '@/types';

interface ScanHistoryListProps {
  scans: ScanJob[];
  onViewScan: (scan: ScanJob) => void;
  onDeleteScan: (scanId: string) => void;
  loading?: boolean;
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; variant: 'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'pending'; label: string }> = {
  pending: { icon: <Loader2 className="h-3 w-3 animate-spin" />, variant: 'pending', label: 'Pending' },
  running: { icon: <Loader2 className="h-3 w-3 animate-spin" />, variant: 'pending', label: 'Running' },
  completed: { icon: <CheckCircle2 className="h-3 w-3" />, variant: 'success', label: 'Completed' },
  failed: { icon: <XCircle className="h-3 w-3" />, variant: 'destructive', label: 'Failed' },
};

export default function ScanHistoryList({ 
  scans, 
  onViewScan, 
  onDeleteScan,
  loading = false 
}: ScanHistoryListProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const itemsPerPage = 10;

  const filteredScans = scans.filter(scan => 
    statusFilter === 'all' || scan.status === statusFilter
  );

  const totalPages = Math.ceil(filteredScans.length / itemsPerPage);
  const paginatedScans = filteredScans.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (start: string, end?: string) => {
    if (!end) return 'In progress';
    const duration = new Date(end).getTime() - new Date(start).getTime();
    const minutes = Math.floor(duration / 60000);
    const seconds = Math.floor((duration % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Scan History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          Scan History
          <Badge variant="secondary">{filteredScans.length}</Badge>
        </CardTitle>
        
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-sm border rounded-md px-2 py-1 bg-background"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </CardHeader>
      
      <CardContent>
        {paginatedScans.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No scans found</p>
            {statusFilter !== 'all' && (
              <p className="text-sm mt-1">Try changing the status filter</p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {paginatedScans.map((scan) => {
              const statusConfig = STATUS_CONFIG[scan.status] || STATUS_CONFIG.pending;
              
              return (
                <div
                  key={scan.id}
                  className="flex items-center gap-4 p-4 rounded-lg border hover:bg-accent/50 transition-colors cursor-pointer group"
                  onClick={() => onViewScan(scan)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={statusConfig.variant} className="gap-1">
                        {statusConfig.icon}
                        {statusConfig.label}
                      </Badge>
                      
                      {scan.status === 'running' && (
                        <span className="text-sm text-muted-foreground">
                          {scan.progress}%
                        </span>
                      )}
                    </div>
                    
                    {scan.status === 'running' && (
                      <Progress value={scan.progress} className="h-1 mb-2" />
                    )}
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        Started: {formatDate(scan.started_at)}
                      </span>
                      
                      {scan.completed_at && (
                        <span>
                          Duration: {formatDuration(scan.started_at, scan.completed_at)}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-4 mt-2 text-sm">
                      <span>Hosts: {scan.scanned_hosts}/{scan.total_hosts}</span>
                      <span className="text-green-600">Found: {scan.found_hosts}</span>
                      {scan.error_message && (
                        <span className="text-destructive flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          Error occurred
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteScan(scan.id);
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
        
        {totalPages > 1 && (
          <div className="mt-6">
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={setCurrentPage}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
