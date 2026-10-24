# Phase 5 implementation plan

Status: completed and verified for Phase 5 review; no Phase 6 work. See ../PHASE5_ACCEPTANCE.md.

1. Inspect existing provider, schemas, database and regression tests. Preserve a database baseline.
2. Add bounded OR-Tools CVRP/TSP, multi-depot, paired pickups, hard windows, distance/duration limits, transparent objectives and independent solution validation.
3. Reuse OSRM with validated asymmetric road matrices, 24-hour cache, small batches, quota limits and real final route geometry. No Euclidean fallback.
4. Add additive normalized logistics persistence, guarded local APIs and bounded asynchronous jobs. Review SQL before migration.
5. Build scenario/fleet/delivery/results/comparison/history UI, GIS/place/map/import inputs and attributed exports/print reports.
6. Run offline regression/constraint tests, live PostGIS/routing scenarios A–H, frontend checks/build and browser verification. Record actual limitations and acceptance evidence.

Scope limits: 20 delivery stops, 4 depots, 6 enabled vehicles, 1–20 second solve, one active optimization job. Capacity is one consistent user-defined integer unit. Time is seconds from scenario day start. Cost is user-supplied MYR. Public car routing does not verify truck access. Optional fuel and driver costs are explicit inputs; no invented tolls.

Primary references:
- https://developers.google.com/optimization/routing/cvrp
- https://developers.google.com/optimization/routing/vrptw
- https://developers.google.com/optimization/routing/pickup_delivery
- https://developers.google.com/optimization/routing/routing_options
- https://routing.openstreetmap.de/about.html

