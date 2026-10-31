"""Suite that actually constrains governor.py."""
import sys, governor

checks = []
checks.append(governor.thermal_admits(85.0) is True)
checks.append(governor.thermal_admits(85.1) is False)
checks.append(governor.dispatch_admits(1, True, False) is True)
checks.append(governor.dispatch_admits(2, True, False) is False)
checks.append(governor.dispatch_admits(1, True, True) is False)
checks.append(governor.dispatch_admits(1, False, False) is False)
checks.append(governor.capability_attenuates({"a", "b"}, {"a"}) is True)
checks.append(governor.capability_attenuates({"a"}, {"a"}) is False)
checks.append(governor.capability_attenuates({"a"}, {"a", "b"}) is False)

print("%d/%d PASS" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
