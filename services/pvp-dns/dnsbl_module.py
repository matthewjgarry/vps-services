import sqlite3

DB = "/var/lib/unbound/pvp-dnsbl.sqlite"

_conn = None


def init_standard(id, env):
    global _conn

    _conn = sqlite3.connect(
        f"file:{DB}?mode=ro",
        uri=True,
        check_same_thread=False,
    )

    log_info("pvp-dnsbl: SQLite blocklist opened")
    return True


def deinit(id):
    global _conn

    if _conn is not None:
        _conn.close()
        _conn = None

    return True


def inform_super(id, qstate, superqstate, qdata):
    return True


def blocked(domain):
    domain = domain.rstrip(".").lower()

    labels = domain.split(".")
    candidates = [
        ".".join(labels[i:])
        for i in range(len(labels))
    ]

    placeholders = ",".join("?" for _ in candidates)

    rows = _conn.execute(
        f"""
        SELECT domain, policy, wildcard
        FROM domains
        WHERE domain IN ({placeholders})
        """,
        candidates,
    ).fetchall()

    if not rows:
        return False

    by_domain = {}

    for candidate, policy, wildcard in rows:
        by_domain.setdefault(candidate, []).append(
            (policy, wildcard)
        )

    # Preserve Midway policy order.
    for policy in (1, 2, 3):
        allowed = _conn.execute(
            """
            SELECT 1
            FROM allowlist
            WHERE policy = ? AND domain = ?
            """,
            (policy, domain),
        ).fetchone()

        if allowed:
            continue

        for index, candidate in enumerate(candidates):
            for row_policy, wildcard in by_domain.get(candidate, []):
                if row_policy != policy:
                    continue

                # Exact match.
                if index == 0:
                    return True

                # Parent domains only block children when that feed
                # supplied the entry as a wildcard.
                if wildcard:
                    return True

    return False


def set_block_answer(qstate):
    domain = qstate.qinfo.qname_str.rstrip(".")
    qtype = qstate.qinfo.qtype

    # Match Midway's nxdomain=0 behavior:
    # NOERROR with 0.0.0.0 for A/CNAME queries.
    #
    # OPNsense itself currently leaves AAAA without a synthetic
    # destination record in this mode.
    msg = DNSMessage(
        domain,
        RR_TYPE_A,
        RR_CLASS_IN,
        PKT_QR | PKT_RA | PKT_AA,
    )

    if qtype == RR_TYPE_A or qtype == RR_TYPE_CNAME:
        msg.answer.append(
            f"{domain} 72000 IN A 0.0.0.0"
        )

    if not msg.set_return_msg(qstate):
        log_err(
            f"pvp-dnsbl: unable to construct blocked response for {domain}"
        )
        return False

    qstate.return_msg.rep.security = sec_status_unchecked
    qstate.return_rcode = RCODE_NOERROR

    return True


def operate(id, event, qstate, qdata):
    if event == MODULE_EVENT_NEW:
        domain = qstate.qinfo.qname_str

        try:
            is_blocked = blocked(domain)
        except Exception as exc:
            log_err(
                f"pvp-dnsbl: lookup failed for {domain}: {exc}"
            )
            qstate.ext_state[id] = MODULE_ERROR
            return True

        if is_blocked:
            if not set_block_answer(qstate):
                qstate.ext_state[id] = MODULE_ERROR
                return True

            qstate.ext_state[id] = MODULE_FINISHED
            return True

        # Not blocked: let iterator/Quad9 resolve it.
        qstate.ext_state[id] = MODULE_WAIT_MODULE
        return True

    if event == MODULE_EVENT_MODDONE:
        # Iterator has completed normally.
        qstate.ext_state[id] = MODULE_FINISHED
        return True

    if event == MODULE_EVENT_PASS:
        # Query was passed back through the module chain.
        qstate.ext_state[id] = MODULE_WAIT_MODULE
        return True

    log_err(
        f"pvp-dnsbl: unexpected event {event} for "
        f"{qstate.qinfo.qname_str}"
    )
    qstate.ext_state[id] = MODULE_ERROR
    return True
