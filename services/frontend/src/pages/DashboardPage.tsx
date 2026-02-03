import {
  MessageSquare,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  Activity,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Badge, Spinner } from '@/components/ui';
import { useDashboardStats, useRecentActivity } from '@/hooks/useDashboard';
import { formatRelativeTime } from '@/utils';

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: activities, isLoading: activityLoading } = useRecentActivity();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Overview of your infrastructure operations
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Conversations"
          value={stats?.total_conversations || 0}
          icon={MessageSquare}
          isLoading={statsLoading}
        />
        <StatCard
          title="Completed Actions"
          value={stats?.completed_actions || 0}
          icon={CheckCircle}
          trend={stats?.completed_actions ? '+12%' : undefined}
          isLoading={statsLoading}
        />
        <StatCard
          title="Pending Approvals"
          value={stats?.pending_approvals || 0}
          icon={Clock}
          variant="warning"
          isLoading={statsLoading}
        />
        <StatCard
          title="Failed Actions"
          value={stats?.failed_actions || 0}
          icon={XCircle}
          variant={stats?.failed_actions && stats.failed_actions > 0 ? 'danger' : 'default'}
          isLoading={statsLoading}
        />
      </div>

      {/* Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {activityLoading ? (
              <div className="flex items-center justify-center py-8">
                <Spinner />
              </div>
            ) : activities && activities.length > 0 ? (
              <div className="space-y-4">
                {activities.map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-8">
                No recent activity
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ElementType;
  trend?: string;
  variant?: 'default' | 'warning' | 'danger';
  isLoading?: boolean;
}

function StatCard({ title, value, icon: Icon, trend, variant = 'default', isLoading }: StatCardProps) {
  const variants = {
    default: 'bg-card',
    warning: 'bg-yellow-500/5 border-yellow-500/20',
    danger: 'bg-red-500/5 border-red-500/20',
  };

  return (
    <Card className={variants[variant]}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            {isLoading ? (
              <div className="mt-2">
                <Spinner size="sm" />
              </div>
            ) : (
              <div className="flex items-baseline gap-2">
                <h3 className="text-3xl font-bold">{value}</h3>
                {trend && (
                  <span className="flex items-center text-xs text-green-500">
                    <TrendingUp className="mr-1 h-3 w-3" />
                    {trend}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="rounded-full bg-primary/10 p-3">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityItem({ activity }: { activity: { id: string; type: string; description: string; timestamp: string; user?: string } }) {
  const icons = {
    message: MessageSquare,
    action: Play,
    approval: CheckCircle,
  };

  const Icon = icons[activity.type as keyof typeof icons] || Activity;
  const variant = activity.type === 'action' ? 'default' : activity.type === 'approval' ? 'success' : 'secondary';

  return (
    <div className="flex items-start gap-4 rounded-lg border p-4">
      <div className="rounded-full bg-primary/10 p-2">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium">{activity.description}</p>
        <div className="flex items-center gap-2 mt-1">
          <Badge variant={variant as 'default' | 'secondary' | 'success'}>
            {activity.type}
          </Badge>
          {activity.user && (
            <span className="text-xs text-muted-foreground">
              by {activity.user}
            </span>
          )}
        </div>
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {formatRelativeTime(activity.timestamp)}
      </span>
    </div>
  );
}
