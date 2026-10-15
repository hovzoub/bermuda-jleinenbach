## Unreleased

- **Breaking:** Area, floor and distance sensors no longer expose `last_good_area_age_s`, `last_good_distance_age_s` and `area_retention_seconds_remaining`, and the scanner online binary sensor no longer exposes `last_seen_age_seconds`. These values changed on every coordinator cycle and forced a `state_changed` event plus a recorder row per entity per second, even though they were excluded from recording. The flags `area_is_stale`, `area_retained` and `area_source` remain. The underlying monotonic timestamps (`area_state_stamp`, `area_distance_stamp`, `last_seen`) remain available via `bermuda.dump_devices` and the integration diagnostics (subject to the dump size limit).
- Compute the active scanner count once per update cycle instead of once per stale device.
- Add configurable FMDN modes and EID parsing, improving manual selection and avoiding duplicate devices through canonical address normalization.
- Harden FMDN EID candidate extraction and deduplicate shared tracker identities to prevent ghost devices and capture variable-length EIDs.
- Align MAC normalization with Home Assistant formatting, separate pseudo-identifier handling, and stabilize FMDN metadevice keys to avoid address collisions.
