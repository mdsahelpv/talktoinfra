import { useState } from 'react';
import {
  Play,
  CheckCircle,
  XCircle,
  Eye,
  Terminal,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  Card,
  CardContent,
  Button,
  Badge,
  Spinner,
  Input,
} from '@/components/ui';
import { useActions, useExecuteAction } from '@/hooks/useActions';
import { cn, formatDate } from '@/utils';

const statusFilters = ['all', 'pending', 'approved', 'rejected', 'executing', 'completed', 'failed'];

export default function ActionsPage() {
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const { data: actions, isLoading } = useActions(filter === 'all' ? undefined : filter);
  const executeMutation = useExecuteAction();

  const filteredActions = actions?.filter((action) =>
    action.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    action.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDryRun = async (actionId: string) => {
    try {
      await executeMutation.mutateAsync({ id: actionId, dryRun: true });
      toast.success('Dry run executed successfully');
    } catch (error) {
      toast.error('Dry run failed');
    }
  };

  const handleExecute = async (actionId: string) => {
    try {
      await executeMutation.mutateAsync({ id: actionId, dryRun: false });
      toast.success('Action executed successfully');
    } catch (error) {
      toast.error('Action execution failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Actions</h1>
          <p className="text-sm text-muted-foreground">
            Manage and execute infrastructure operations
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search actions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-2 sm:pb-0">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {statusFilters.map((status) => (
            <Button
              key={status}
              variant={filter === status ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter(status)}
              className="capitalize whitespace-nowrap"
            >
              {status}
            </Button>
          ))}
        </div>
      </div>

      {/* Actions List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : filteredActions && filteredActions.length > 0 ? (
        <div className="space-y-4">
          {filteredActions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              onDryRun={() => handleDryRun(action.id)}
              onExecute={() => handleExecute(action.id)}
              isExecuting={executeMutation.isPending}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Terminal className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No actions found</h3>
          <p className="text-sm text-muted-foreground">
            Try adjusting your filters or search query
          </p>
        </div>
      )}
    </div>
  );
}

interface ActionCardProps {
  action: {
    id: string;
    type: string;
    name: string;
    description: string;
    status: string;
    requires_approval: boolean;
    created_at: string;
  };
  onDryRun: () => void;
  onExecute: () => void;
  isExecuting: boolean;
}

function ActionCard({ action, onDryRun, onExecute, isExecuting }: ActionCardProps) {
  const [expanded, setExpanded] = useState(false);

  const statusConfig = {
    pending: { variant: 'pending' as const, icon: Play },
    approved: { variant: 'default' as const, icon: CheckCircle },
    rejected: { variant: 'destructive' as const, icon: XCircle },
    executing: { variant: 'pending' as const, icon: Spinner },
    completed: { variant: 'success' as const, icon: CheckCircle },
    failed: { variant: 'destructive' as const, icon: XCircle },
  };

  const config = statusConfig[action.status as keyof typeof statusConfig] || statusConfig.pending;
  const StatusIcon = config.icon;

  return (
    <Card className={cn('overflow-hidden', action.status === 'executing' && 'border-primary')}>
      <CardContent className="p-0">
        <div
          className="flex items-center gap-4 p-4 cursor-pointer hover:bg-accent/50"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="rounded-full bg-primary/10 p-2">
            <StatusIcon className="h-4 w-4 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold truncate">{action.name}</h3>
              <Badge variant={config.variant}>{action.status}</Badge>
              {action.requires_approval && (
                <Badge variant="warning">Approval Required</Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground truncate">
              {action.description}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground hidden sm:block">
              {formatDate(action.created_at)}
            </span>
            <Button variant="ghost" size="icon" className="shrink-0">
              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        {expanded && (
          <div className="border-t px-4 py-4 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Type</p>
                <p className="capitalize">{action.type}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Created</p>
                <p>{formatDate(action.created_at)}</p>
              </div>
            </div>

            {action.status === 'pending' && !action.requires_approval && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDryRun();
                  }}
                  disabled={isExecuting}
                >
                  <Eye className="mr-2 h-4 w-4" />
                  Dry Run
                </Button>
                <Button
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onExecute();
                  }}
                  disabled={isExecuting}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Execute
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
