"""
Enhanced intent classification for infrastructure queries.
Extends classification to include DISCOVERY, ONBOARDING, and MANAGEMENT intents.
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class IntentClassification:
    """Enhanced intent classification result."""

    intent: str  # QUERY, ACTION, DISCOVERY, ONBOARDING, MANAGEMENT, ANALYSIS, HELP, UNKNOWN
    confidence: float
    entities: List[Dict[str, Any]]
    action_type: Optional[str] = None
    target_resource: Optional[str] = None
    requires_approval: bool = False
    risk_level: Optional[str] = None


class IntentClassifier:
    """Enhanced classifier for infrastructure query intents."""

    # Query intent patterns (read-only)
    QUERY_KEYWORDS = [
        "show", "list", "get", "find", "search", "display",
        "what", "where", "which", "how many", "count", "status",
        "describe", "explain", "tell me", "see", "view", "check",
    ]

    # Action intent patterns (modifications)
    ACTION_KEYWORDS = [
        "restart", "stop", "start", "delete", "create", "deploy",
        "scale", "update", "patch", "exec", "run", "kill",
        "remove", "rollback", "promote", "drain", "cordon",
        "uncordon", "taint", "apply", "replace", "edit", "modify",
    ]

    # Discovery intent patterns (exploration/scanning)
    DISCOVERY_KEYWORDS = [
        "discover", "scan", "explore", "find all", "detect",
        "probe", "enumerate", "crawl", "inventory", "map network",
        "what's running", "list all", "show all", "get all",
    ]

    # Onboarding intent patterns (adding infrastructure)
    ONBOARDING_KEYWORDS = [
        "add", "register", "connect", "onboard", "link", "integrate",
        "import", "install agent", "deploy agent", "new cluster",
        "new connection", "new infrastructure", "attach", "provision",
    ]

    # Management intent patterns (settings/users)
    MANAGEMENT_KEYWORDS = [
        "settings", "configure", "config", "preferences", "user management",
        "add user", "remove user", "role", "permission", "access",
        "api key", "token", "webhook", "notification", "alert",
        "schedule", "automation", "policy", "limits", "quotas",
    ]

    # Analysis intent patterns
    ANALYSIS_KEYWORDS = [
        "analyze", "compare", "trend", "pattern", "why", "explain",
        "performance", "optimization", "recommend", "suggest",
        "forecast", "predict", "correlate", "insight", "diagnose",
    ]

    # Help intent patterns
    HELP_KEYWORDS = [
        "help", "how do i", "how to", "what can", "assist",
        "guide", "tutorial", "documentation", "example", "commands",
    ]

    # Resource patterns
    RESOURCE_PATTERNS = {
        "pod": r"\bpod[s]?\b|\bcontainer[s]?\b",
        "deployment": r"\bdeployment[s]?\b|\bdeploy[s]?\b",
        "service": r"\bservice[s]?\b|\bsvc[s]?\b",
        "node": r"\bnode[s]?\b|\bworker[s]?\b|\bmaster[s]?\b",
        "namespace": r"\bnamespace[s]?\b|\bns\b|\bproject[s]?\b",
        "configmap": r"\bconfigmap[s]?\b|\bcm[s]?\b",
        "secret": r"\bsecret[s]?\b",
        "ingress": r"\bingress[es]?\b",
        "job": r"\bjob[s]?\b",
        "cronjob": r"\bcronjob[s]?\b",
        "cluster": r"\bcluster[s]?\b",
        "helm": r"\bhelm\b|\brelease[s]?\b",
        "pvc": r"\bpvc[s]?\b|\bvolume[s]?\b",
    }

    # Critical resources for risk assessment
    CRITICAL_RESOURCES = {"cluster", "namespace", "persistentvolume", "node"}

    def __init__(self):
        """Initialize the classifier."""
        self._initialize_patterns()

    def _initialize_patterns(self):
        """Compile regex patterns for efficiency."""
        self._query_pattern = self._compile_or_pattern(self.QUERY_KEYWORDS)
        self._action_pattern = self._compile_or_pattern(self.ACTION_KEYWORDS)
        self._discovery_pattern = self._compile_or_pattern(
            self.DISCOVERY_KEYWORDS)
        self._onboarding_pattern = self._compile_or_pattern(
            self.ONBOARDING_KEYWORDS)
        self._management_pattern = self._compile_or_pattern(
            self.MANAGEMENT_KEYWORDS)

    def _compile_or_pattern(self, keywords: List[str]) -> re.Pattern:
        """Compile a regex pattern from keywords."""
        escaped = [re.escape(kw) for kw in keywords]
        pattern = "|".join(escaped)
        return re.compile(pattern, re.IGNORECASE)

    def classify(self, query: str) -> IntentClassification:
        """Classify the intent of a query.

        Args:
            query: User query text

        Returns:
            IntentClassification with detected intent and metadata
        """
        query_lower = query.lower()

        # Count keyword matches using patterns
        query_score = len(self._query_pattern.findall(query_lower))
        action_score = len(self._action_pattern.findall(query_lower))
        discovery_score = len(self._discovery_pattern.findall(query_lower))
        onboarding_score = len(self._onboarding_pattern.findall(query_lower))
        management_score = len(self._management_pattern.findall(query_lower))
        analysis_score = sum(
            1 for kw in self.ANALYSIS_KEYWORDS if kw in query_lower)
        help_score = sum(1 for kw in self.HELP_KEYWORDS if kw in query_lower)

        # Calculate scores with weights
        scores = {
            "QUERY": query_score * 1.0,
            "ACTION": action_score * 1.2,  # Weight action higher
            "DISCOVERY": discovery_score * 1.1,
            "ONBOARDING": onboarding_score * 1.1,
            "MANAGEMENT": management_score * 1.1,
            "ANALYSIS": analysis_score * 1.0,
            "HELP": help_score * 0.8,
        }

        # Extract entities
        entities = self._extract_entities(query)

        # Apply context-aware adjustments
        scores = self._adjust_for_context(query_lower, scores, entities)

        # Determine intent
        max_intent = max(scores, key=scores.get)
        max_score = scores[max_intent]

        # Calculate confidence
        total_score = sum(scores.values())
        if total_score > 0:
            confidence = max_score / total_score
        else:
            confidence = 0.3  # Low confidence for empty scores

        # Adjust confidence based on context
        confidence = self._calculate_confidence(
            query_lower, max_intent, entities, confidence)

        # Handle ambiguous cases
        if max_score == 0:
            max_intent = "QUERY"
            confidence = 0.4

        # Determine approval requirements and risk
        requires_approval = False
        risk_level = None

        if max_intent == "ACTION":
            requires_approval = self._requires_approval(query_lower, entities)
            risk_level = self._assess_risk(query_lower, entities)

        # Extract action type and target
        action_type = None
        target_resource = None

        if max_intent in ["ACTION", "QUERY", "DISCOVERY"]:
            action_type = self._extract_action_type(query_lower)
            target_resource = self._extract_target_resource(
                query_lower, entities)

        return IntentClassification(
            intent=max_intent,
            confidence=min(confidence, 1.0),
            entities=entities,
            action_type=action_type,
            target_resource=target_resource,
            requires_approval=requires_approval,
            risk_level=risk_level,
        )

    def _adjust_for_context(
        self,
        query: str,
        scores: Dict[str, float],
        entities: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Adjust scores based on conversational context."""
        adjusted = scores.copy()

        # Check for follow-up indicators
        follow_up_patterns = [
            r"^and ",
            r"^also ",
            r"^what about ",
            r"^show me ",
            r"^tell me ",
        ]
        for pattern in follow_up_patterns:
            if re.search(pattern, query):
                # Increase query likelihood for follow-ups
                adjusted["QUERY"] *= 1.3
                break

        # Check for comparative queries
        if " vs " in query or " compared to " in query:
            adjusted["ANALYSIS"] *= 1.4
            adjusted["QUERY"] *= 1.2

        # Check for time-based queries
        time_patterns = [r"\b(last|this|past|ago)\b",
                         r"\b(current|now|today)\b"]
        for pattern in time_patterns:
            if re.search(pattern, query):
                adjusted["QUERY"] *= 1.1
                break

        return adjusted

    def _calculate_confidence(
        self,
        query: str,
        intent: str,
        entities: List[Dict[str, Any]],
        base_confidence: float,
    ) -> float:
        """Calculate final confidence score."""
        confidence = base_confidence

        # Boost confidence if entities are found
        if entities:
            confidence += 0.1

        # Boost for specific action verbs
        specific_actions = {"restart", "scale", "delete", "deploy", "apply"}
        if intent == "ACTION" and any(a in query for a in specific_actions):
            confidence += 0.15

        # Reduce confidence for vague queries
        vague_terms = {"something", "anything", "stuff", "things"}
        if any(term in query for term in vague_terms):
            confidence -= 0.2

        # Reduce for very short queries
        if len(query.split()) < 3:
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def _requires_approval(self, query: str, entities: List[Dict[str, Any]]) -> bool:
        """Determine if action requires approval."""
        action_words = {"delete", "remove", "stop", "kill", "terminate"}
        resource_values = {e.get("value", "").lower() for e in entities}

        # Actions on critical resources require approval
        if any(word in query for word in action_words):
            if resource_values & self.CRITICAL_RESOURCES:
                return True

        # Scale to zero requires approval
        if "scale" in query and "0" in query:
            return True

        # Force operations require approval
        if "force" in query or "--force" in query:
            return True

        return False

    def _assess_risk(self, query: str, entities: List[Dict[str, Any]]) -> str:
        """Assess risk level of action."""
        action_words = {"delete", "remove", "stop", "kill", "terminate"}
        resource_values = {e.get("value", "").lower() for e in entities}

        # Critical risk: delete/remove on critical resources
        if any(word in query for word in action_words):
            if resource_values & self.CRITICAL_RESOURCES:
                return "CRITICAL"
            if "namespace" in resource_values:
                return "HIGH"

        # High risk: scale operations
        if "scale" in query:
            return "HIGH"

        # High risk: force operations
        if "force" in query:
            return "HIGH"

        # Medium risk: restart/modify
        if any(word in query for word in {"restart", "patch", "update", "apply"}):
            return "MEDIUM"

        return "LOW"

    def _extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """Extract entities from query."""
        entities = []
        query_lower = query.lower()

        # Extract resource types
        for resource, pattern in self.RESOURCE_PATTERNS.items():
            if re.search(pattern, query_lower):
                entities.append({
                    "type": "resource",
                    "value": resource,
                    "confidence": 0.9,
                })

        # Extract namespace references
        namespace_patterns = [
            r"in (?:namespace|ns) (\w+)",
            r"in (?:the )?(\w+) namespace",
            r"namespace[:\s]*(\w+)",
            r"-n (\w+)",
        ]
        for pattern in namespace_patterns:
            match = re.search(pattern, query_lower)
            if match:
                namespace = match.group(1)
                # Avoid matching known resource names as namespaces
                if namespace not in {"default", "kube-system", "kube-public"}:
                    entities.append({
                        "type": "namespace",
                        "value": namespace,
                        "confidence": 0.95,
                    })
                break

        # Extract labels/selectors
        label_pattern = r"(?:with|where|having) (\w+)=(\w+)"
        for match in re.finditer(label_pattern, query_lower):
            entities.append({
                "type": "label_selector",
                "key": match.group(1),
                "value": match.group(2),
                "confidence": 0.85,
            })

        # Extract quoted names
        quoted = re.findall(r'"([^"]*)"', query)
        for name in quoted:
            entities.append({
                "type": "named_resource",
                "value": name,
                "confidence": 0.95,
            })

        # Extract numbers (replicas, ports, etc.)
        numbers = re.findall(r"\b(\d+)\b", query)
        for num in numbers[:3]:  # Limit to first 3
            entities.append({
                "type": "numeric",
                "value": num,
                "confidence": 0.7,
            })

        return entities

    def _extract_action_type(self, query: str) -> Optional[str]:
        """Extract the action type from query."""
        for keyword in self.ACTION_KEYWORDS:
            if keyword in query:
                return keyword

        for keyword in self.DISCOVERY_KEYWORDS:
            if keyword in query:
                return keyword

        for keyword in self.ONBOARDING_KEYWORDS:
            if keyword in query:
                return keyword

        return None

    def _extract_target_resource(
        self,
        query: str,
        entities: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Extract target resource from query."""
        # Look for resource entities
        resource_entities = [
            e for e in entities if e.get("type") == "resource"]
        if resource_entities:
            return resource_entities[0]["value"]

        # Look for named resources
        named_entities = [e for e in entities if e.get(
            "type") == "named_resource"]
        if named_entities:
            return named_entities[0]["value"]

        # Try to extract from quoted strings
        quoted = re.findall(r'"([^"]*)"', query)
        if quoted:
            return quoted[0]

        return None

    def classify_batch(self, queries: List[str]) -> List[IntentClassification]:
        """Classify multiple queries.

        Args:
            queries: List of query texts

        Returns:
            List of classifications
        """
        return [self.classify(q) for q in queries]

    def get_intent_description(self, intent: str) -> str:
        """Get human-readable description of intent.

        Args:
            intent: Intent type string

        Returns:
            Human-readable description
        """
        descriptions = {
            "QUERY": "Read-only inquiry about infrastructure",
            "ACTION": "Modification request requiring approval",
            "DISCOVERY": "Infrastructure exploration or scanning",
            "ONBOARDING": "Add new infrastructure to management",
            "MANAGEMENT": "Settings or user management task",
            "ANALYSIS": "Analysis or optimization request",
            "HELP": "Help or documentation request",
            "UNKNOWN": "Unclassified request",
        }
        return descriptions.get(intent, "Unknown intent")
