# Runtime controller regression tests

`tests/test_runtime_controller_core_runtime.py` compiles the repository's current
`runtime_controller.cpp` and `runtime_controller_state.cpp`, with and without the
optional VoIP observer, then executes independent scenarios. Run it with:

```sh
python -m pytest tests/test_runtime_controller_core_runtime.py -q
```

The C++17 compiler and Python/pytest are the only requirements for this test.
There is no copied controller or independent reducer implementation in the test.
The adapters under `stubs` replace ESPHome automation callbacks, plain globals,
component scheduling, allocation, logging, LED calls, output scripts and a VoIP
state callback. They do not emulate the firmware scheduler, SIP, audio or hardware.

The tested transaction boundary includes policy publication and effects, the
output script, queuing the named action, and `event.then`. A nested input runs
only after that boundary. Named actions remain deferred until `loop()` and keep
their FIFO/deduplication contract; asynchronous automation completion is outside
the reducer transaction.

The queues stay bounded at sixteen entries. New events produced while draining
a batch remain pending for a later turn. A full event queue rejects additional
events with a log; a dropped VoIP observation is reconciled to the latest live
state once the queued observations have drained. No guarantee is made that
intermediate transitions survive queue overflow.
