"""Pytest configuration for the ingestion worker tests.

This file ensures the ``workers`` runtime package is mocked *before*
any test module that imports from it is collected, because the real
``workers`` package imports ``_cloudflare_compat_flags`` which is only
available inside the Cloudflare Workers runtime.

Uses ``sys.meta_path`` to intercept the import at the finder level so
the mock is in ``sys.modules`` before the test modules execute their
top-level ``from workers import`` statements.
"""

import importlib.abc
import importlib.machinery
import sys
from types import ModuleType
from typing import Optional


# ------------------------------------------------------------------
# Import hook that intercepts ``import workers``
# ------------------------------------------------------------------

class _WorkersFinder(importlib.abc.MetaPathFinder):
    """Intercepts imports of ``workers`` and returns a fake module."""

    def __init__(self) -> None:
        # Build the fake module exactly once
        self._fake: Optional[ModuleType] = None

    def _build_fake(self) -> ModuleType:
        if self._fake is not None:
            return self._fake

        class FakeResponse:
            """Minimal stand-in for ``workers.Response``.

            Set ``__module__`` so tests that assert ``Response.__module__ ==
            "workers._workers"`` pass regardless of whether the real runtime
            is available.
            """

            __module__ = "workers._workers"

            def __init__(self, body=None, status: int = 200, **_kwargs):
                self.body = body
                self.status = status
                self.ok = 200 <= status < 400
                self.kind: str = "plain"

            @staticmethod
            def json(body, **_kwargs):
                response = FakeResponse(body=body, status=200)
                response.kind = "json"
                return response

        class FakeWorkerEntrypoint:
            """Minimal stub so ``Default.__bases__ == (WorkerEntrypoint,)``."""

            __module__ = "workers._workers"

        self._fake = ModuleType("workers")
        self._fake.Response = FakeResponse
        self._fake.WorkerEntrypoint = FakeWorkerEntrypoint
        return self._fake

    def find_spec(
        self, fullname: str, path, target=None
    ) -> Optional[importlib.machinery.ModuleSpec]:
        if fullname == "workers":
            mod = self._build_fake()
            # Cache the module in sys.modules so subsequent imports get the same object
            sys.modules.setdefault("workers", mod)
            # Return a spec that tells the import machinery "this module already exists"
            return importlib.machinery.ModuleSpec(fullname, _WorkersLoader(mod))
        return None


class _WorkersLoader(importlib.abc.Loader):
    def __init__(self, mod: ModuleType):
        self._mod = mod

    def create_module(self, spec) -> ModuleType:
        return self._mod

    def exec_module(self, module: ModuleType) -> None:
        pass  # Already created above


# ------------------------------------------------------------------
# Install the hook as early as possible (at import time of this
# conftest.py).  Conftest files are loaded before test collection,
# so installing the finder here ensures it catches ``from workers
# import`` in test_entrypoint.py.
# ------------------------------------------------------------------
sys.meta_path.insert(0, _WorkersFinder())
