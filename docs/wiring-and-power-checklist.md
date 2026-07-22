# Wiring and Power Checklist Template

This is a pre-power template for future real hardware. It does not claim that any wiring has been completed.

## Before Applying Power

| Check | Required Result | Status |
| --- | --- | --- |
| Voltage check | All rails match selected component requirements; unknown values are `待选型确认` | Pending |
| Polarity check | Battery, regulator, actuator, and charging connectors are marked and verified | Pending |
| Common ground check | Controller, sensors, and actuator supplies share ground only where intended | Pending |
| Short/resistance check | No short between power and ground before power is applied | Pending |
| Pin conflict check | Servo, OLED, sensor, and communication pins do not conflict | Pending |
| Fuse check | Fuse rating and placement are `待选型确认` | Pending |
| Emergency switch check | Physical cutoff is reachable and verified before actuator power | Pending |
| USB separation | USB power is not forced to supply actuator current | Pending |
| Servo independent supply | Servo rail current capacity and voltage are `待选型确认` | Pending |
| Motor driver isolation | Motor driver power and logic isolation are `待选型确认` | Pending |
| Maximum current | Worst-case current is calculated after actuator selection | Pending |

## First Power Sequence

1. Power only the controller, with no servos or motors connected.
2. Verify no heat, smoke, repeated reset, or unexpected output.
3. If a human operator explicitly chooses to inspect logs, open serial manually; Codex automation must not open serial.
4. Connect one low-risk sensor at a time.
5. Connect one actuator at a time with current limiting where possible.
6. Test only small-angle servo motion after firmware limits and emergency stop behavior are confirmed.
7. Add remaining actuators gradually.
8. Do not place the robot on the ground for movement until bench and lifted tests pass.

## Stop Conditions

- Unexpected actuator movement.
- Brownout or repeated resets.
- Heating, smell, smoke, spark, or abnormal noise.
- Voltage outside selected component limits.
- Incorrect polarity or uncertain connector orientation.
- Emergency stop or disconnect path unavailable.

## Unknown Electrical Parameters

The following remain `待选型确认` until parts are selected and measured:

- Servo voltage and stall current.
- Motor voltage, current, and driver protection.
- Battery chemistry, voltage range, and protection board behavior.
- Regulator current, thermal behavior, and dropout.
- Charging module current, termination, and fault behavior.
- Charging dock polarity, voltage, and contact resistance.
