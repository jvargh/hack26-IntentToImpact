# ENG-04-01: focused Intent Continuity projection

`graph.build_graph` produces a schema-valid P06 from an authorized closed set of
records and an already-produced evaluation. It performs no network, file writes,
predicate evaluation, approval, or runtime change.

The caller supplies the trusted run/scenario, loaded records, selected evaluation
artifact ID, source case revision and projection cutoff. Reference integrity is
validated before and after projection. Unknown evidence becomes an explicit gap;
a missing referenced record is an error rather than a fabricated supported node.

- Scenario links describe intended mappings, not proof of implementation or approval.
- A failed evaluation highlights the exact promise and declared failed property.
- A pending correction leaves the existing breached edge broken.
- A supported evaluation edge means the referenced evaluation reports success for its
  own phase and scope. It does not establish a new verdict or guarantee current freshness.
- The evaluator/API must refresh or mark stale evaluations before treating the graph
  as current runtime evidence. `as_of` is projection time, not a new observation time.
- Graph nodes and the accessible ordered list have identical relationships.
- Inputs are not mutated. No graph database, traversal service or editing endpoint exists.
- Allowed actions are empty here; the owning capability/experience API supplies
  permitted actions rather than the graph authorizing them.

Run the bounded tests:

```powershell
& .\contracts\.venv\Scripts\python.exe -B -m unittest discover -s .\tests\continuity -p test_graph.py -v
& .\contracts\.venv\Scripts\python.exe -B .\tests\continuity\record_evidence.py
```

Fixtures are explicitly synthetic. Even a `verified` fixture demonstrates graph
mapping only, not Azure restoration, browser accessibility, or a passed human UX gate.
