import { apiClient } from './client';
import type { Workflow, WorkflowExecution, WorkflowTemplate, WorkflowListResponse, ExecutionListResponse } from '@/types';

export const workflowApi = {
    // List workflows
    listWorkflows(params?: { page?: number; limit?: number; status?: string }) {
        const queryParams = new URLSearchParams();
        if (params?.page) queryParams.append('page', params.page.toString());
        if (params?.limit) queryParams.append('limit', params.limit.toString());
        if (params?.status) queryParams.append('status', params.status);
        const query = queryParams.toString();
        return apiClient.get<WorkflowListResponse>(`/workflows${query ? `?${query}` : ''}`);
    },

    // Get single workflow
    getWorkflow(id: string) {
        return apiClient.get<Workflow>(`/workflows/${id}`);
    },

    // Create workflow
    createWorkflow(workflow: Partial<Workflow>) {
        return apiClient.post<Workflow>('/workflows', workflow);
    },

    // Update workflow
    updateWorkflow(id: string, workflow: Partial<Workflow>) {
        return apiClient.put<Workflow>(`/workflows/${id}`, workflow);
    },

    // Delete workflow
    deleteWorkflow(id: string) {
        return apiClient.delete(`/workflows/${id}`);
    },

    // Execute workflow synchronously
    executeWorkflow(id: string, inputs: Record<string, unknown>) {
        return apiClient.post<WorkflowExecution>(`/workflows/${id}/execute`, inputs);
    },

    // Execute workflow asynchronously
    executeWorkflowAsync(id: string) {
        return apiClient.post<WorkflowExecution>(`/workflows/${id}/execute-async`);
    },

    // Get execution status
    getExecutionStatus(executionId: string) {
        return apiClient.get<WorkflowExecution>(`/executions/${executionId}/status`);
    },

    // List executions for a workflow
    listExecutions(workflowId: string, params?: { page?: number; limit?: number }) {
        const queryParams = new URLSearchParams();
        if (params?.page) queryParams.append('page', params.page.toString());
        if (params?.limit) queryParams.append('limit', params.limit.toString());
        const query = queryParams.toString();
        return apiClient.get<ExecutionListResponse>(`/workflows/${workflowId}/executions${query ? `?${query}` : ''}`);
    },

    // Get single execution
    getExecution(executionId: string) {
        return apiClient.get<WorkflowExecution>(`/executions/${executionId}`);
    },

    // Cancel execution
    cancelExecution(executionId: string) {
        return apiClient.post<WorkflowExecution>(`/executions/${executionId}/cancel`);
    },

    // Rollback execution
    rollbackExecution(executionId: string, targetStepId?: string) {
        return apiClient.post<WorkflowExecution>(`/executions/${executionId}/rollback`, { target_step_id: targetStepId });
    },

    // List templates
    listTemplates() {
        return apiClient.get<WorkflowTemplate[]>('/workflow-templates');
    },

    // Get single template
    getTemplate(id: string) {
        return apiClient.get<WorkflowTemplate>(`/workflow-templates/${id}`);
    },

    // Create workflow from template
    createFromTemplate(templateId: string, name: string) {
        return apiClient.post<Workflow>('/workflow-templates/create', { template_id: templateId, name });
    },
};
