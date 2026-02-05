/** Cost Management TypeScript Types */

export type CloudProvider = 'aws' | 'azure' | 'gcp' | 'kubernetes';

export type RecommendationType =
    | 'right_size'
    | 'spot_instance'
    | 'reserved_instance'
    | 'delete_idle'
    | 'storage_optimize'
    | 'network_optimize';

export type RecommendationPriority = 'critical' | 'high' | 'medium' | 'low';

export type PricingModelType = 'on_demand' | 'reserved_1_year' | 'reserved_3_year' | 'spot';

// Cost Record Types
export interface CostRecord {
    id: string;
    cluster_id?: string;
    cloud_provider: CloudProvider;
    account_id?: string;
    account_name?: string;
    region?: string;
    availability_zone?: string;
    service_name?: string;
    resource_type?: string;
    resource_id?: string;
    resource_name?: string;
    cost_amount: number;
    currency: string;
    usage_quantity?: number;
    usage_unit?: string;
    operation?: string;
    description?: string;
    tags?: Record<string, string>;
    usage_start: string;
    usage_end?: string;
    created_at: string;
    updated_at: string;
}

// Cost Summary
export interface CostSummary {
    total_cost: number;
    currency: string;
    period_start: string;
    period_end: string;
    resource_count: number;
    previous_period_cost?: number;
    cost_change_percent?: number;
}

// Cost by Dimension
export interface CostByDimension {
    dimension: string;
    dimension_value: string;
    total_cost: number;
    percentage: number;
    resource_count: number;
}

// Cost Trend Point
export interface CostTrendPoint {
    timestamp: string;
    cost: number;
}

// Budget Types
export interface Budget {
    id: string;
    name: string;
    description?: string;
    cloud_provider?: CloudProvider;
    cluster_id?: string;
    namespace?: string;
    amount: number;
    currency: string;
    period: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
    start_date: string;
    end_date?: string;
    alert_thresholds?: number[];
    notify_email?: string[];
    notify_slack?: string[];
    notify_pagerduty?: string[];
    current_spend: number;
    percentage_used: number;
    is_active: boolean;
    last_alert_at?: string;
    created_at: string;
    updated_at: string;
}

// Budget Alert
export interface BudgetAlert {
    id: string;
    budget_id: string;
    budget_name: string;
    alert_type: string;
    threshold_percent: number;
    spend_amount: number;
    budget_amount: number;
    percentage_used: number;
    status: string;
    triggered_at: string;
    acknowledged_at?: string;
}

// Budget Summary
export interface BudgetSummary {
    total_budgets: number;
    active_budgets: number;
    inactive_budgets: number;
    total_budget_amount: number;
    total_spend: number;
    utilization_percent: number;
    active_alerts: number;
    budgets_near_limit: number;
    budgets_exceeded: number;
}

// Resource Specification for Estimation
export interface ResourceSpec {
    cpu_cores: number;
    memory_gb: number;
    storage_gb?: number;
    storage_type?: string;
    monthly_network_egress_gb?: number;
    monthly_requests?: number;
    operating_system: string;
    instance_family?: string;
    instance_name?: string;
}

// Cost Estimate Request
export interface CostEstimateRequest {
    resource_spec: ResourceSpec;
    cloud_provider: CloudProvider;
    region: string;
    pricing_model: PricingModelType;
    term_length?: string;
    payment_option?: string;
}

// Cost Estimate Response
export interface CostEstimateResponse {
    id: string;
    cloud_provider: CloudProvider;
    region: string;
    pricing_model: string;
    resource_spec: ResourceSpec;
    hourly_cost: number;
    daily_cost: number;
    monthly_cost: number;
    yearly_cost: number;
    currency: string;
    compute_cost: number;
    storage_cost: number;
    network_cost: number;
    other_costs: number;
    on_demand_hourly: number;
    savings_with_pricing_model?: number;
    savings_percentage?: number;
    alternatives?: Alternative[];
    created_at: string;
    expires_at?: string;
}

// Alternative
export interface Alternative {
    instance_type: string;
    description: string;
    hourly_cost: number;
    monthly_cost: number;
    savings_percent: number;
}

// Recommendation Types
export interface Recommendation {
    id: string;
    cluster_id?: string;
    cloud_provider: CloudProvider;
    resource_type?: string;
    resource_id?: string;
    resource_name?: string;
    recommendation_type: RecommendationType;
    title: string;
    description: string;
    current_cost?: number;
    estimated_savings?: number;
    priority: RecommendationPriority;
    status: 'pending' | 'approved' | 'dismissed' | 'implemented';
    action_steps?: string[];
    risks?: string[];
    utilization_data?: Record<string, unknown>;
    right_sizing_data?: Record<string, unknown>;
    created_at: string;
    updated_at: string;
    reviewed_at?: string;
}

// Recommendation Summary
export interface RecommendationSummary {
    total_recommendations: number;
    total_potential_savings_monthly: number;
    total_potential_savings_yearly: number;
    by_priority: Record<string, { count: number; savings: number }>;
    by_type: Record<string, { count: number; savings: number }>;
    by_status: Record<string, number>;
    critical_count: number;
    high_count: number;
}

// Dashboard Overview
export interface CostDashboardOverview {
    total_cost: number;
    currency: string;
    period: string;
    period_start: string;
    period_end: string;
    previous_period_cost: number;
    cost_change_percent: number;
    cost_by_provider: Record<string, number>;
    cost_by_cluster: Record<string, number>;
    top_resources: TopResource[];
    active_budgets: number;
    budgets_near_limit: number;
    budgets_exceeded: number;
}

// Top Resource
export interface TopResource {
    resource_id: string;
    resource_name?: string;
    resource_type?: string;
    service_name?: string;
    cloud_provider?: CloudProvider;
    region?: string;
    total_cost: number;
    usage_hours: number;
}

// Time Series Data Point
export interface TimeSeriesDataPoint {
    timestamp: string;
    value: number;
    label?: string;
}

// Time Series Data
export interface TimeSeriesData {
    metric: string;
    provider?: CloudProvider;
    unit: string;
    data_points: TimeSeriesDataPoint[];
}

// Idle Resource
export interface IdleResource {
    resource_id: string;
    resource_name?: string;
    resource_type?: string;
    service_name?: string;
    cloud_provider?: CloudProvider;
    region?: string;
    cluster_id?: string;
    total_cost: number;
    usage_records: number;
    potential_savings: number;
    recommendation_type: string;
}

// Right Sizing Opportunity
export interface RightSizingOpportunity {
    resource_id: string;
    resource_name?: string;
    resource_type?: string;
    service_name?: string;
    cloud_provider?: CloudProvider;
    region?: string;
    current_monthly_cost: number;
    recommended_action: string;
    estimated_savings_percent: number;
    recommendation_type: string;
}

// Pricing Model Info
export interface PricingModelInfo {
    description: string;
    best_for: string;
    flexibility: string;
    savings: string;
}
