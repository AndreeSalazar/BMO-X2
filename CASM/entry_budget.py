"""Binary size contract for the first BMO-X2 entry packet."""

HEADER_BYTES = 24
PACKET_LIMIT = 512


def entry_budget(body_bytes, packet_bytes):
    if not 0 < body_bytes or packet_bytes != body_bytes + HEADER_BYTES or packet_bytes >= PACKET_LIMIT:
        raise ValueError(f'ENTRY-BUDGET: {body_bytes} body bytes, {packet_bytes} packet bytes, required < {PACKET_LIMIT}')
    return dict(HeaderBytes=HEADER_BYTES, LimitExclusive=PACKET_LIMIT,
                RemainingBytes=PACKET_LIMIT - 1 - packet_bytes)
