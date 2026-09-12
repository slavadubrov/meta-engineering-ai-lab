# Recorded experiments

The article uses `agent-study-03`, recorded September 11, 2026 with validated,
versioned memory records and the fixed temporal conflict policy. Three campaigns
each made four model calls: subject/date filters, deduplication, a confidence
threshold of 0.6, then stop. Nine proposals were evaluated; none failed validation.
All selected configurations passed 20/20 public scenarios. Estimated provider
cost: $0.0391774, shown as $0.039177 in the article.

`article-01.6` records the four hand-prepared teaching configurations against the
same source. Their scores remain 13/20, 19/20, 19/20, and 16/20. These prepared
answers are not supplied as initial candidates to the live agent.

## Earlier evidence

- `agent-pilot-01`: one API and Structured Outputs smoke call, reaching 19/20. Its provisional cost omitted the cache-write surcharge. Recomputed from saved usage, the estimate is $0.00535395 rather than $0.0043716; the original report remains unchanged.
- `agent-study-01`: three development campaigns, 12 calls, including three invalid proposals. Rejection feedback did not yet contain the complete rejected output. Estimated cost: $0.036043.
- `agent-study-02`: three campaigns with complete rejection feedback and current-evidence references, before record schema validation. They used 4, 4, and 3 calls, evaluated eight proposals, and each stopped at 20/20. Estimated cost: $0.03412255.
- `article-01.1` through `article-01.5`: earlier deterministic evidence with its original source metadata and repeat counts. Use matching source revisions to reproduce it.

All 36 saved live calls together have a token-based cost estimate of $0.1146969.
The calculation includes cache-write surcharges and ignores cache-read discounts.
It is not an invoice. Model rates were rechecked against the official model page
on September 11, 2026 and had not changed.

Historical artifacts are never overwritten. For the current implementation, use
`lab verify artifacts/agent-study-03 --source` and
`lab verify artifacts/article-01.6 --source`. Source-file hashes identify exactly
what ran. The manifests also record the source commit and a dirty working tree
because documentation changes and new evidence directories were present.
