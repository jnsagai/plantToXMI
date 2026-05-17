# Detailed Design

## DD-Startup

Startup executes in a restricted initialization mode. The kernel initializes
the platform abstraction, runs startup self-checks, configures memory regions,
loads the task table, and then admits safety tasks to the scheduler.

Failure behavior:

- A failed self-check prevents task start.
- A memory configuration failure is reported to diagnostics.
- The watchdog is not refreshed until the health monitor confirms startup
  checkpoints.

## DD-PeriodicScheduling

The timer driver raises the scheduler tick. The scheduler updates task budgets,
activates due periodic tasks, selects the highest-priority ready task, and asks
memory protection to switch MPU regions before dispatch.

Failure behavior:

- A deadline miss is reported to the health monitor.
- Scheduler tick processing must remain bounded and non-blocking.

## DD-WatchdogRecovery

The health monitor receives task checkpoints. The watchdog manager asks for the
health summary before each refresh window closes. If checkpoints are missing,
the watchdog manager withholds refresh and the diagnostic manager stores the
last observed fault.

## DD-FaultContainment

When a task violates timing or memory policy, the kernel raises a safety fault.
The health monitor classifies severity, the diagnostic manager persists a fault
record, and the kernel transitions affected tasks or the whole ECU into a safe
state.

## Additional UML Views

The importable diagram set includes use case, activity, state machine,
communication, interaction overview, and timing views in addition to the
sequence flows above.
