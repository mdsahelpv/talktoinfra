// Chat components barrel export
export { ChatInterface } from './ChatInterface';
export { IntentIndicator } from './IntentIndicator';
export { ApprovalModal } from './ApprovalModal';
export { QueryResult } from './QueryResult';
export { ConversationTimeline, ConversationPreview } from './ConversationTimeline';
export { SourcesDisplay } from './SourcesDisplay';
export { default as ApprovalChainIndicator } from './ApprovalChainIndicator';
export { default as ApprovalNotification } from './ApprovalNotification';

// New components for query result handling
export { QueryResultPagination } from './QueryResultPagination';
export { QueryResultFilters } from './QueryResultFilters';
export { ExportDropdown } from './ExportDropdown';
export { CreateAlertModal } from './CreateAlertModal';

// Types
export type {
    ChatInputState,
    ApprovalModalProps,
    IntentIndicatorProps,
    QueryResultProps,
    QueryResultPaginationProps,
    QueryResultFiltersProps,
    ExportDropdownProps,
    CreateAlertModalProps,
    ConversationTimelineProps,
    ApprovalNotificationProps,
    ApprovalChainIndicatorProps,
    NotificationPreferences,
    ActionApprovalChain,
    ApprovalRule,
    ApproverHistoryEntry,
    ApprovalLevel,
    // Pagination & Filter types
    PaginationState,
    PaginationConfig,
    FilterState,
    FilterCondition,
    FilterPreset,
    SortState,
    SortDirection,
    // Alert types
    AlertSeverity,
    AlertConditionType,
    AlertStatus,
    AlertConfig,
    Alert,
    CreateAlertRequest,
    AlertThreshold,
    AlertNotificationChannel,
    // Query result types
    QueryResultMetadata,
} from '@/types/conversation';
