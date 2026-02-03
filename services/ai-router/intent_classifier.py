"""
Intent classification for natural language queries.
Uses spaCy for NER and rule-based classification.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import spacy
from spacy.tokens import Doc


@dataclass
class IntentClassification:
    intent: str  # QUERY, ACTION, ANALYSIS, HELP, UNKNOWN
    confidence: float
    entities: List[Dict[str, Any]]
    action_type: Optional[str] = None
    target_resource: Optional[str] = None


class IntentClassifier:
    """Classify user query intents."""

    # Intent patterns
    ACTION_KEYWORDS = [
        "restart",
        "stop",
        "start",
        "delete",
        "create",
        "deploy",
        "scale",
        "update",
        "patch",
        "exec",
        "run",
        "kill",
        "remove",
        "rollback",
        "promote",
        "drain",
        "cordon",
        "uncordon",
        "taint",
    ]

    QUERY_KEYWORDS = [
        "show",
        "list",
        "get",
        "find",
        "search",
        "display",
        "what",
        "where",
        "which",
        "how many",
        "count",
        "status",
    ]

    ANALYSIS_KEYWORDS = [
        "analyze",
        "compare",
        "trend",
        "pattern",
        "why",
        "explain",
        "performance",
        "optimization",
        "recommend",
        "suggest",
        "forecast",
        "predict",
        "correlate",
    ]

    HELP_KEYWORDS = [
        "help",
        "how do i",
        "how to",
        "what can",
        "assist",
        "guide",
        "tutorial",
        "documentation",
        "example",
    ]

    RESOURCE_PATTERNS = {
        "pod": r"\bpod[s]?\b|\bcontainer[s]?\b",
        "deployment": r"\bdeployment[s]?\b|\bdeploy[s]?\b",
        "service": r"\bservice[s]?\b|\bsvc[s]?\b",
        "node": r"\bnode[s]?\b|\bworker[s]?\b",
        "namespace": r"\bnamespace[s]?\b|\bns\b|\bproject[s]?\b",
        "configmap": r"\bconfigmap[s]?\b|\bcm[s]?\b",
        "secret": r"\bsecret[s]?\b",
        "ingress": r"\bingress[es]?\b",
        "job": r"\bjob[s]?\b",
        "cronjob": r"\bcronjob[s]?\b",
    }

    def __init__(self):
        """Initialize the classifier."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Fallback to basic processing if model not available
            self.nlp = None

    def classify(self, query: str) -> IntentClassification:
        """Classify the intent of a query."""
        query_lower = query.lower()

        # Count keyword matches
        action_score = sum(1 for kw in self.ACTION_KEYWORDS if kw in query_lower)
        query_score = sum(1 for kw in self.QUERY_KEYWORDS if kw in query_lower)
        analysis_score = sum(1 for kw in self.ANALYSIS_KEYWORDS if kw in query_lower)
        help_score = sum(1 for kw in self.HELP_KEYWORDS if kw in query_lower)

        # Extract entities
        entities = self._extract_entities(query)

        # Determine intent
        scores = {
            "ACTION": action_score,
            "QUERY": query_score,
            "ANALYSIS": analysis_score,
            "HELP": help_score,
        }

        max_intent = max(scores, key=scores.get)
        max_score = scores[max_intent]

        # Calculate confidence
        total_score = sum(scores.values())
        confidence = max_score / max(total_score, 1)

        # Default to QUERY if no clear intent and no action keywords
        if max_score == 0:
            max_intent = "QUERY"
            confidence = 0.5

        # Extract action type and target
        action_type = None
        target_resource = None

        if max_intent == "ACTION":
            action_type = self._extract_action_type(query_lower)
            target_resource = self._extract_target_resource(query_lower, entities)
        elif max_intent == "QUERY":
            target_resource = self._extract_target_resource(query_lower, entities)

        return IntentClassification(
            intent=max_intent,
            confidence=min(confidence, 1.0),
            entities=entities,
            action_type=action_type,
            target_resource=target_resource,
        )

    def _extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """Extract entities from query."""
        entities = []
        query_lower = query.lower()

        # Extract resource types
        for resource, pattern in self.RESOURCE_PATTERNS.items():
            if re.search(pattern, query_lower):
                entities.append(
                    {"type": "resource", "value": resource, "confidence": 0.9}
                )

        # Extract using spaCy NER if available
        if self.nlp:
            doc = self.nlp(query)
            for ent in doc.ents:
                entities.append(
                    {
                        "type": ent.label_,
                        "value": ent.text,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "confidence": 0.8,
                    }
                )

        # Extract namespace references
        namespace_patterns = [
            r"in (?:namespace|ns) (\w+)",
            r"in (?:the )?(\w+) namespace",
            r"namespace[:\s]*(\w+)",
        ]
        for pattern in namespace_patterns:
            match = re.search(pattern, query_lower)
            if match:
                entities.append(
                    {"type": "namespace", "value": match.group(1), "confidence": 0.95}
                )
                break

        return entities

    def _extract_action_type(self, query: str) -> Optional[str]:
        """Extract the action type from query."""
        for keyword in self.ACTION_KEYWORDS:
            if keyword in query:
                return keyword
        return None

    def _extract_target_resource(
        self, query: str, entities: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Extract target resource from query."""
        # Look for resource entities
        resource_entities = [e for e in entities if e.get("type") == "resource"]
        if resource_entities:
            return resource_entities[0]["value"]

        # Try to extract from quoted strings
        quoted = re.findall(r'"([^"]*)"', query)
        if quoted:
            return quoted[0]

        return None
