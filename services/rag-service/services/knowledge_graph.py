"""
Knowledge Graph service for RAG pipeline.

This module provides functionality for:
- Entity extraction from infrastructure resources
- Relationship mapping between resources
- Graph traversal queries for topology analysis
"""

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger()


class Entity:
    """Represents an extracted entity from infrastructure."""

    def __init__(
        self,
        entity_id: str,
        entity_type: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.name = name
        self.properties = properties or {}
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "properties": self.properties,
            "metadata": self.metadata,
        }


class Relationship:
    """Represents a relationship between entities."""

    def __init__(
        self,
        relationship_id: str,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ):
        self.relationship_id = relationship_id
        self.source_id = source_id
        self.target_id = target_id
        self.relationship_type = relationship_type
        self.properties = properties or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "properties": self.properties,
        }


class KnowledgeGraphService:
    """Service for managing knowledge graph of infrastructure resources."""

    # Entity type mappings
    ENTITY_TYPES = {
        "host": ["ip_address", "hostname", "mac_address"],
        "pod": ["name", "namespace", "node_name"],
        "deployment": ["name", "namespace", "replicas"],
        "service": ["name", "namespace", "cluster_ip", "type"],
        "node": ["name", "status", "ip_address"],
        "container": ["name", "image", "port"],
        "cluster": ["name", "region", "cloud_provider"],
        "namespace": ["name", "cluster_id"],
        "application": ["name", "tier", "team"],
    }

    # Relationship type mappings
    RELATIONSHIP_TYPES = {
        "hosts": "host -> node (physical/virtual)",
        "runs_on": "pod -> node",
        "contains": "namespace -> pod",
        "deploys": "deployment -> pod",
        "exposes": "service -> pod",
        "connects_to": "service -> service",
        "depends_on": "pod -> pod",
        "scales_with": "deployment -> hpa",
        "backed_by": "service -> persistent_volume",
        "belongs_to": "resource -> namespace",
        "managed_by": "resource -> cluster",
    }

    def __init__(self):
        """Initialize the knowledge graph service."""
        self._entity_cache: Dict[str, Entity] = {}
        self._relationship_cache: Dict[str, Relationship] = {}

    def extract_entity_id(self, entity_type: str, identifier: str) -> str:
        """Generate a unique entity ID.

        Args:
            entity_type: Type of entity
            identifier: Unique identifier for the entity

        Returns:
            Unique entity ID
        """
        combined = f"{entity_type}:{identifier}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def extract_entities_from_host(
        self, host_data: Dict[str, Any]
    ) -> List[Entity]:
        """Extract entities from discovered host data.

        Args:
            host_data: Host discovery data

        Returns:
            List of extracted entities
        """
        entities = []

        # Main host entity
        ip_address = host_data.get("ip_address", "unknown")
        host_id = self.extract_entity_id("host", ip_address)

        host_entity = Entity(
            entity_id=host_id,
            entity_type="host",
            name=ip_address,
            properties={
                "ip_address": ip_address,
                "hostname": host_data.get("hostname"),
                "mac_address": host_data.get("mac_address"),
                "operating_system": host_data.get("operating_system"),
                "status": host_data.get("status", "unknown"),
            },
            metadata={
                "source": "discovery",
                "source_id": str(host_data.get("id", "")),
                "discovered_at": host_data.get("discovered_at"),
            },
        )
        entities.append(host_entity)

        # Add hostname entity if available
        hostname = host_data.get("hostname")
        if hostname:
            hostname_id = self.extract_entity_id("hostname", hostname)
            hostname_entity = Entity(
                entity_id=hostname_id,
                entity_type="hostname",
                name=hostname,
                properties={"resolves_to": ip_address},
                metadata={"source": "discovery"},
            )
            entities.append(hostname_entity)

        # Add port entities
        ports = host_data.get("ports", [])
        for port in ports[:20]:  # Limit to 20 ports
            port_num = port.get("port")
            if port_num:
                port_id = self.extract_entity_id(
                    "port", f"{ip_address}:{port_num}")
                port_entity = Entity(
                    entity_id=port_id,
                    entity_type="port",
                    name=f"{ip_address}:{port_num}",
                    properties={
                        "port": port_num,
                        "protocol": port.get("protocol", "tcp"),
                        "service": port.get("service"),
                        "state": port.get("state", "open"),
                    },
                    metadata={"source": "discovery"},
                )
                entities.append(port_entity)

        return entities

    def extract_entities_from_k8s_pod(
        self, pod_data: Dict[str, Any]
    ) -> List[Entity]:
        """Extract entities from K8s pod data.

        Args:
            pod_data: Pod resource data

        Returns:
            List of extracted entities
        """
        entities = []

        name = pod_data.get("name", "unknown")
        namespace = pod_data.get("namespace", "default")
        cluster_id = pod_data.get("cluster_id", "unknown")

        # Main pod entity
        pod_id = self.extract_entity_id(
            "pod", f"{cluster_id}/{namespace}/{name}")

        pod_entity = Entity(
            entity_id=pod_id,
            entity_type="pod",
            name=name,
            properties={
                "namespace": namespace,
                "status": pod_data.get("status"),
                "node_name": pod_data.get("node_name"),
                "images": pod_data.get("images", []),
                "labels": pod_data.get("labels", {}),
            },
            metadata={
                "source": "k8s",
                "cluster_id": cluster_id,
                "uid": pod_data.get("uid"),
            },
        )
        entities.append(pod_entity)

        # Container entities
        containers = pod_data.get("containers", [])
        for container in containers:
            container_name = container.get("name")
            if container_name:
                container_id = self.extract_entity_id(
                    "container", f"{cluster_id}/{namespace}/{name}/{container_name}"
                )
                container_entity = Entity(
                    entity_id=container_id,
                    entity_type="container",
                    name=container_name,
                    properties={
                        "image": container.get("image"),
                        "ports": container.get("ports", []),
                        "env": container.get("env", [])[:5],  # Limit env vars
                    },
                    metadata={"source": "k8s", "parent_pod": name},
                )
                entities.append(container_entity)

        return entities

    def extract_entities_from_k8s_deployment(
        self, deployment_data: Dict[str, Any]
    ) -> List[Entity]:
        """Extract entities from K8s deployment data.

        Args:
            deployment_data: Deployment resource data

        Returns:
            List of extracted entities
        """
        entities = []

        name = deployment_data.get("name", "unknown")
        namespace = deployment_data.get("namespace", "default")
        cluster_id = deployment_data.get("cluster_id", "unknown")

        deployment_id = self.extract_entity_id(
            "deployment", f"{cluster_id}/{namespace}/{name}"
        )

        deployment_entity = Entity(
            entity_id=deployment_id,
            entity_type="deployment",
            name=name,
            properties={
                "namespace": namespace,
                "replicas": deployment_data.get("replicas"),
                "ready_replicas": deployment_data.get("ready_replicas"),
                "strategy_type": deployment_data.get("strategy_type"),
                "labels": deployment_data.get("labels", {}),
            },
            metadata={
                "source": "k8s",
                "cluster_id": cluster_id,
                "uid": deployment_data.get("uid"),
            },
        )
        entities.append(deployment_entity)

        return entities

    def extract_entities_from_k8s_service(
        self, service_data: Dict[str, Any]
    ) -> List[Entity]:
        """Extract entities from K8s service data.

        Args:
            service_data: Service resource data

        Returns:
            List of extracted entities
        """
        entities = []

        name = service_data.get("name", "unknown")
        namespace = service_data.get("namespace", "default")
        cluster_id = service_data.get("cluster_id", "unknown")

        service_id = self.extract_entity_id(
            "service", f"{cluster_id}/{namespace}/{name}"
        )

        service_entity = Entity(
            entity_id=service_id,
            entity_type="service",
            name=name,
            properties={
                "namespace": namespace,
                "type": service_data.get("type"),
                "cluster_ip": service_data.get("cluster_ip"),
                "ports": service_data.get("ports", []),
                "selector": service_data.get("selector", {}),
            },
            metadata={
                "source": "k8s",
                "cluster_id": cluster_id,
                "uid": service_data.get("uid"),
            },
        )
        entities.append(service_entity)

        return entities

    def extract_entities_from_k8s_node(
        self, node_data: Dict[str, Any]
    ) -> List[Entity]:
        """Extract entities from K8s node data.

        Args:
            node_data: Node resource data

        Returns:
            List of extracted entities
        """
        entities = []

        name = node_data.get("name", "unknown")
        cluster_id = node_data.get("cluster_id", "unknown")

        node_id = self.extract_entity_id("node", f"{cluster_id}/{name}")

        node_entity = Entity(
            entity_id=node_id,
            entity_type="node",
            name=name,
            properties={
                "status": node_data.get("status"),
                "capacity": node_data.get("capacity", {}),
                "allocatable": node_data.get("allocatable", {}),
                "labels": node_data.get("labels", {}),
                "addresses": node_data.get("addresses", []),
            },
            metadata={
                "source": "k8s",
                "cluster_id": cluster_id,
                "uid": node_data.get("uid"),
            },
        )
        entities.append(node_entity)

        return entities

    def extract_relationships(
        self,
        source_entity: Entity,
        target_entity: Entity,
        relationship_type: str,
    ) -> Optional[Relationship]:
        """Extract a relationship between two entities.

        Args:
            source_entity: Source entity
            target_entity: Target entity
            relationship_type: Type of relationship

        Returns:
            Relationship if valid, None otherwise
        """
        # Validate relationship type
        if relationship_type not in self.RELATIONSHIP_TYPES:
            logger.warning(
                "invalid_relationship_type",
                type=relationship_type,
                source=source_entity.entity_type,
                target=target_entity.entity_type,
            )
            return None

        # Generate relationship ID
        rel_id = f"{source_entity.entity_id}:{relationship_type}:{target_entity.entity_id}"
        relationship_id = hashlib.sha256(rel_id.encode()).hexdigest()[:16]

        return Relationship(
            relationship_id=relationship_id,
            source_id=source_entity.entity_id,
            target_id=target_entity.entity_id,
            relationship_type=relationship_type,
            properties={
                "source_type": source_entity.entity_type,
                "target_type": target_entity.entity_type,
            },
        )

    def infer_relationships(
        self, entities: List[Entity]
    ) -> List[Relationship]:
        """Infer relationships between entities based on their properties.

        Args:
            entities: List of entities to analyze

        Returns:
            List of inferred relationships
        """
        relationships = []
        entity_map = {e.entity_id: e for e in entities}

        for entity in entities:
            # Pod -> Node relationship (runs_on)
            if entity.entity_type == "pod":
                node_name = entity.properties.get("node_name")
                if node_name:
                    # Find matching node entity
                    for other in entities:
                        if (
                            other.entity_type == "node"
                            and other.name == node_name
                        ):
                            rel = self.extract_relationships(
                                entity, other, "runs_on"
                            )
                            if rel:
                                relationships.append(rel)
                            break

            # Service -> Pod relationship (exposes)
            if entity.entity_type == "service":
                selector = entity.properties.get("selector", {})
                if selector:
                    # Find matching pods
                    for other in entities:
                        if other.entity_type == "pod":
                            labels = other.properties.get("labels", {})
                            if self._matches_selector(labels, selector):
                                rel = self.extract_relationships(
                                    entity, other, "exposes"
                                )
                                if rel:
                                    relationships.append(rel)

            # Deployment -> Pod relationship (deploys)
            if entity.entity_type == "deployment":
                namespace = entity.properties.get("namespace")
                labels = entity.properties.get("labels", {})
                if namespace and labels:
                    for other in entities:
                        if other.entity_type == "pod":
                            other_namespace = other.properties.get("namespace")
                            other_labels = other.properties.get("labels", {})
                            if (
                                other_namespace == namespace
                                and self._matches_selector(other_labels, labels)
                            ):
                                rel = self.extract_relationships(
                                    entity, other, "deploys"
                                )
                                if rel:
                                    relationships.append(rel)

            # Pod -> Pod relationship (depends_on)
            if entity.entity_type == "pod":
                # Check for environment variable references to other pods
                containers = entity.properties.get("images", [])
                for other in entities:
                    if (
                        other.entity_type == "pod"
                        and other.entity_id != entity.entity_id
                    ):
                        # Simple heuristic: check if other pod name appears in this pod's data
                        if other.name in str(entity.properties):
                            rel = self.extract_relationships(
                                entity, other, "depends_on"
                            )
                            if rel:
                                relationships.append(rel)

        return relationships

    def _matches_selector(
        self, labels: Dict[str, str], selector: Dict[str, str]
    ) -> bool:
        """Check if labels match a selector.

        Args:
            labels: Resource labels
            selector: Selector to match against

        Returns:
            True if labels match selector
        """
        for key, value in selector.items():
            if key not in labels or labels[key] != value:
                return False
        return True

    def build_graph_from_resources(
        self, resources: List[Dict[str, Any]]
    ) -> Tuple[List[Entity], List[Relationship]]:
        """Build knowledge graph from a list of resources.

        Args:
            resources: List of resource data dictionaries

        Returns:
            Tuple of (entities, relationships)
        """
        all_entities = []
        all_relationships = []

        for resource in resources:
            resource_type = resource.get("resource_type", "")

            # Extract entities based on resource type
            if resource_type == "discovered_host" or "ip_address" in resource:
                entities = self.extract_entities_from_host(resource)
            elif resource_type == "k8s_pod" or "pod" in resource_type:
                entities = self.extract_entities_from_k8s_pod(resource)
            elif resource_type == "k8s_deployment" or "deployment" in resource_type:
                entities = self.extract_entities_from_k8s_deployment(resource)
            elif resource_type == "k8s_service" or "service" in resource_type:
                entities = self.extract_entities_from_k8s_service(resource)
            elif resource_type == "k8s_node" or "node" in resource_type:
                entities = self.extract_entities_from_k8s_node(resource)
            else:
                logger.warning(
                    "unknown_resource_type",
                    type=resource_type,
                )
                continue

            all_entities.extend(entities)

            # Infer relationships
            relationships = self.infer_relationships(entities)
            all_relationships.extend(relationships)

        return all_entities, all_relationships

    def get_related_entities(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """Get related entities through graph traversal.

        Args:
            entity_id: Starting entity ID
            relationship_types: Filter by relationship types
            max_depth: Maximum traversal depth

        Returns:
            List of related entities with paths
        """
        # This would typically query a graph database
        # For now, return a placeholder implementation
        logger.info(
            "graph_traversal_requested",
            entity_id=entity_id,
            max_depth=max_depth,
        )

        return []

    def find_path(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> Optional[List[str]]:
        """Find a path between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_depth: Maximum path length

        Returns:
            List of entity IDs forming the path, or None if no path found
        """
        # BFS-based path finding
        # This would typically query a graph database
        logger.info(
            "path_finding_requested",
            source=source_id,
            target=target_id,
            max_depth=max_depth,
        )

        return None


# Singleton instance
_knowledge_graph_service: Optional[KnowledgeGraphService] = None


def get_knowledge_graph() -> KnowledgeGraphService:
    """Get the singleton knowledge graph service instance."""
    global _knowledge_graph_service
    if _knowledge_graph_service is None:
        _knowledge_graph_service = KnowledgeGraphService()
    return _knowledge_graph_service
