"""Compare the guest's shutdown transitions with live QEMU registers."""
import struct


def verify_storage_quiesce(memory, context, rows, actual, required):
    raw = memory(context+0xb58, 32, 'storage-quiesce-result')
    if not required:
        if any(raw):
            raise ValueError('Storage shutdown was attempted without the lab IOMMU')
        return dict(StorageQuiesceSkippedVerified=True)

    results = list(struct.iter_unpack('<HHIII', raw))
    proof = {}
    for row, result in zip(rows, results):
        rid, _, kind, bar, length, identity, before, captured, a, b, engines, pending = row
        status, after, final0, final1, ack = result
        live = actual.get(rid)
        if status!=3 or not before&4 or after!=before&~4:
            raise ValueError(f'Storage {rid:04X} failed to relinquish DMA: {result}, before={before:04X}')
        if not live or live[:6]!=(kind,bar,length,identity,after,captured):
            raise ValueError(f'Storage {rid:04X} PCI snapshot or final state differs: {live}')
        if kind==0x010601:
            if not engines or pending or live[6:]!=(a,b,0,0) or (final0,final1,ack)!=(0,0,0):
                raise ValueError(f'AHCI engine stop did not match hardware: engines={engines:#x}, live={live}')
            proof['AHCI']=dict(Requester=f'{rid:04X}',CommandBefore=before,CommandAfter=after,
                               EnginesBefore=engines,EnginesAfter=live[8],CommandsPendingAfter=live[9])
        elif kind==0x010802:
            if (not a&1 or b&0x4f!=1 or ack&0x4e!=8 or final0&0xc001 or final1&0x43
                    or live[6:8]!=(final0,final1)):
                raise ValueError(f'NVMe shutdown or disabled state differs: {result}, live={live}')
            proof['NVMe']=dict(Requester=f'{rid:04X}',CommandBefore=before,CommandAfter=after,
                               ConfigurationBefore=a,StatusBefore=b,ShutdownAcknowledgement=ack,
                               ConfigurationAfter=final0,StatusAfter=final1)
    if proof.keys()!={'AHCI','NVMe'}:
        raise ValueError('The shutdown probe must verify both controllers')
    return dict(StorageQuiesceVerified=True,StorageQuiesce=proof)
