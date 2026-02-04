"""
Unified Discovered Infrastructure Manager Service.

This service handles all operations for discovered infrastructure including
listing, filtering, state management, and bulk operations.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import and_, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import DiscoveredHost, DiscoveredPort, ScanJob
from app.models_discovered import (
    DiscoveredBulkOperation,
    DiscoveredInfrastructure,
    DiscoveredState,
    DiscoveredStateHistory,
    InfrastructureType,
    ServiceCatalogEntry,
    VALID_STATE_TRANSITIONS,
)
from app.schemas_discovered import (
    BulkIgnoreRequest,
    BulkOnboardRequest,
    BulkOperationResponse,
    DiscoveredFilterRequest,
    DiscoveredInfrastructureDetail,
    DiscoveredInfrastructureResponse,
    DiscoveredStatsSchema,
    ExportRequest,
    IgnoreRequest,
    OnboardingSuggestionSchema,
    PaginatedDiscoveredResponse,
    ReScanRequest,
    ServiceCatalogEntryResponse,
    ServiceCatalogResponse,
    StateHistoryEntry,
    SuggestionsResponse,
    UpdateNotesRequest,
    UpdateStateRequest,
)

logger = structlog.get_logger()


class DiscoveredManager:
    """Manager for unified discovered infrastructure operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the discovered manager.

        Args:
            db: Database session
        """
        self.db = db
        self.settings = get_settings()

    async def list_discovered(
        self,
        page: int = 1,
        page_size: int = 50,
        filters: Optional[DiscoveredFilterRequest] = None,
        sort_by: str = "discovered_at",
        sort_order: str = "desc",
    ) -> PaginatedDiscoveredResponse:
        """List discovered infrastructure with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            filters: Optional filter criteria
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Paginated list of discovered infrastructure
        """
        query = select(DiscoveredInfrastructure)

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(DiscoveredInfrastructure,
                              sort_by, DiscoveredInfrastructure.discovered_at)
        if sort_order == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        query = query.order_by(sort_column)
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Convert to response
        response_items = [self._to_response(item) for item in items]

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        return PaginatedDiscoveredResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def _apply_filters(
        self, query, filters: DiscoveredFilterRequest
    ):
        """Apply filter criteria to query.

        Args:
            query: SQLAlchemy query
            filters: Filter criteria

        Returns:
            Modified query
        """
        conditions = []

        if filters.infra_types:
            types = [t.value for t in filters.infra_types]
            conditions.append(DiscoveredInfrastructure.infra_type.in_(types))

        if filters.states:
            states = [s.value for s in filters.states]
            conditions.append(DiscoveredInfrastructure.state.in_(states))

        if filters.scan_job_ids:
            conditions.append(
                DiscoveredInfrastructure.scan_job_id.in_(filters.scan_job_ids))

        if filters.search_query:
            search = f"%{filters.search_query}%"
            conditions.append(
                or_(
                    DiscoveredInfrastructure.ip_address.ilike(search),
                    DiscoveredInfrastructure.hostname.ilike(search),
                    DiscoveredInfrastructure.fqdn.ilike(search),
                )
            )

        if filters.min_confidence is not None:
            conditions.append(
                DiscoveredInfrastructure.confidence_score >= filters.min_confidence)

        if filters.cloud_providers:
            conditions.append(DiscoveredInfrastructure.cloud_provider.in_(
                filters.cloud_providers))

        if filters.tags:
            conditions.append(
                DiscoveredInfrastructure.tags.contains(filters.tags))

        if filters.discovered_after:
            conditions.append(
                DiscoveredInfrastructure.discovered_at >= filters.discovered_after)

        if filters.discovered_before:
            conditions.append(
                DiscoveredInfrastructure.discovered_at <= filters.discovered_before)

        if conditions:
            query = query.where(and_(*conditions))

        return query

    async def get_detail(self, item_id: UUID) -> Optional[DiscoveredInfrastructureDetail]:
        """Get detailed information for a discovered item.

        Args:
            item_id: ID of the item

        Returns:
            Detailed item information or None
        """
        query = (
            select(DiscoveredInfrastructure)
            .options(
                selectinload(DiscoveredInfrastructure.state_history),
                selectinload(DiscoveredInfrastructure.scan_job),
            )
            .where(DiscoveredInfrastructure.id == item_id)
        )

        result = await self.db.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            return None

        return self._to_detail_response(item)

    async def get_stats(self) -> DiscoveredStatsSchema:
        """Get statistics for discovered infrastructure.

        Returns:
            Statistics summary
        """
        # Total count
        total_query = select(func.count()).select_from(
            DiscoveredInfrastructure)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # Count by type
        type_counts = {}
        for infra_type in InfrastructureType:
            query = (
                select(func.count())
                .select_from(DiscoveredInfrastructure)
                .where(DiscoveredInfrastructure.infra_type == infra_type.value)
            )
            result = await self.db.execute(query)
            count = result.scalar() or 0
            if count > 0:
                type_counts[infra_type.value] = count

        # Count by state
        state_counts = {}
        for state in DiscoveredState:
            query = (
                select(func.count())
                .select_from(DiscoveredInfrastructure)
                .where(DiscoveredInfrastructure.state == state.value)
            )
            result = await self.db.execute(query)
            count = result.scalar() or 0
            if count > 0:
                state_counts[state.value] = count

        # Detailed breakdown by type and state
        by_state_detailed = {}
        for infra_type in InfrastructureType:
            type_value = infra_type.value
            type_query = (
                select(DiscoveredInfrastructure.state)
                .where(DiscoveredInfrastructure.infra_type == type_value)
            )
            result = await self.db.execute(type_query)
            states = result.scalars().all()

            state_breakdown = {}
            for state in set(states):
                state_breakdown[state] = states.count(state)
            if state_breakdown:
                by_state_detailed[type_value] = state_breakdown

        # Recently discovered (last 24h)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_query = (
            select(func.count())
            .select_from(DiscoveredInfrastructure)
            .where(DiscoveredInfrastructure.discovered_at >= yesterday)
        )
        recent_result = await self.db.execute(recent_query)
        recently_discovered = recent_result.scalar() or 0

        return DiscoveredStatsSchema(
            total_items=total,
            by_type=type_counts,
            by_state=state_counts,
            by_state_detailed=by_state_detailed,
            recently_discovered=recently_discovered,
            pending_onboarding=state_counts.get(
                DiscoveredState.PENDING_ONBOARDING.value, 0),
            onboarded=state_counts.get(DiscoveredState.ONBOARDED.value, 0),
            ignored=state_counts.get(DiscoveredState.IGNORED.value, 0),
        )

    async def get_suggestions(
        self, limit: int = 20
    ) -> SuggestionsResponse:
        """Get smart onboarding suggestions.

        Args:
            limit: Maximum number of suggestions

        Returns:
            List of suggestions with reasoning
        """
        # Find items in suggested state that haven't been acted on
        query = (
            select(DiscoveredInfrastructure)
            .where(DiscoveredInfrastructure.state == DiscoveredState.SUGGESTED.value)
            .order_by(DiscoveredInfrastructure.confidence_score.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        suggestions = []
        for item in items:
            suggestion = self._generate_suggestion(item)
            if suggestion:
                suggestions.append(suggestion)

        return SuggestionsResponse(
            suggestions=suggestions,
            total_count=len(suggestions),
        )

    def _generate_suggestion(
        self, item: DiscoveredInfrastructure
    ) -> Optional[OnboardingSuggestionSchema]:
        """Generate onboarding suggestion for an item.

        Args:
            item: Discovered infrastructure item

        Returns:
            Suggestion or None if no action needed
        """
        infra_type = item.infra_type
        service_type = item.service_type

        if infra_type == InfrastructureType.KUBERNETES_CLUSTER.value:
            return OnboardingSuggestionSchema(
                item_id=item.id,
                suggested_action="connect_k8s",
                action_label="Connect Kubernetes Cluster",
                confidence=item.confidence_score,
                reason="Kubernetes API server detected",
                prerequisites=["Kubeconfig or credentials"],
                estimated_effort="10 minutes",
            )

        if infra_type == InfrastructureType.DATABASE.value:
            action = "onboard_database"
            if service_type == "postgresql":
                action = "onboard_postgresql"
            elif service_type == "mysql":
                action = "onboard_mysql"
            elif service_type == "redis":
                action = "onboard_redis"

            return OnboardingSuggestionSchema(
                item_id=item.id,
                suggested_action=action,
                action_label=f"Connect {service_type or 'Database'}",
                confidence=item.confidence_score,
                reason=f"{service_type or 'Database'} service detected",
                prerequisites=["Connection credentials"],
                estimated_effort="5 minutes",
            )

        if infra_type == InfrastructureType.CLOUD_RESOURCE.value:
            return OnboardingSuggestionSchema(
                item_id=item.id,
                suggested_action="add_cloud_resource",
                action_label="Add Cloud Resource",
                confidence=item.confidence_score,
                reason=f"Cloud resource detected ({item.cloud_provider})",
                prerequisites=["Cloud provider credentials"],
                estimated_effort="5 minutes",
            )

        if infra_type == InfrastructureType.SERVICE.value:
            return OnboardingSuggestionSchema(
                item_id=item.id,
                suggested_action="add_monitoring",
                action_label="Add to Monitoring",
                confidence=item.confidence_score,
                reason="HTTP service detected",
                prerequisites=[],
                estimated_effort="2 minutes",
            )

        return OnboardingSuggestionSchema(
            item_id=item.id,
            suggested_action="add_host",
            action_label="Add to Managed Hosts",
            confidence=item.confidence_score,
            reason="Host detected",
            prerequisites=[],
            estimated_effort="3 minutes",
        )

    async def update_state(
        self,
        item_id: UUID,
        request: UpdateStateRequest,
        user_id: str = "system",
    ) -> Optional[DiscoveredInfrastructureResponse]:
        """Update the state of a discovered item.

        Args:
            item_id: ID of the item
            request: State update request
            user_id: User making the change

        Returns:
            Updated item or None if not found
        """
        query = select(DiscoveredInfrastructure).where(
            DiscoveredInfrastructure.id == item_id
        )
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            return None

        # Validate state transition
        current_state = DiscoveredState(item.state)
        new_state = request.new_state

        if new_state not in VALID_STATE_TRANSITIONS.get(current_state, []):
            logger.warning(
                "invalid_state_transition",
                item_id=str(item_id),
                from_state=current_state.value,
                to_state=new_state.value,
            )
            return None

        # Record history
        history = DiscoveredStateHistory(
            item_id=item_id,
            from_state=item.state,
            to_state=new_state.value,
            triggered_by=user_id,
            trigger_reason=request.reason,
        )
        self.db.add(history)

        # Update item
        item.previous_state = item.state
        item.state = new_state.value

        await self.db.commit()
        await self.db.refresh(item)

        return self._to_response(item)

    async def ignore_item(
        self,
        item_id: UUID,
        request: IgnoreRequest,
        user_id: str = "system",
    ) -> Optional[DiscoveredInfrastructureResponse]:
        """Mark an item as ignored.

        Args:
            item_id: ID of the item
            request: Ignore request with reason
            user_id: User making the change

        Returns:
            Updated item or None if not found
        """
        query = select(DiscoveredInfrastructure).where(
            DiscoveredInfrastructure.id == item_id
        )
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            return None

        # Record history
        history = DiscoveredStateHistory(
            item_id=item_id,
            from_state=item.state,
            to_state=DiscoveredState.IGNORED.value,
            triggered_by=user_id,
            trigger_reason=request.reason,
        )
        self.db.add(history)

        # Update item
        item.state = DiscoveredState.IGNORED.value
        item.ignored_at = datetime.utcnow()
        item.ignored_by = user_id
        item.ignore_reason = request.reason

        await self.db.commit()
        await self.db.refresh(item)

        return self._to_response(item)

    async def bulk_onboard(
        self, request: BulkOnboardRequest, user_id: str = "system"
    ) -> BulkOperationResponse:
        """Initiate bulk onboarding operation.

        Args:
            request: Bulk operation request
            user_id: User initiating the operation

        Returns:
            Operation tracking response
        """
        operation = DiscoveredBulkOperation(
            operation_type=request.action_type,
            target_count=len(request.item_ids),
            status="pending",
            created_by=user_id,
            target_ids=[str(i) for i in request.item_ids],
            result_summary={},
        )

        self.db.add(operation)
        await self.db.commit()
        await self.db.refresh(operation)

        # TODO: Start async task for actual processing
        logger.info(
            "bulk_onboard_started",
            operation_id=str(operation.id),
            target_count=len(request.item_ids),
        )

        return BulkOperationResponse(
            operation_id=operation.id,
            status=operation.status,
            target_count=operation.target_count,
            created_at=operation.created_at,
        )

    async def export_to_csv(
        self, request: ExportRequest
    ) -> str:
        """Export discovered items to CSV format.

        Args:
            request: Export request with filters

        Returns:
            CSV content as string
        """
        query = select(DiscoveredInfrastructure)

        if request.filters:
            query = self._apply_filters(query, request.filters)

        if request.item_ids:
            query = query.where(
                DiscoveredInfrastructure.id.in_(request.item_ids))

        result = await self.db.execute(query)
        items = result.scalars().all()

        # Generate CSV
        headers = [
            "id",
            "ip_address",
            "hostname",
            "infra_type",
            "service_type",
            "state",
            "discovered_at",
            "confidence_score",
        ]

        rows = []
        for item in items:
            rows.append(
                [
                    str(item.id),
                    item.ip_address or "",
                    item.hostname or "",
                    item.infra_type,
                    item.service_type or "",
                    item.state,
                    item.discovered_at.isoformat() if item.discovered_at else "",
                    str(item.confidence_score),
                ]
            )

        csv_lines = [",".join(headers)]
        for row in rows:
            csv_lines.append(",".join(row))

        return "\n".join(csv_lines)

    async def get_service_catalog(
        self, page: int = 1, page_size: int = 50
    ) -> ServiceCatalogResponse:
        """Get service catalog (discovered services).

        Args:
            page: Page number
            page_size: Items per page

        Returns:
            Service catalog response
        """
        query = select(ServiceCatalogEntry)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        entries = result.scalars().all()

        # Convert to response
        services = [self._to_service_response(entry) for entry in entries]

        # Group by type
        by_type = {}
        for entry in entries:
            service_type = entry.service_type or "unknown"
            by_type[service_type] = by_type.get(service_type, 0) + 1

        return ServiceCatalogResponse(
            services=services,
            total=total,
            by_type=by_type,
        )

    def _to_response(self, item: DiscoveredInfrastructure) -> DiscoveredInfrastructureResponse:
        """Convert database model to response schema.

        Args:
            item: Database model

        Returns:
            Response schema
        """
        return DiscoveredInfrastructureResponse(
            id=item.id,
            ip_address=str(item.ip_address) if item.ip_address else None,
            hostname=item.hostname,
            fqdn=item.fqdn,
            mac_address=str(item.mac_address) if item.mac_address else None,
            infra_type=InfrastructureType(item.infra_type),
            service_type=item.service_type,
            service_version=item.service_version,
            confidence_score=item.confidence_score,
            state=DiscoveredState(item.state),
            previous_state=DiscoveredState(
                item.previous_state) if item.previous_state else None,
            scan_job_id=item.scan_job_id,
            discovered_at=item.discovered_at,
            last_seen_at=item.last_seen_at,
            port=item.port,
            protocol=item.protocol,
            response_time_ms=item.response_time_ms,
            availability_score=item.availability_score,
            suggested_action=item.suggested_action,
            tags=item.tags or [],
            created_by=item.created_by,
            notes=item.notes,
        )

    def _to_detail_response(
        self, item: DiscoveredInfrastructure
    ) -> DiscoveredInfrastructureDetail:
        """Convert to detailed response with history.

        Args:
            item: Database model

        Returns:
            Detailed response schema
        """
        base = self._to_response(item)

        history = [
            StateHistoryEntry(
                id=h.id,
                from_state=h.from_state,
                to_state=h.to_state,
                triggered_by=h.triggered_by,
                trigger_reason=h.trigger_reason,
                created_at=h.created_at,
                metadata=h.metadata or {},
            )
            for h in item.state_history
        ]

        return DiscoveredInfrastructureDetail(
            **base.model_dump(),
            state_history=history,
        )

    def _to_service_response(
        self, entry: ServiceCatalogEntry
    ) -> ServiceCatalogEntryResponse:
        """Convert service catalog entry to response.

        Args:
            entry: Database model

        Returns:
            Response schema
        """
        return ServiceCatalogEntryResponse(
            id=entry.id,
            host_id=entry.host_id,
            endpoint=entry.endpoint,
            path=entry.path,
            method=entry.method,
            service_name=entry.service_name,
            service_type=entry.service_type,
            api_version=entry.api_version,
            discovered_at=entry.discovered_at,
            last_checked_at=entry.last_checked_at,
            response_time_ms=entry.response_time_ms,
            documentation_url=entry.documentation_url,
            description=entry.description,
            capabilities=entry.capabilities or [],
            auth_required=bool(entry.auth_required),
            auth_type=entry.auth_type,
        )
