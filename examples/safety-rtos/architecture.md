# Architectural Design

## Overview

SafetyLite is organized as a small deterministic kernel with separately
allocated safety, platform, diagnostics, and application integration services.
The kernel owns scheduling, system mode, and critical execution rules. Safety
services observe the kernel and decide whether the ECU may continue normal
operation. Platform services isolate hardware-specific behavior behind bounded
driver facades.

## Architecture Elements

| ID | Element | Responsibility |
| --- | --- | --- |
| ARC-Kernel | Kernel Core | Owns boot sequencing, service-call validation, critical sections, dispatch handoff, and system mode coordination. |
| ARC-StartupController | Startup Controller | Runs initialization sequencing, self-check admission, and startup checkpoint publication. |
| ARC-ConfigManager | Configuration Manager | Validates task, memory, checkpoint, driver, and timing configuration before normal mode. |
| ARC-ModeManager | Mode Manager | Maintains initialization, normal, degraded, safe state, and reset pending modes. |
| ARC-Scheduler | Priority Scheduler | Selects ready tasks, processes ticks, activates periodic tasks, and detects deadline misses. |
| ARC-TaskSupervisor | Task Supervisor | Tracks task budgets, checkpoints, fault counters, and task health status. |
| ARC-TimeService | Time Service | Provides monotonic tick and elapsed-time queries to kernel and application services. |
| ARC-IPC | IPC Manager | Provides bounded queues and event flags with deterministic wake-up order. |
| ARC-MemoryProtection | Memory Protection Service | Programs MPU regions during context switch and reports access violations. |
| ARC-HealthMonitor | Health Monitor | Aggregates checkpoints, deadline faults, access violations, and safety-state decisions. |
| ARC-WatchdogManager | Watchdog Manager | Refreshes or withholds the external watchdog based on health status and reset window. |
| ARC-DiagnosticManager | Diagnostic Manager | Stores fault records, emits diagnostic events, and supplies reset reason data. |
| ARC-ResetManager | Reset Manager | Coordinates reset pending mode, software reset requests, and final watchdog policy. |
| ARC-FaultStore | Fault Snapshot Store | Owns bounded in-memory and nonvolatile fault snapshot data. |
| ARC-Platform | Platform Abstraction | Wraps timer, interrupt, MPU, watchdog, reset, nonvolatile storage, and diagnostic drivers. |
| ARC-AppAPI | Safety Application API | Provides controlled RTOS services to application tasks. |

## Platform Drivers

| ID | Driver | Responsibility |
| --- | --- | --- |
| DRV-Timer | Timer Driver | Provides scheduler tick interrupts and timer status. |
| DRV-Interrupts | Interrupt Controller Adapter | Provides bounded critical-section entry and exit. |
| DRV-MPU | MPU Driver | Programs task memory regions and reports hardware protection status. |
| DRV-Watchdog | Watchdog Driver | Refreshes the external watchdog and reports refresh-window state. |
| DRV-Reset | Reset Controller | Performs software reset requests. |
| DRV-NVM | Nonvolatile Storage Driver | Persists bounded reset reason and fault snapshot records. |
| DRV-Diagnostics | Diagnostic Transport | Publishes diagnostic events to ECU diagnostics. |

## Architectural Principles

- Safety-critical services fail closed: absence of health evidence prevents
  watchdog refresh.
- The scheduler never performs blocking diagnostic writes.
- Hardware-specific behavior is isolated behind the platform abstraction.
- Application tasks cannot directly access platform drivers.
- Mode transitions are explicit and observable in the model.
- Configuration is validated before normal-mode scheduling starts.

## Diagram Coverage

`architecture_components.puml` captures the full RTOS component structure.
`kernel_services_components.puml` focuses on the deterministic kernel services.
`platform_services_components.puml` documents driver-facing platform
abstractions. `application_integration_components.puml` covers application task
access through the Safety Application API. `safety_services_components.puml`
focuses on health monitoring, watchdog recovery, diagnostics, and fault
containment.

Additional structure diagrams in `diagrams/importable` document class, object,
package, composite structure, deployment, profile, requirements, and behavior
views of the same system.
