# Validation Matrix

| ID | Diagram | Type | Expected `planttoxmi` Result | Purpose |
| --- | --- | --- | --- | --- |
| VAL-001 | importable/architecture_components.puml | Component | Convert and EA import | Full RTOS architecture. |
| VAL-002 | importable/safety_services_components.puml | Component | Convert and EA import | Safety service dependencies. |
| VAL-003 | importable/startup_sequence.puml | Sequence | Convert and EA import | Startup and admission flow. |
| VAL-004 | importable/periodic_scheduling_sequence.puml | Sequence | Convert and EA import | Tick and task dispatch flow. |
| VAL-005 | importable/watchdog_recovery_sequence.puml | Sequence | Convert and EA import | Checkpoint and watchdog behavior. |
| VAL-006 | importable/fault_containment_sequence.puml | Sequence | Convert and EA import | Fault reporting and safe-state transition. |
| VAL-007 | importable/safety_requirements.puml | Requirements | Convert and EA import | Safety requirement decomposition using EA Requirement elements. |
| VAL-008 | importable/kernel_services_components.puml | Component | Convert and EA import | Kernel service allocation and deterministic service dependencies. |
| VAL-009 | importable/platform_services_components.puml | Component | Convert and EA import | Platform abstraction and hardware driver dependencies. |
| VAL-010 | importable/application_integration_components.puml | Component | Convert and EA import | Application task access through controlled RTOS APIs. |
| VAL-011 | importable/safety_requirement_traceability.puml | Requirements | Convert and EA import | Requirement satisfy, verify, refine, trace, and containment relationships. |
| VAL-101 | importable/kernel_classes.puml | Class | Convert and EA import | Kernel data and service types. |
| VAL-102 | importable/runtime_snapshot_object.puml | Object | Convert and EA import | Runtime task-table snapshot. |
| VAL-103 | importable/safety_architecture_packages.puml | Package | Convert and EA import | Package-level ownership and dependencies. |
| VAL-104 | importable/kernel_composite_structure.puml | Composite structure | Convert and EA import | Kernel internal parts and ports. |
| VAL-105 | importable/ecu_deployment.puml | Deployment | Convert and EA import | ECU hardware and deployed artifacts. |
| VAL-106 | importable/safety_profile.puml | Profile | Convert and EA import | Safety-specific stereotypes. |
| VAL-201 | importable/developer_use_cases.puml | Use case | Convert and EA import | Developer and diagnostic workflows. |
| VAL-202 | importable/scheduler_activity.puml | Activity | Convert and EA import | Scheduler tick activity flow. |
| VAL-203 | importable/task_lifecycle_state.puml | State | Convert and EA import | Task lifecycle state transitions. |
| VAL-204 | importable/fault_triage_communication.puml | Communication | Convert and EA import | Numbered collaboration during fault triage. |
| VAL-205 | importable/startup_interaction_overview.puml | Interaction overview | Convert and EA import | Startup scenario branching across interactions. |
| VAL-206 | importable/scheduler_timing.puml | Timing | Convert and EA import | Scheduler, task, and watchdog timing states. |
