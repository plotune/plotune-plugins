---
name: plotune-controller-simulations
description: Use when building a closed-loop controller container (CAN or DDS) that joins a simulator/plant network and drives it through a planned profile — e.g. a drive-cycle pedal controller for a vehicle dynamics sim — then deploying it via the Nexus and recording the run as evidence.
---

# Plotune Controller Simulations

A *controller simulation* is a container that joins a bench network, reads a plant's feedback
signal, and actively commands the plant through a planned profile (a drive cycle, a ramp, a
hold). It is the active counterpart to a passive simulator: the simulator publishes state, the
controller closes the loop. Examples in this repo: `simulations/powertrain_controller_simulation`
(CAN, NEDC/WLTP pedal control) and `simulations/dds_drive_cycle_controller` (DDS, drive-cycle
pedal control over `/vehicle/*`).

This skill is the systematic starting point for building one and using it as the driver for a
Nexus test sequence. The control law and structure are transport-agnostic; only the wiring
(CAN frames vs DDS topics) differs.

## Step 1 — Characterise the plant before writing any control code

You cannot tune a controller you don't understand. Establish:

- **Feedback signal**: what the plant publishes and its units (e.g. DDS `/vehicle/speed` as
  `std_msgs/Float32` in m/s; or a CAN `VehicleMotionStatus.VehicleSpeed` in km/h).
- **Command signals**: what the plant subscribes to and their ranges (e.g. throttle/brake as
  `0..1` fractions; or pedal percentages in a DBC message).
- **Plant dynamics and limits**: write down the steady-state relation. For the DDS sim the model
  is `accel = 3.2·throttle − 7.5·brake − 0.018·v²`, so the steady-state throttle for speed `v`
  is `0.018·v²/3.2 = 0.005625·v²`, and drive force saturates against drag near **~48 km/h**.
  Knowing this gives you (a) an analytic feedforward and (b) a realistic speed ceiling so your
  scenarios stay achievable.

Read the simulator's `README.md` / source. Don't guess the topic names or units.

## Step 2 — Lay out the package (mirror the existing controllers)

```
<controller>/
  scenario.py     # DriveCyclePoint + DriveCycleScenario(JSON loader, linear interpolation)
  config.py       # frozen dataclass: gains, limits, topic/interface names, refresh period
  controller.py   # the control law — transport-agnostic (see Step 3)
  main.py         # arg parsing, transport wiring, --self-test, signal handling
  scenarios/*.json
  Dockerfile, <run>.sh, pyproject.toml, README.md, tests/
```

Keep `controller.py` free of any CAN/DDS imports. Inject the I/O as callables:

```python
class DriveCycleController:
    def __init__(self, config, scenario, *, speed_source, throttle_sink, brake_sink): ...
    def run(self, stop_event) -> RunStats: ...
```

`main.py` wires `speed_source`/`throttle_sink`/`brake_sink` to DDS readers/writers (or a CAN bus);
the self-test and unit tests wire them to an in-process plant. This is what makes the controller
testable without hardware or a network.

## Step 3 — The control law: feedforward + PID, with a brake split

For each refresh tick compute `error = target − actual` and:

- **Feedforward** the known steady-state command (e.g. `drag_ff_gain·v²` for throttle). This does
  most of the work; the PID only trims the residual.
- **Accelerate** when `error ≥ −brake_threshold`: `ff + Kp·e + Ki·∫e + Kd·max(de/dt, 0)`, clamped
  to `max_throttle`.
- **Brake** when `error < −brake_threshold`: a PD law on `−error`, clamped to `max_brake`.
- **Slew-limit** both pedals (`pedal_slew_rate·dt`) and keep throttle and brake mutually exclusive.
- Decay/clamp the integral near zero error to avoid windup at standstill.

Pull the target from the scenario by interpolation: `scenario.target_speed_at(elapsed·time_scale)`.
A `time_scale > 1` runs the cycle faster than real time — keep your in-process plant integrating
`dt·time_scale` so physics and scenario stay consistent.

