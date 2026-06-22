"""Load external providers from configuration.

Provider keys support:

- ``local``: handled by built-in local adapters.
- ``package.module:factory`` or ``package.module.ProviderClass``: imported and
  instantiated/called at runtime.

Factories/classes may either accept no arguments or a single ``Settings``
argument. This keeps production adapters outside core pipeline code while still
making them configurable through environment variables.
"""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from typing import Any

from trendos.config import Settings


def load_provider(spec: str, settings: Settings) -> object:
    """Import and create a provider object from a dotted path spec."""
    module_name, attr_name = _split_spec(spec)
    module = importlib.import_module(module_name)
    target = getattr(module, attr_name)

    if inspect.isclass(target):
        return _build(target, settings)
    if callable(target):
        return _call(target, settings)
    return target


def _split_spec(spec: str) -> tuple[str, str]:
    if ":" in spec:
        module_name, attr_name = spec.split(":", 1)
    else:
        module_name, _, attr_name = spec.rpartition(".")
    if not module_name or not attr_name:
        raise ValueError(
            "Provider key must be 'local' or an import path like "
            "'package.module:ProviderFactory'"
        )
    return module_name, attr_name


def _build(cls: type, settings: Settings) -> object:
    signature = inspect.signature(cls)
    required = [
        p
        for p in signature.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    ]
    if not required:
        return cls()
    if len(required) == 1:
        return cls(settings)
    raise TypeError(f"Provider class {cls.__module__}.{cls.__name__} has unsupported init")


def _call(factory: Callable[..., Any], settings: Settings) -> object:
    signature = inspect.signature(factory)
    required = [
        p
        for p in signature.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    ]
    if not required:
        return factory()
    if len(required) == 1:
        return factory(settings)
    raise TypeError(f"Provider factory {factory} has unsupported signature")
