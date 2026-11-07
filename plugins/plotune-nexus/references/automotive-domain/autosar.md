# AUTOSAR Architecture Review

Use this reference for offline AUTOSAR Classic and Adaptive architecture review. It is not a schema replacement and does not include licensed AUTOSAR content.

## Classic Review Points

- Software component type and responsibility
- sender-receiver and client-server interfaces
- runnable events and timing assumptions
- init values and safe startup behavior
- diagnostic, COM, NVM, watchdog, and E2E interactions
- mapping between SWC ports, signals, DIDs, and requirements

## Adaptive Review Points

- executables, processes, service instances, and machine deployment
- ara::com service contracts and update rates
- execution management and health monitoring assumptions
- logging, diagnostics, and state-management integration
- network binding and deployment manifest consistency

## ARXML Checks

- duplicate `SHORT-NAME`s in relevant scope
- unresolved reference paths
- package path assumptions
- partial ECU extract versus system description context
- namespace and schema-version variance

## Script Helpers

Run from the plugin package root when script execution is allowed:

- `python3 scripts/automotive/autosar_manifest_inspect.py --arxml system.arxml --manifest machine_manifest.json --format json`
- `python3 scripts/automotive/autosar_architecture_report.py --arxml system.arxml --manifest machine_manifest.json --format json`

If command execution is restricted, do not bypass it. Review snippets manually and state that deterministic script checks were not run.

## Nexus Handoff

Use Nexus skills when architecture review turns into live bus capture, diagnostic validation, containerized tool execution, or managed test sequences.
