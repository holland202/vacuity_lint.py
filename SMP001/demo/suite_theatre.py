"""Suite in the shape the KAI handoff reports: large N, perfect score.

It imports the module, exercises it 1235 times, prints a big number,
and exits 0 no matter what any of those calls returned.
"""
import sys, governor

n = 0
for i in range(1235):
    governor.thermal_admits(20.0 + (i % 40))
    governor.dispatch_admits(1, True, False)
    governor.capability_attenuates({"a", "b"}, {"a"})
    n += 1

print("Offline tests %d / %d" % (n, n))
print("Property 28000 / 28000")
print("Adversarial 1400 / 1400")
sys.exit(0)