## Step 4 — Self-test against an in-process plant

Add `--self-test` that runs the controller against a Python mirror of the plant dynamics (no
transport) and asserts the vehicle both accelerates and brakes and reaches a sane peak. This is
the fast smoke test for the control law and belongs in CI. Mirror it in `tests/`.

## Step 5 — Containerise

- Pin the exact middleware the Nexus uses (e.g. `cyclonedds==11.0.1`) so type/topic discovery
  matches.
- Use `--network=host` for cross-machine DDS.
- For DDS, an entrypoint script should bind `CYCLONEDDS_URI` to the default-route interface when
  unset, and let a pre-set `CYCLONEDDS_URI` override (interface + peers). See
  [[plotune-dds-workflows]].

## Step 6 — Deploy via the Nexus (not on the workstation)

The expected method is to deploy the controller as a managed container on the Nexus while the
simulator runs on the bench host. Build the OCI tar, stage it, and start it — full detail in
[[plotune-gateways-containers]]:

```
podman build -t <controller> . && podman save --format oci-archive -o <controller>.tar localhost/<controller>:latest
prepare_put_artifact(file_name="<controller>.tar", size=..., sha256=..., folder_name="containers")  # MUST be 'containers'
# PUT the bytes to the returned upload_url (pieces with Content-Range if the file is over the per-request limit), then:
put_artifact(transfer_id="...")  # → artifact_id
start_container(name="<controller>", artifact_id="...", network_mode="host",
                env={"CYCLONEDDS_URI": "<...bind bench iface + <Peer> publisher IP...>"},
                args=["--scenario", "nexus_demo", "--domain-id", "0"], max_runtime_seconds=70)
```

Always `stop_container` when done.

## Step 7 — Record the run as evidence

Record the feedback and command signals into one artifact (see [[plotune-dds-workflows]] /
[[plotune-can-workflows]]), then verify the profile:

```
join_dds_session(name="controller-evidence", domain_id=0, cyclonedds_uri="<...>")
→ session_id: "<hex>"

record_dds_topics(topics=[{"topic_name":"/vehicle/speed","type_name":"std_msgs/msg/Float32"},
                          {"topic_name":"/vehicle/throttle_request","type_name":"std_msgs/msg/Float32"},
                          {"topic_name":"/vehicle/brake_request","type_name":"std_msgs/msg/Float32"}],
                  duration_seconds=..., domain_id=0, session_id="<hex>")
```

For a controller-driven cycle, **start the recorder first and give DDS peer-discovery several
seconds to settle before launching the controller** — otherwise the remote feedback topic is
discovered late and the leading phase is missed. The leading idle in the file (plant free-running
before the controller engages) is a harness artifact; re-zero analysis to controller engagement.
When the job reaches a terminal state, leave the DDS session explicitly. A recording job can be
cancelled and still yield a partial readable artifact; record that terminal status in the evidence.

## Step 8 — Drive a test sequence with it

Once the controller reliably drives the plant, fold it into a managed `run_test_sequence`: start
the controller container as a step, record the topics, wait on conditions, and gather evidence
atomically. See [[plotune-test-sequences-reporting]].

## Cross-machine gotchas (hard-won)

- Recorder/snapshot `type_name` is the **ROS form** `std_msgs/msg/Float32`, not the IDL
  `std_msgs::msg::dds_::Float32_`. Topic names are ROS form; the tool applies the `rt/` prefix.
- Peer-unicast discovery takes several seconds — a 2 s snapshot returns nothing; use ≥10 s.
- The publisher host's firewall must allow inbound LAN UDP; a default-drop INPUT policy silently
  blocks DDS (e.g. `sudo iptables -I INPUT -p udp -s 192.168.1.0/24 -j ACCEPT`). See
  [[plotune-dds-workflows]].
- Keep scenario speeds within the plant's achievable envelope (drive force saturates against drag).
