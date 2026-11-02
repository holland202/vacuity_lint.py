"""A toy governance module, deliberately in the shape of a KAI-style gate."""

CEILING_C = 85.0
MAX_UNITS_PER_DISPATCH = 1


def thermal_admits(temp_c):
    return temp_c <= CEILING_C


def dispatch_admits(units, authorized, revoked):
    if revoked:
        return False
    if not authorized:
        return False
    return units <= MAX_UNITS_PER_DISPATCH


def capability_attenuates(parent_scope, child_scope):
    return child_scope.issubset(parent_scope) and child_scope != parent_scope
