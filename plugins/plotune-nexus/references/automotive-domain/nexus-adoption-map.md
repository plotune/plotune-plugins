# Automotive To Nexus Adoption Map

Use this reference when an offline automotive workflow should become a bounded Plotune Nexus hardware workflow.

## Offline First

Work without hardware should start from local artifacts and explicit engineering intent:

- DBC files and CAN traces
- UDS request/response bytes, DTC reports, ODX/PDX notes
- A2L/LAB files, measurement lists, calibration change logs
- ARXML or Adaptive manifests
- requirements, hazards, test plans, safety/security workproducts

Do not invent active hardware actions from domain knowledge alone. Treat offline findings as preparation, not permission to send frames, write calibrations, run routines, or flash an ECU.

## Handoff To Nexus Skills

- CAN or DBC findings -> `plotune-can-workflows`
- UDS or DoIP execution -> `plotune-uds-doip-diagnostics`
- XCP measurement or calibration -> `plotune-xcp-workflows`
- UART console or SLCAN setup -> `plotune-uart-workflows`
- large outputs or shared evidence -> `plotune-artifacts-drives`
- repeatable bench runs -> `plotune-test-sequences-reporting`
- gateways, managed containers, or device-local tool execution -> `plotune-gateways-containers`

Before any Nexus live action, read the relevant Nexus runtime resources and confirm interfaces, targets, leases, and artifacts.

## Safe Adoption Pattern

1. Analyze files offline and summarize exact findings.
2. Separate evidence from assumptions.
3. Ask for missing ECU, bus, target, or safety context.
4. Convert the plan into bounded Nexus operations with explicit stop conditions.
5. Capture results as artifacts or reports for traceability.

## Boundaries

- This plugin is an engineering aid, not certification evidence.
- Licensed standards and qualified safety/security review remain authoritative.
- Offline scripts do not open CAN sockets, serial ports, DoIP sockets, or cloud connections.
