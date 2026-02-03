import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  Search,
  AlertCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Spinner,
  Input,
} from '@/components/ui';
import { useActions, useApproveAction, useRejectAction } from '@/hooks/useActions';
import { useAuthStore } from '@/stores';
import { formatDate } from '@/utils';

export default function ApprovalsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const { data: pendingActions, isLoading } = useActions('pending');
  const { data: allActions } = useActions();
  const approveMutation = useApproveAction();
  const rejectMutation = useRejectAction();
  const { user } = useAuthStore();

  const filteredPending = pendingActions?.filter((action) =>
    action.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    action.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const recentApprovals = allActions?.filter(
    (action) => action.status === 'approved' || action.status === 'rejected'
  ).slice(0, 5);

  const handleApprove = async (actionId: string) => {
    if (!user) return;
    try {
      await approveMutation.mutateAsync(actionId);
      toast.success('Action approved');
    } catch (error) {
      toast.error('Failed to approve action');
    }
  };

  const handleReject = async (actionId: string) => {
    try {
      await rejectMutation.mutateAsync(actionId);
      toast.success('Action rejected');
    } catch (error) {
      toast.error('Failed to reject action');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Approvals</h1>
        <p className="text-sm text-muted-foreground">
          Review and approve infrastructure operations
        </p>
      </div>

      {/* Pending Approvals */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Pending Approvals
            {filteredPending && filteredPending.length > 0 && (
              <Badge variant="warning">{filteredPending.length}</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search pending approvals..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : filteredPending && filteredPending.length > 0 ? (
            <div className="space-y-4">
              {filteredPending.map((action) => (
                <PendingActionCard
                  key={action.id}
                  action={action}
                  onApprove={() => handleApprove(action.id)}
                  onReject={() => handleReject(action.id)}
                  isProcessing={approveMutation.isPending || rejectMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <AlertCircle className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">No pending approvals</h3>
              <p className="text-sm text-muted-foreground">
                All actions have been reviewed
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Decisions */}
      {recentApprovals && recentApprovals.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Recent Decisions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentApprovals.map((action) => (
                <div
                  key={action.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={action.status === 'approved' ? 'success' : 'destructive'}
                    >
                      {action.status}
                    </Badge>
                    <div>
                      <p className="font-medium">{action.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {action.description}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(action.created_at)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface PendingActionCardProps {
  action: {
    id: string;
    name: string;
    description: string;
    type: string;
    created_at: string;
  };
  onApprove: () => void;
  onReject: () => void;
  isProcessing: boolean;
}

function PendingActionCard({ action, onApprove, onReject, isProcessing }: PendingActionCardProps) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="rounded-lg border p-4 space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-yellow-500/10 p-2">
            <Clock className="h-4 w-4 text-yellow-500" />
          </div>
          <div>
            <h3 className="font-semibold">{action.name}</h3>
            <p className="text-sm text-muted-foreground">{action.description}</p>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="outline" className="capitalize">
                {action.type}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {formatDate(action.created_at)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onReject}
            disabled={isProcessing}
          >
            <XCircle className="mr-2 h-4 w-4" />
            Reject
          </Button>
          <Button
            size="sm"
            onClick={onApprove}
            disabled={isProcessing}
          >
            <CheckCircle className="mr-2 h-4 w-4" />
            Approve
          </Button>
        </div>
      </div>

      <Button
        variant="ghost"
        size="sm"
        className="w-full"
        onClick={() => setShowDetails(!showDetails)}
      >
        {showDetails ? 'Hide Details' : 'View Details'}
      </Button>

      {showDetails && (
        <div className="rounded-md bg-muted p-4 text-sm">
          <p className="font-medium mb-2">Action Details:</p>
          <p>Type: {action.type}</p>
          <p>ID: {action.id}</p>
          <p>Created: {formatDate(action.created_at)}</p>
        </div>
      )}
    </div>
  );
}
