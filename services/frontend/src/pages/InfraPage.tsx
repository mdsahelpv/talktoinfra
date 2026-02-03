import { useEffect, useState } from 'react';
import { Server, Activity, Cpu, MemoryStick, Database, Globe, CheckCircle, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { apiClient } from '@/api/client';
import { cn } from '@/utils';
import { useRequireAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/stores';

interface InfraService {
  id: string;
  name: string;
  type: string;
  cluster: string;
  namespace: string;
  status: string;
  replicas: number;
  endpoint?: string;
  health?: Record<string, unknown>;
  error?: string;
}

interface InfraContainer {
  name: string;
  status: string;
  ports: string;
  type: string;
}

interface InfraResources {
  compute: {
    total_cpu_cores?: number;
    cpu_usage_percent?: number;
    total_memory_gb?: number;
    used_memory_gb?: number;
    memory_usage_percent?: number;
    total_storage_gb?: number;
    used_storage_gb?: number;
    storage_usage_percent?: number;
    error?: string;
    details?: string;
  };
  network: {
    [key: string]: unknown;
  };
}

interface InfrastructureData {
  environment: string;
  services: InfraService[];
  infrastructure_containers: InfraContainer[];
  resources: InfraResources;
  summary: {
    total_services: number;
    healthy_services: number;
    unhealthy_services: number;
    infrastructure_containers: number;
    last_updated: string;
  };
}

export default function InfraPage() {
  // Ensure user is authenticated before making API calls
  const isAuthenticated = useRequireAuth();
  const { isLoading: authLoading } = useAuthStore();
  const [infraData, setInfraData] = useState<InfrastructureData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Show loading spinner while auth is being rehydrated
  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  useEffect(() => {
    // Only fetch if authenticated
    if (!isAuthenticated) return;

    const fetchInfrastructure = async () => {
      try {
        const data = await apiClient.get<InfrastructureData>('/api/v1/infra');
        setInfraData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load infrastructure data');
      } finally {
        setLoading(false);
      }
    };

    fetchInfrastructure();
  }, [isAuthenticated]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  if (!infraData) return null;

  const { services, infrastructure_containers, resources, summary } = infraData;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Infrastructure</h1>
          <p className="text-muted-foreground">
            Overview of infrastructure known to the AI system
          </p>
        </div>
        <div className="text-sm text-muted-foreground">
          Environment: {infraData.environment}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Services</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.total_services}</div>
            <p className="text-xs text-muted-foreground">
              {summary.healthy_services} healthy, {summary.unhealthy_services} unhealthy
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Containers</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.infrastructure_containers}</div>
            <p className="text-xs text-muted-foreground">
              Infrastructure services
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {resources.compute?.cpu_usage_percent !== undefined
                ? `${Math.round(resources.compute.cpu_usage_percent)}%`
                : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              {resources.compute?.total_cpu_cores
                ? `${resources.compute.total_cpu_cores} cores`
                : 'Unable to query'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
            <MemoryStick className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {resources.compute?.memory_usage_percent !== undefined
                ? `${Math.round(resources.compute.memory_usage_percent)}%`
                : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              {resources.compute?.total_memory_gb
                ? `${resources.compute.total_memory_gb} GB total`
                : 'Unable to query'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Services Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Services</h2>
        <div className="grid gap-4">
          {services.map((service) => (
            <Card key={service.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{service.name}</h3>
                      <div className={cn(
                        "px-2 py-0.5 rounded-full text-xs font-medium",
                        service.status === 'healthy' || service.status === 'running'
                          ? 'bg-green-100 text-green-700'
                          : service.status === 'unhealthy'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                      )}>
                        {service.status}
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {service.cluster} / {service.namespace} • {service.type} • {service.replicas} replica{service.replicas !== 1 ? 's' : ''}
                    </div>
                    {service.error && (
                      <div className="text-xs text-red-500">{service.error}</div>
                    )}
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    {service.endpoint && (
                      <div className="text-xs">{service.endpoint}</div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          {services.length === 0 && (
            <p className="text-muted-foreground text-center py-8">No services found</p>
          )}
        </div>
      </div>

      {/* Infrastructure Containers Section */}
      {infrastructure_containers.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Infrastructure Containers</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {infrastructure_containers.map((container, idx) => (
              <Card key={idx}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{container.name}</p>
                      <p className="text-sm text-muted-foreground">{container.status}</p>
                    </div>
                    <Database className="h-4 w-4 text-muted-foreground" />
                  </div>
                  {container.ports && (
                    <p className="text-xs text-muted-foreground mt-2">{container.ports}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Resources Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Resource Overview</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Cpu className="h-4 w-4" />
                Compute Resources
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {resources.compute?.error ? (
                <p className="text-sm text-muted-foreground">{resources.compute.error}</p>
              ) : (
                <>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">CPU</span>
                      <span className="font-medium">
                        {resources.compute?.cpu_usage_percent
                          ? `${Math.round(resources.compute.cpu_usage_percent)}%`
                          : 'N/A'}
                      </span>
                    </div>
                    {resources.compute?.cpu_usage_percent && (
                      <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{ width: `${resources.compute.cpu_usage_percent}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Memory</span>
                      <span className="font-medium">
                        {resources.compute?.used_memory_gb && resources.compute?.total_memory_gb
                          ? `${resources.compute.used_memory_gb} / ${resources.compute.total_memory_gb} GB`
                          : 'N/A'}
                      </span>
                    </div>
                    {resources.compute?.memory_usage_percent && (
                      <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{ width: `${resources.compute.memory_usage_percent}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Storage</span>
                      <span className="font-medium">
                        {resources.compute?.used_storage_gb && resources.compute?.total_storage_gb
                          ? `${resources.compute.used_storage_gb} / ${resources.compute.total_storage_gb} GB`
                          : 'N/A'}
                      </span>
                    </div>
                    {resources.compute?.storage_usage_percent && (
                      <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{ width: `${resources.compute.storage_usage_percent}%` }}
                        />
                      </div>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Globe className="h-4 w-4" />
                System Info
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm">
                <p className="text-muted-foreground">Last Updated</p>
                <p className="font-medium">
                  {summary.last_updated
                    ? new Date(summary.last_updated).toLocaleString()
                    : 'N/A'}
                </p>
              </div>
              <div className="text-sm">
                <p className="text-muted-foreground">Environment</p>
                <p className="font-medium capitalize">{infraData.environment}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
