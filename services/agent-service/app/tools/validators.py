"""
Input validation and security validators for tools.
"""

import re
from typing import List, Optional, Set
from pydantic import BaseModel, validator, ValidationError

# Allowed Kubernetes namespaces - whitelist approach
ALLOWED_NAMESPACES: Set[str] = {
    "default",
    "kube-system",
    "kube-public",
    "kube-node-lease",
}

# Dangerous patterns that should never appear in inputs
DANGEROUS_PATTERNS: List[re.Pattern] = [
    re.compile(r"[;&|]"),  # Command chaining
    re.compile(r"`[^`]*`"),  # Backtick command substitution
    re.compile(r"\$\([^)]*\)"),  # $(...) command substitution
    re.compile(r"\$\{[^}]*\}"),  # ${...} variable expansion
    re.compile(r">|>>|<"),  # Redirections
    re.compile(r"\|\|"),  # OR operator
    re.compile(r"&&"),  # AND operator
    re.compile(r"[\x00-\x1f\x7f]"),  # Control characters
]

# Kubernetes resource name validation
RESOURCE_NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
MAX_RESOURCE_NAME_LENGTH = 253


class ValidationResult:
    """Result of validation operation."""

    def __init__(self, is_valid: bool, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.error_message = error_message

    def __bool__(self) -> bool:
        return self.is_valid

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(True)

    @classmethod
    def failure(cls, message: str) -> "ValidationResult":
        return cls(False, message)


class K8sResourceName(BaseModel):
    """Validates Kubernetes resource names."""

    name: str

    @validator("name")
    def validate_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Resource name cannot be empty")

        if len(v) > MAX_RESOURCE_NAME_LENGTH:
            raise ValueError(
                f"Resource name too long (max {MAX_RESOURCE_NAME_LENGTH} characters)"
            )

        if not RESOURCE_NAME_PATTERN.match(v):
            raise ValueError(
                "Resource name must consist of lowercase alphanumeric characters or '-', "
                "and must start and end with an alphanumeric character"
            )

        return v


class K8sNamespace(BaseModel):
    """Validates Kubernetes namespace names."""

    namespace: str

    @validator("namespace")
    def validate_namespace(cls, v: str) -> str:
        if not v:
            raise ValueError("Namespace cannot be empty")

        # Allow explicit namespace addition through configuration
        # For now, use whitelist approach
        if v not in ALLOWED_NAMESPACES and not v.startswith(
            ("app-", "system-", "monitoring")
        ):
            raise ValueError(f"Namespace '{v}' is not in allowed list")

        if len(v) > MAX_RESOURCE_NAME_LENGTH:
            raise ValueError("Namespace name too long")

        return v


class SafeString(BaseModel):
    """Validates that a string is safe from command injection."""

    value: str

    @validator("value")
    def validate_safety(cls, v: str) -> str:
        if not v:
            return v

        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(v):
                matched = pattern.search(v).group()
                raise ValueError(f"Potentially dangerous pattern detected: '{matched}'")

        return v


class PodQueryInput(BaseModel):
    """Input validation for pod-related queries."""

    namespace: Optional[str] = "default"
    pod_name: Optional[str] = None
    label_selector: Optional[str] = None

    @validator("namespace")
    def validate_namespace(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return K8sNamespace(namespace=v).namespace

    @validator("pod_name")
    def validate_pod_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return K8sResourceName(name=v).name

    @validator("label_selector")
    def validate_label_selector(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return SafeString(value=v).value


class LogQueryInput(BaseModel):
    """Input validation for log queries."""

    pod_name: str
    namespace: Optional[str] = "default"
    container: Optional[str] = None
    tail_lines: Optional[int] = 100

    @validator("pod_name")
    def validate_pod_name(cls, v: str) -> str:
        return K8sResourceName(name=v).name

    @validator("namespace")
    def validate_namespace(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return K8sNamespace(namespace=v).namespace

    @validator("container")
    def validate_container(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return SafeString(value=v).value

    @validator("tail_lines")
    def validate_tail_lines(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("tail_lines must be non-negative")
        if v > 10000:
            raise ValueError("tail_lines cannot exceed 10000")
        return v


class DescribeResourceInput(BaseModel):
    """Input validation for resource describe operations."""

    resource_type: str
    resource_name: str
    namespace: Optional[str] = "default"

    ALLOWED_RESOURCE_TYPES: Set[str] = {
        "pod",
        "pods",
        "service",
        "services",
        "svc",
        "deployment",
        "deployments",
        "deploy",
        "configmap",
        "configmaps",
        "cm",
        "secret",
        "secrets",
        "node",
        "nodes",
        "namespace",
        "namespaces",
        "ns",
        "ingress",
        "ingresses",
        "persistentvolume",
        "persistentvolumes",
        "pv",
        "persistentvolumeclaim",
        "persistentvolumeclaims",
        "pvc",
        "replicaset",
        "replicasets",
        "rs",
        "statefulset",
        "statefulsets",
        "daemonset",
        "daemonsets",
        "ds",
        "job",
        "jobs",
        "cronjob",
        "cronjobs",
    }

    @validator("resource_type")
    def validate_resource_type(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in cls.ALLOWED_RESOURCE_TYPES:
            raise ValueError(
                f"Resource type '{v}' is not allowed. Allowed types: {', '.join(sorted(cls.ALLOWED_RESOURCE_TYPES))}"
            )
        return v_lower

    @validator("resource_name")
    def validate_resource_name(cls, v: str) -> str:
        return K8sResourceName(name=v).name

    @validator("namespace")
    def validate_namespace(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return K8sNamespace(namespace=v).namespace


def validate_no_shell_injection(value: str) -> ValidationResult:
    """Validate that a string contains no shell injection attempts."""
    try:
        SafeString(value=value)
        return ValidationResult.success()
    except ValidationError as e:
        return ValidationResult.failure(str(e))


def validate_k8s_resource_name(name: str) -> ValidationResult:
    """Validate a Kubernetes resource name."""
    try:
        K8sResourceName(name=name)
        return ValidationResult.success()
    except ValidationError as e:
        return ValidationResult.failure(str(e))


def validate_namespace(namespace: str) -> ValidationResult:
    """Validate a Kubernetes namespace."""
    try:
        K8sNamespace(namespace=namespace)
        return ValidationResult.success()
    except ValidationError as e:
        return ValidationResult.failure(str(e))


def validate_resource_type(resource_type: str) -> ValidationResult:
    """Validate a Kubernetes resource type."""
    try:
        DescribeResourceInput(resource_type=resource_type, resource_name="test")
        return ValidationResult.success()
    except ValidationError as e:
        return ValidationResult.failure(str(e))


def sanitize_input(value: str) -> str:
    """Sanitize input by removing dangerous characters."""
    if not value:
        return value

    # Remove null bytes and control characters
    sanitized = re.sub(r"[\x00-\x1f\x7f]", "", value)

    return sanitized
