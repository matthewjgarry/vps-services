# Beszel first-rollout monitoring policy

## Purpose

This is the deliberately small first production monitoring set for Wormlogic.
Beszel owns telemetry, history, and selected native metric thresholds. The
Wormlogic Operational Event Ingress owns incident lifecycle and Discord routing.
Beszel native Discord notifications remain disabled. `external-dns-health` remains
the authority for its DNS and external-path checks.

No Beszel observer or heartbeat/dead-man service is defined here. Total
Heighliner loss remains a known monitoring-plane blind spot.

## Alert semantics

- `error`: user-relevant loss of a critical service, storage danger, or host loss.
- `warning`: sustained pressure or loss of a redundant/non-primary component.
- Short CPU/load spikes and intentional GPU utilization are dashboard history,
  not pages.
- Every alert needs an entry debounce and a correlated recovery. Healthy polls do
  not emit events.

## Arrakis

| Condition | Layer | Initial owner | Initial policy |
| --- | --- | --- | --- |
| Host unreachable | host | Beszel status | Error after sustained down state; suppress child container alerts during a host incident. |
| Home Assistant functional availability | functional | Direct future probe | Error after 2 of 3 failures. A running container is insufficient. |
| Mosquitto and Zigbee2MQTT | service/functional | Beszel container data plus direct future probe | Error when either is stopped/unhealthy and the relevant transaction fails. |
| Matter Server | service | Beszel container data | Warning unless Home Assistant reports material Matter impairment. |
| Caddy / selected published services | service/functional | Beszel + direct route probe | Alert only for explicitly selected useful routes. |
| Root capacity | resource | Beszel native threshold | Warning at 85% sustained; error at 95%. |
| SMART | resource | Not enabled yet | `smartctl` was absent. Installation and permission validation are a prerequisite, not an alert. |
| ESPHome | service | Explicit exclusion | Known intentionally stopped USB-dependent service; no alert. |
| DNS | functional/path | external-dns-health | Do not duplicate. |

## IX

| Condition | Layer | Initial owner | Initial policy |
| --- | --- | --- | --- |
| Host unreachable | host | Beszel status | Error after sustained down state. |
| Hermes availability | functional | Direct future readiness probe | Error after 2 of 3 failures. Probe the supported readiness/status path, not `/`. |
| Ollama availability | service/functional | Beszel plus direct future API probe | Warning by default; error only where Hermes depends on local inference. |
| GPU device/driver disappearance | resource/service | Beszel GPU metrics | Error. |
| GPU thermal condition | resource | Beszel GPU metrics | Warning above 85°C for 10 minutes; error above 90°C for 5 minutes. |
| GPU utilization/VRAM use | telemetry | Beszel GPU history | Dashboard only unless correlated with API failure, OOM, or thermal pressure. |
| Root and `/srv/ix` capacity | resource | Beszel native threshold | Warning at 80%; error at 90%; use trend evidence for projected exhaustion. |
| NVMe SMART | resource | Beszel SMART plus native smartmontools | Current Beszel state is UNKNOWN. First repair least-privilege device capability/access, then alert any failed/pre-fail state as error. |

## Midway

Midway remains the authoritative OPNsense control plane. Beszel may retain host
CPU, memory, disk, and temperature history only. Do not add Docker, SMART, or
administrative privileges to its agent.

| Condition | Owner | Initial policy |
| --- | --- | --- |
| WAN/LAN interface and gateway state | OPNsense native health / existing HA integration | Error for sustained WAN/LAN loss. |
| Heighliner WireGuard path | OPNsense native status | Error for stale tunnel/handshake beyond chosen peer tolerance. |
| Proton gateway | OPNsense native status | Warning unless an explicitly required traffic path depends on it. |
| DHCP / resolver / firewall health | OPNsense native configuration | Determine configured checks before enabling policy. |
| DNS functional health | external-dns-health | Do not duplicate. |
| Host resource telemetry | Beszel / HA | Dashboard and sustained-pressure evidence only. |

`monit` is installed but was not demonstrably running during the 2026-08-27
inspection. Do not design an alert policy around it until its intended
configuration and runtime authority are verified from OPNsense itself.

## Caladan / server03

Caladan is currently unreachable and absent from Beszel. The following is planned,
not live policy:

- host reachability;
- pool/array degradation;
- SMART failure and failed self-test;
- capacity exhaustion;
- mounted filesystem/share availability from an intended client vantage;
- backup completion and restore-verification age;
- selected media service availability only after those services are deployed.

Storage failures and failed backup verification are error-level conditions. Do not
fabricate thresholds, service names, or storage topology before Caladan is
observable.
