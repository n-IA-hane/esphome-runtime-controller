Runtime Controller
==================

.. seo::
    :description: Deterministic state arbitration for composite ESPHome voice, media and VoIP devices.

The ``runtime_controller`` component is a reducer for ESPHome devices where
Voice Assistant, media playback, announcements, timers, mute state,
connectivity and VoIP can overlap.

Feature callbacks report facts such as ``media_playing`` or
``voip:in_call``. The controller keeps the active facts, resolves each output
policy by priority, and drives LEDs, globals or automations from the resolved
snapshot.

.. code-block:: yaml

    external_components:
      - source: github://n-IA-hane/esphome-runtime-controller@main
        components: [runtime_controller]

    runtime_controller:
      id: runtime
      profile: full_voice_voip

Configuration variables:
------------------------

- **id** (*Optional*, :ref:`config-id`): Manually specify the controller ID.
- **debug** (*Optional*, boolean): Log every processed event and activity mask.
  Defaults to ``false``.
- **profile** (*Optional*, string): ``full_voice_voip`` installs the built-in
  Voice Assistant, media, timer, mute, connectivity and VoIP model.
- **observe.voip_stack** (*Optional*, :ref:`config-id`): VoIP Stack instance to
  observe when using the built-in profile.
- **activities** (*Optional*, mapping): Named facts with priority, initial
  state and policy values.
- **events** (*Optional*, mapping): Named inputs with ``activate``,
  ``deactivate``, ``action``, ordered ``cases`` and optional post-reducer
  ``then`` automation.
- **actions** (*Optional*, mapping): Top-level named one-shot automations.
- **policies** (*Optional*, mapping): Output channels, integer globals,
  per-value automations and optional ``on_change`` triggers.
- **derived_activities** (*Optional*, list): Facts computed from other active
  facts.
- **groups** (*Optional*, mapping): Mutually exclusive activity groups.
- **outputs.led** (*Optional*): Built-in LED renderer.
- **output_script** (*Optional*, :ref:`config-id`): Script executed after each
  committed snapshot.
- **state_outputs.activity_mask** / **state_outputs.sequence** (*Optional*):
  Globals receiving the active bitmask and change counter.

Event ``then``
--------------

An event-level ``then`` automation runs after the matched case/default rule has
updated activities and outputs. The automation therefore sees the resolved
state. Event ``then`` names are separate from top-level ``actions:``, and the
validator rejects name collisions.

Actions
-------

``runtime_controller.event`` Action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Delivers an event.

.. code-block:: yaml

    on_...:
      - runtime_controller.event:
          id: runtime
          event: media_playing
          reason: media_player

``runtime_controller.set_activity`` Action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sets one activity directly.

``runtime_controller.set_activities`` Action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sets several activities atomically.

``runtime_controller.request_action`` Action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs a top-level named action.

``runtime_controller.dump`` Action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Logs the active set and resolved policy table.

``runtime_controller.is_active`` Condition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns true when a named activity is active.

Limits
------

The reducer uses fixed storage and does not allocate at runtime: 32 activities,
8 policy channels, 8 policy entries per activity, 16 named actions and 64
event-driven activity updates. Events raised while dispatch is active are
queued and processed after the current commit.

See Also
--------

- :doc:`/components/voice_assistant`
- :doc:`/components/micro_wake_word`
- :apiref:`runtime_controller/runtime_controller.h`
- :ghedit:`Edit`
