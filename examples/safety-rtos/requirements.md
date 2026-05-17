# Requirements

## Context

The SafetyLite RTOS runs on a single automotive microcontroller used by a
domain ECU. It provides deterministic scheduling, fault containment, watchdog
servicing, memory protection, diagnostics, and controlled application APIs for
safety-related software components.

SafetyLite is intentionally small enough to remain analyzable. Requirements are
allocated to architecture elements and detailed design flows so the PlantUML to
XMI conversion can be stressed with realistic traceability, not only isolated
diagram shapes.

## System Requirements

| ID | Requirement |
| --- | --- |
| REQ-001 | The RTOS shall provide fixed-priority preemptive scheduling for periodic and event-triggered tasks. |
| REQ-002 | The RTOS shall isolate safety-critical tasks from non-critical tasks using MPU regions where hardware support exists. |
| REQ-003 | The RTOS shall provide bounded inter-task communication through queues and event flags. |
| REQ-004 | The RTOS shall detect task deadline misses and report them to the health monitor. |
| REQ-005 | The RTOS shall provide startup self-checks before safety tasks are admitted to run. |
| REQ-006 | The RTOS shall expose a platform abstraction for timer, interrupt, MPU, watchdog, reset, and nonvolatile drivers. |
| REQ-007 | The RTOS shall maintain an explicit system mode covering initialization, normal operation, degraded operation, safe state, and reset pending. |
| REQ-008 | The RTOS shall expose only validated service calls to application tasks through the Safety Application API. |
| REQ-009 | The RTOS shall maintain configuration data separately from runtime state. |
| REQ-010 | Scheduler tick processing shall complete within 50 microseconds on the reference ECU. |
| REQ-011 | A task activation request shall be visible to the scheduler within one tick. |
| REQ-012 | Watchdog checkpoint evaluation shall complete within 200 microseconds. |
| REQ-013 | Fault notification to the diagnostic manager shall be non-blocking for the scheduler. |

## Safety Requirements

| ID | Requirement | Rationale |
| --- | --- | --- |
| SAF-001 | The RTOS shall transition to a controlled safe state when a safety-critical task repeatedly misses its deadline. | Prevents continued unsafe actuation under timing fault. |
| SAF-002 | The health monitor shall refresh the external watchdog only after all configured safety checkpoints are observed. | Avoids masking stuck or runaway tasks. |
| SAF-003 | The memory protection service shall deny writes outside a task's configured memory region. | Contains software faults inside a task partition. |
| SAF-004 | The diagnostic manager shall persist reset reason and last safety fault before requesting ECU reset. | Supports post-fault analysis and service diagnostics. |
| SAF-005 | The scheduler shall preserve deterministic execution order for tasks with equal priority by configured activation order. | Reduces timing variation during validation. |
| SAF-006 | The startup controller shall prevent normal mode entry when mandatory self-checks fail. | Avoids running safety tasks on an invalid platform. |
| SAF-007 | The kernel shall reject service calls from a task whose current mode does not permit the requested service. | Prevents unsafe API use outside configured lifecycle states. |
| SAF-008 | The health monitor shall classify faults as recoverable, degraded, or fatal before requesting a system mode change. | Keeps recovery policy explicit and reviewable. |
| SAF-009 | The watchdog manager shall withhold refresh when the health summary is stale. | Detects health monitor failure or communication loss. |
| SAF-010 | The RTOS shall record a bounded fault snapshot before entering reset pending mode. | Preserves evidence without unbounded fault-time work. |

## Kernel Requirements

| ID | Requirement |
| --- | --- |
| KER-001 | The kernel core shall own boot sequencing, critical sections, task dispatch, and system mode transitions. |
| KER-002 | The scheduler shall maintain ready, blocked, suspended, and faulted task states. |
| KER-003 | The scheduler shall account each periodic task against a configured deadline budget. |
| KER-004 | The scheduler shall expose deadline misses to the health monitor without performing diagnostic storage directly. |
| KER-005 | The IPC manager shall reject queue sends that exceed configured capacity. |
| KER-006 | The IPC manager shall wake tasks deterministically by priority and activation order. |
| KER-007 | The time service shall provide monotonic tick and elapsed-time queries to kernel services. |
| KER-008 | The configuration manager shall validate task, memory, checkpoint, and driver tables before the scheduler starts. |

## Platform Requirements

| ID | Requirement |
| --- | --- |
| PLT-001 | The timer driver shall provide the scheduler tick source. |
| PLT-002 | The interrupt controller adapter shall support bounded critical-section entry and exit. |
| PLT-003 | The MPU driver shall program task regions before a safety-critical task is dispatched. |
| PLT-004 | The watchdog driver shall expose refresh and reset-window status through the platform abstraction. |
| PLT-005 | The reset controller shall support software reset requests issued by the watchdog manager or kernel core. |
| PLT-006 | The nonvolatile storage driver shall provide bounded writes for reset reason and fault snapshot records. |

## Application API Requirements

| ID | Requirement |
| --- | --- |
| API-001 | The Safety Application API shall expose task activation, checkpoint, queue, event flag, and time query services. |
| API-002 | The Safety Application API shall validate task identity and caller permissions before forwarding requests. |
| API-003 | The Safety Application API shall return explicit status codes for rejected or degraded service calls. |
| API-004 | The Safety Application API shall prevent direct application access to platform drivers. |

## Traceability

| Requirement | Architecture Element | Detailed Design Flow | Validation Scenario |
| --- | --- | --- | --- |
| SAF-001 | ARC-HealthMonitor, ARC-Scheduler, ARC-Kernel | DD-FaultContainment | VAL-004 |
| SAF-002 | ARC-WatchdogManager, ARC-HealthMonitor | DD-WatchdogRecovery | VAL-003 |
| SAF-003 | ARC-MemoryProtection, ARC-Platform | DD-Startup, DD-PeriodicScheduling | VAL-005 |
| SAF-004 | ARC-DiagnosticManager, ARC-Platform | DD-FaultContainment | VAL-004 |
| SAF-005 | ARC-Scheduler | DD-PeriodicScheduling | VAL-002 |
| SAF-006 | ARC-StartupController, ARC-ConfigManager | DD-Startup | VAL-001 |
| SAF-007 | ARC-AppAPI, ARC-Kernel | DD-PeriodicScheduling | VAL-002 |
| SAF-008 | ARC-HealthMonitor, ARC-ModeManager | DD-FaultContainment | VAL-004 |
| SAF-009 | ARC-WatchdogManager, ARC-HealthMonitor | DD-WatchdogRecovery | VAL-003 |
| SAF-010 | ARC-DiagnosticManager, ARC-ResetManager | DD-FaultContainment | VAL-004 |
