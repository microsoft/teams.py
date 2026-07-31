# Agent instructions

## Tests

- Tests should be thoughtfully created to exercise the intended purpose, not just to turn green. When possible, do red-green tests: confirm the test fails when the behavior is wrong and passes when it is right, so it actually guards the behavior it claims to.
- Consider mocking carefully. The goal is to guard against regressions for the intended behavior, so mocks should mirror the real contract (types, shapes, and edge values like `null`) rather than a simplified stand-in that a broken implementation could still satisfy.
