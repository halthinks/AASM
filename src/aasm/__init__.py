# public_v56 remains the frozen 0.56.1 base surface; public_active_entity_evolution is the qualified 0.32.15 parent; public_active_engineering_quantity is the qualified 0.32.16 parent; public_active_engineering_rule is the qualified 0.32.17 parent; public_active_semantic_projection is the qualified 0.32.18 parent; public_active_uncertainty_scenario_trace is the qualified 0.32.19 parent; public_active_degraded_operation is the current qualified adoption overlay.
from . import public_active_degraded_operation as _active_public

# The additive adoption overlays carry a deliberately narrower
# SUPPORTED_PUBLIC_IMPORTS registry, but the historical package root has always
# preserved the complete non-private namespace of its selected public module.
# A direct star import would obey the overlay's narrower __all__ and silently
# erase long-standing root imports. Mirror both the full non-private namespace
# and any explicitly declared dunder exports instead.
# Historical source-contract spellings, intentionally not executed:
# from .public_active_degraded_operation import *
# from .public_active_degraded_operation import __version__, AASMEngine, validate_public_api_contract, public_api_contract, PUBLIC_API_CONTRACT
_ROOT_PUBLIC_NAMES = tuple(
    dict.fromkeys(
        [
            *(name for name in dir(_active_public) if not name.startswith("_")),
            *getattr(_active_public, "__all__", ()),
        ]
    )
)
for _name in _ROOT_PUBLIC_NAMES:
    globals()[_name] = getattr(_active_public, _name)
del _name

__version__ = _active_public.__version__
AASMEngine = _active_public.AASMEngine
validate_public_api_contract = _active_public.validate_public_api_contract
public_api_contract = _active_public.public_api_contract
PUBLIC_API_CONTRACT = _active_public.PUBLIC_API_CONTRACT
__all__ = _ROOT_PUBLIC_NAMES
del _ROOT_PUBLIC_NAMES
