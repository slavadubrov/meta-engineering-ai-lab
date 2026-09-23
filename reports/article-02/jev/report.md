# Jev compared with exact matching

Model: `typesafe/jev-1.13` through `https://openrouter.ai/api/alpha/decisions`. Status: **completed**. Billed cost: $0.000172.

Labels were written for this demo and have not been reviewed by a second person. hard_failures are recorded observations used to test composition; this study does not execute the memory tool.

| Method | Scored against | Agreement | False accepts | False rejects |
| --- | --- | ---: | ---: | ---: |
| Exact match | `semantic_accept` | 8/10 | 0/3 | 2/7 |
| Exact match + hard checks | `reference_accept` | 8/10 | 0/6 | 2/4 |
| Jev, answer only | `semantic_accept` | 10/10 | 0/3 | 0/7 |
| Jev + hard checks | `reference_accept` | 10/10 | 0/6 | 0/4 |
| Jev, given state evidence | `reference_accept` | 10/10 | 0/6 | 0/4 |

`semantic_accept` asks only whether the answer is right. `reference_accept` also requires the recorded hard checks to pass.

| Case | Category | semantic_accept | reference_accept | Exact match | Exact match + hard checks | Jev, answer only | Jev + hard checks | Jev, given state evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c01 | correct | accept | accept | accept | accept | accept | accept | accept |
| c02 | incorrect | reject | reject | reject | reject | reject | reject | reject |
| c03 | correct answer, wrong state | accept | reject | accept | reject | accept | reject | reject |
| c04 | temporally stale | reject | reject | reject | reject | reject | reject | reject |
| c05 | owner isolation | accept | reject | accept | reject | accept | reject | reject |
| c06 | deletion | accept | reject | accept | reject | accept | reject | reject |
| c07 | partially supported | reject | reject | reject | reject | reject | reject | reject |
| c08 | correct abstention | accept | accept | accept | accept | accept | accept | accept |
| c09 | valid paraphrase | accept | accept | reject | reject | accept | accept | accept |
| c10 | valid paraphrase | accept | accept | reject | reject | accept | accept | accept |

## Calls

- `answer_only`: completed, returned model `typesafe/jev-1.13-20260917`, 0.38 s, 1793 input / 303 output tokens, cost $0.000075, lowest returned confidence 0.84.
- `state_aware`: completed, returned model `typesafe/jev-1.13-20260917`, 0.35 s, 2297 input / 303 output tokens, cost $0.000096, lowest returned confidence 0.94.

These are ten public, authored examples. They show how the composition works; they are not a measured error rate and not a human calibration.
