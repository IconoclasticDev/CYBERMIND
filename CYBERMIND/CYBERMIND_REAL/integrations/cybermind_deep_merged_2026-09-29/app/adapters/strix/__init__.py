"""Strix integration: controlled adversarial validation adapter.

Public surface:
    StrixRunner, StrixClient, SafetyGate, AuthorizationError,
    StrixArtifactParser, ArtifactCollector, schemas (EnvironmentClass, ...)
"""

from app.adapters.strix.artifacts import ArtifactCollector
from app.adapters.strix.client import StrixClient
from app.adapters.strix.parser import StrixArtifactParser
from app.adapters.strix.runner import StrixRunner
from app.adapters.strix.safety import AuthorizationError, SafetyGate
from app.adapters.strix.schemas import (
    EnvironmentClass,
    ExecutionMode,
    NormalizedFinding,
    RunStatus,
    StrixRunConfig,
    StrixRunRecord,
    TargetRegistration,
    ValidationComparison,
)

__all__ = [
    "ArtifactCollector",
    "AuthorizationError",
    "EnvironmentClass",
    "ExecutionMode",
    "NormalizedFinding",
    "RunStatus",
    "SafetyGate",
    "StrixArtifactParser",
    "StrixClient",
    "StrixRunConfig",
    "StrixRunRecord",
    "StrixRunner",
    "TargetRegistration",
    "ValidationComparison",
]
