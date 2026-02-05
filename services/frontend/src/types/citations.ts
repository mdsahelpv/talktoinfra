/**
 * Source Citation Types - Maps to backend source_citations.py
 */

export interface SourceCitation {
    id: string;
    type: string;
    name: string;
    description: string;
    retrieved_at: string;
    confidence: number;
    score: number;
    source: string;
    source_id: string;
    raw_data?: Record<string, unknown>;
    metadata?: SourceMetadata;
}

export interface SourceMetadata {
    discovered_at?: string;
    last_seen_at?: string;
    scan_job_id?: string;
}

export interface CitationSet {
    sources: SourceCitation[];
    retrieved_count: number;
    query_time_ms: number;
}

export interface SourceConfidence {
    high: number;
    medium: number;
    low: number;
    uncertain: number;
}

export interface UICitationCard {
    id: string;
    icon: string;
    name: string;
    type: string;
    description: string;
    confidence: number;
    confidence_label: 'High' | 'Medium' | 'Low' | 'Uncertain';
    source: string;
    retrieved_at: string;
    metadata?: SourceMetadata;
}

/**
 * Confidence thresholds
 */
export const CONFIDENCE_THRESHOLDS = {
    HIGH: 0.9,
    MEDIUM: 0.7,
    LOW: 0.5,
} as const;

/**
 * Resource type to icon mapping
 */
export const RESOURCE_TYPE_ICONS: Record<string, string> = {
    discovered_host: '🖥️',
    k8s_pod: '📦',
    k8s_deployment: '🚀',
    k8s_service: '🌐',
    k8s_node: '🧠',
    k8s_namespace: '📁',
    k8s_statefulset: '📋',
    k8s_daemonset: '⚙️',
    k8s_ingress: '🚪',
    k8s_configmap: '📝',
    k8s_secret: '🔒',
    k8s_pvc: '💾',
    aws_instance: '☁️',
    aws_rds: '🗄️',
    aws_elb: '⚖️',
    aws_s3: '📦',
    azure_vm: '☁️',
    azure_sql: '🗄️',
    gcp_instance: '☁️',
    gcp_sql: '🗄️',
    manual_entry: '✍️',
    unknown: '📄',
} as const;

/**
 * Source label mapping
 */
export const SOURCE_LABELS: Record<string, string> = {
    discovery_scan: 'Discovery Scan',
    k8s_watcher: 'Kubernetes',
    cloud_api: 'Cloud API',
    manual_entry: 'Manual Entry',
    unknown: 'Unknown',
} as const;

/**
 * Utility to convert backend SourceCitation to UI format
 */
export function toUICitationCard(citation: SourceCitation): UICitationCard {
    return {
        id: citation.id,
        icon: RESOURCE_TYPE_ICONS[citation.type] || RESOURCE_TYPE_ICONS.unknown,
        name: citation.name,
        type: citation.type,
        description: citation.description,
        confidence: citation.confidence,
        confidence_label: getConfidenceLabel(citation.confidence),
        source: SOURCE_LABELS[citation.source] || citation.source.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        retrieved_at: citation.retrieved_at,
        metadata: citation.metadata,
    };
}

/**
 * Get confidence label from score
 */
export function getConfidenceLabel(confidence: number): 'High' | 'Medium' | 'Low' | 'Uncertain' {
    if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return 'High';
    if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return 'Medium';
    if (confidence >= CONFIDENCE_THRESHOLDS.LOW) return 'Low';
    return 'Uncertain';
}

/**
 * Get confidence badge color
 */
export function getConfidenceColor(confidence: number): string {
    if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return 'bg-green-100 text-green-800 border-green-200';
    if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    if (confidence >= CONFIDENCE_THRESHOLDS.LOW) return 'bg-orange-100 text-orange-800 border-orange-200';
    return 'bg-red-100 text-red-800 border-red-200';
}
