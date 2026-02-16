export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'archived';
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'rolled_back';
export type StepType = 'action' | 'condition' | 'wait' | 'approval' | 'parallel' | 'notification';

export interface WorkflowStep {
    id: string;
    name: string;
    type: StepType;
    config: Record<string, unknown>;
    next_steps: Record<string, string>; // condition -> step_id
    on_failure: 'stop' | 'continue' | 'rollback';
}

export interface Workflow {
    id: string;
    name: string;
    description?: string;
    version: number;
    status: WorkflowStatus;
    steps: WorkflowStep[];
    inputs: Record<string, unknown>;
    created_at: string;
    updated_at: string;
}

export interface WorkflowExecution {
    id: string;
    workflow_id: string;
    status: ExecutionStatus;
    current_step_id?: string;
    inputs: Record<string, unknown>;
    outputs?: Record<string, unknown>;
    error?: string;
    started_at?: string;
    completed_at?: string;
    created_at: string;
    step_history?: WorkflowStepExecution[];
}

export interface WorkflowStepExecution {
    id: string;
    step_id: string;
    step_name: string;
    step_type: StepType;
    status: ExecutionStatus;
    inputs: Record<string, unknown>;
    outputs?: Record<string, unknown>;
    error?: string;
    started_at?: string;
    completed_at?: string;
}

export interface WorkflowTemplate {
    id: string;
    name: string;
    description: string;
    category: string;
    steps: WorkflowStep[];
}

export interface WorkflowListResponse {
    items: Workflow[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
}

export interface ExecutionListResponse {
    items: WorkflowExecution[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
}
