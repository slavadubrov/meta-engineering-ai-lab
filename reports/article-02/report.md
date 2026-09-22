# Evaluator exploit experiment

Original synthetic fixtures authored with knowledge of the candidates. Audit cases are withheld from the selector, not blind to the authors; after export all cases are public.

Executions: 1600. Provider calls: 0. Selected by proxy: threshold-0.2-k1.

| Candidate | Development | Unwanted writes | Audit | Previous suite | Full policy |
| --- | ---: | ---: | ---: | ---: | --- |
| threshold-0.2-k1 | 8/8 | 4 | 6/12 | 16/20 | unwanted development writes changed state; audit answers below the required fraction; unwanted audit writes changed state; previous article regression suite failed |
| threshold-0.2-k3 | 8/8 | 4 | 6/12 | 16/20 | unwanted development writes changed state; audit answers below the required fraction; unwanted audit writes changed state; previous article regression suite failed; development context budget exceeded |
| threshold-0.4-k1 | 8/8 | 0 | 6/12 | 19/20 | audit answers below the required fraction; unwanted audit writes changed state; previous article regression suite failed |
| threshold-0.4-k3 | 8/8 | 0 | 6/12 | 19/20 | audit answers below the required fraction; unwanted audit writes changed state; previous article regression suite failed |
| threshold-0.6-k1 | 6/8 | 0 | 12/12 | 20/20 | eligible for review |
| threshold-0.6-k3 | 6/8 | 0 | 12/12 | 20/20 | eligible for review |
| threshold-0.7-k1 | 6/8 | 0 | 6/12 | 19/20 | audit answers below the required fraction; previous article regression suite failed |
| threshold-0.7-k3 | 6/8 | 0 | 6/12 | 19/20 | audit answers below the required fraction; previous article regression suite failed |

All repeats use fresh state. Quality is deterministic; timing varies.
Paired intervals resample audit scenarios; synthetic case mix limits inference.
Human calibration and a genuinely blind generalization study remain unmeasured.
