#!/usr/bin/env bash
set -euo pipefail

UPLINK="${PVP_UPLINK_IFACE:-eth0}"
PVP_TABLE="${PVP_ROUTE_TABLE:-pvp}"
RULE_PRIORITY="${PVP_UNBOUND_RULE_PRIORITY:-110}"
ROUTE_PROBE="${PVP_ROUTE_PROBE_IP:-9.9.9.9}"

for command_name in ethtool ip id awk grep; do
    command -v "$command_name" >/dev/null 2>&1 || {
        echo "✗ Required command not found: $command_name"
        exit 1
    }
done

if ! ip link show dev "$UPLINK" >/dev/null 2>&1; then
    echo "✗ PVP uplink does not exist: $UPLINK"
    exit 1
fi

if ! ip link show dev wg-proton >/dev/null 2>&1; then
    echo "✗ Proton WireGuard interface is not present: wg-proton"
    exit 1
fi

echo "• Disabling GRO on $UPLINK..."
ethtool -K "$UPLINK" gro off

gro_state="$(
    ethtool -k "$UPLINK" |
        awk -F': ' '$1 == "generic-receive-offload" { print $2; exit }'
)"

if [[ "$gro_state" != "off" ]]; then
    echo "✗ GRO is still enabled on $UPLINK"
    exit 1
fi

if ! ip route show table "$PVP_TABLE" |
    grep -Eq '^default dev wg-proton([[:space:]]|$)'; then
    echo "✗ PVP route table has no default route through wg-proton"
    ip route show table "$PVP_TABLE" || true
    exit 1
fi

unbound_uid="$(id -u unbound)"

# Priority 110 is owned by PVP DNS. Remove stale/duplicate copies first.
while ip -4 rule del priority "$RULE_PRIORITY" 2>/dev/null; do
    :
done

ip -4 rule add \
    priority "$RULE_PRIORITY" \
    uidrange "${unbound_uid}-${unbound_uid}" \
    lookup "$PVP_TABLE"

route="$(
    ip -4 route get "$ROUTE_PROBE" uid "$unbound_uid"
)"

if [[ "$route" != *"dev wg-proton"* ||
      "$route" != *"table $PVP_TABLE"* ]]; then
    echo "✗ Unbound traffic is not selecting the Proton route"
    echo "  $route"
    exit 1
fi

echo "✓ PVP DNS host state ready"
echo "  GRO:          off on $UPLINK"
echo "  Unbound UID:  $unbound_uid"
echo "  Policy rule:  priority $RULE_PRIORITY -> table $PVP_TABLE"
