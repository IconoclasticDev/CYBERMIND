from __future__ import annotations

"""HARD SECURITY BOUNDARY for Strix execution.

Nothing in the application may invoke Strix except through
`SafetyGate.authorize()`. The gate enforces:

1. Only explicitly registered targets can be scanned (requirement #2/#14).
2. Only classified environments are permitted: SANDBOX, REPLAY,
   AUTHORIZED_TEST.
3. Autonomous actions hard-fail outside SANDBOX authorization (#8).
4. Local network / loopback / link-local / private-link metadata addresses are
   additionally blocked for AUTHORIZED_TEST registrations (defense in depth).
"""

import ipaddress
import time
from typing import Any
from urllib.parse import urlparse

from app.adapters.strix.schemas import EnvironmentClass, TargetRegistration
from app.core.logging import log

ALLOWED_ENVIRONMENTS = {EnvironmentClass.SANDBOX, EnvironmentClass.REPLAY, EnvironmentClass.AUTHORIZED_TEST}

# Loopback/metadata ranges are never valid AUTHORIZED_TEST scan targets.
_FORBIDDEN_TEST_NETS = tuple(
    ipaddress.ip_network(n)
    for n in ("127.0.0.0/8", "169.254.0.0/16", "::1/128", "fe80::/10")
)


class AuthorizationError(Exception):
    """Raised when a Strix execution is not authorized. Carries a code for the API layer."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SafetyGate:
    """Registry + authorization check for Strix targets."""

    def __init__(self) -> None:
        self._targets: dict[str, TargetRegistration] = {}

    # ------------------------------------------------------------- registry
    def register(
        self,
        target: str,
        environment: EnvironmentClass | str,
        label: str = "",
        notes: str = "",
    ) -> TargetRegistration:
        target = (target or "").strip()
        if not target:
            raise AuthorizationError("INVALID_TARGET", "target must be a non-empty string")
        if len(target) > 512:
            raise AuthorizationError("INVALID_TARGET", "target too long")
        try:
            env = EnvironmentClass(environment)
        except ValueError:
            raise AuthorizationError(
                "INVALID_ENVIRONMENT",
                f"environment must be one of: {', '.join(e.value for e in ALLOWED_ENVIRONMENTS)}",
            ) from None
        if env not in ALLOWED_ENVIRONMENTS:
            raise AuthorizationError("INVALID_ENVIRONMENT", f"environment {env} is not permitted")
        self._block_forbidden_target_class(target, env)
        reg = TargetRegistration(
            target=target,
            environment=env,
            label=label or target,
            registered_at=time.time(),
            notes=notes,
        )
        self._targets[target] = reg
        log.info("strix target registered: %s (%s)", target, env.value)
        return reg

    def unregister(self, target: str) -> bool:
        return self._targets.pop((target or "").strip(), None) is not None

    def get(self, target: str) -> TargetRegistration | None:
        return self._targets.get((target or "").strip())

    def list_targets(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._targets.values()]

    # ------------------------------------------------------- authorization
    def authorize(self, target: str, environment: EnvironmentClass | str | None = None) -> TargetRegistration:
        """Authorize a Strix execution against `target`. Raises AuthorizationError."""
        reg = self.get(target)
        if reg is None:
            raise AuthorizationError(
                "TARGET_NOT_REGISTERED",
                f"target '{target}' is not registered for validation; register it first",
            )
        if reg.environment not in ALLOWED_ENVIRONMENTS:
            raise AuthorizationError("ENVIRONMENT_NOT_PERMITTED", f"environment {reg.environment} is not permitted")
        if environment is not None:
            env = EnvironmentClass(environment)
            if env is not reg.environment:
                raise AuthorizationError(
                    "ENVIRONMENT_MISMATCH",
                    f"declared environment {env.value} does not match registration {reg.environment.value}",
                )
        return reg

    def authorize_autonomous(self, target: str) -> TargetRegistration:
        """Autonomous-sandbox mode: only SANDBOX environments may proceed."""
        reg = self.authorize(target)
        if reg.environment is not EnvironmentClass.SANDBOX:
            raise AuthorizationError(
                "AUTONOMOUS_NOT_SANDBOX",
                "autonomous mode is only permitted inside SANDBOX environments",
            )
        return reg

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _host_ips(target: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        hosts: list[str] = []
        parsed = urlparse(target)
        if parsed.hostname:
            hosts.append(parsed.hostname)
        if "//" not in target and "/" not in target:
            hosts.append(target.strip("[]"))
        ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        for h in hosts:
            try:
                ips.append(ipaddress.ip_address(h.strip("[]")))
            except ValueError:
                continue
        return ips

    def _block_forbidden_target_class(self, target: str, env: EnvironmentClass) -> None:
        if env is not EnvironmentClass.AUTHORIZED_TEST:
            return  # SANDBOX/REPLAY explicitly cover loopback test rigs
        for ip in self._host_ips(target):
            for net in _FORBIDDEN_TEST_NETS:
                if ip in net:
                    raise AuthorizationError(
                        "FORBIDDEN_TARGET",
                        f"AUTHORIZED_TEST targets may not address loopback/link-local/metadata ranges ({ip})",
                    )


def require_environment(reg: TargetRegistration, env: EnvironmentClass) -> None:
    if reg.environment is not env:
        raise AuthorizationError("ENVIRONMENT_MISMATCH", f"expected {env.value} environment")
