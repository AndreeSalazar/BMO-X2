"""Closed x86-64 ABI micro-architecture profiles carried by SBEF v2."""

from ..diagnostics import Rejection


FEATURES = {
    'CMOV': (1, 0, 'EDX', 15),
    'CX8': (1, 0, 'EDX', 8),
    'FPU': (1, 0, 'EDX', 0),
    'FXSR': (1, 0, 'EDX', 24),
    'MMX': (1, 0, 'EDX', 23),
    'SSE': (1, 0, 'EDX', 25),
    'SSE2': (1, 0, 'EDX', 26),
    'CMPXCHG16B': (1, 0, 'ECX', 13),
    'LAHF_SAHF': (0x80000001, 0, 'ECX', 0),
    'POPCNT': (1, 0, 'ECX', 23),
    'SSE3': (1, 0, 'ECX', 0),
    'SSE4_1': (1, 0, 'ECX', 19),
    'SSE4_2': (1, 0, 'ECX', 20),
    'SSSE3': (1, 0, 'ECX', 9),
    'AVX': (1, 0, 'ECX', 28),
    'AVX2': (7, 0, 'EBX', 5),
    'BMI1': (7, 0, 'EBX', 3),
    'BMI2': (7, 0, 'EBX', 8),
    'F16C': (1, 0, 'ECX', 29),
    'FMA': (1, 0, 'ECX', 12),
    'LZCNT': (0x80000001, 0, 'ECX', 5),
    'MOVBE': (1, 0, 'ECX', 22),
    'OSXSAVE': (1, 0, 'ECX', 27),
    'AVX512F': (7, 0, 'EBX', 16),
    'AVX512BW': (7, 0, 'EBX', 30),
    'AVX512CD': (7, 0, 'EBX', 28),
    'AVX512DQ': (7, 0, 'EBX', 17),
    'AVX512VL': (7, 0, 'EBX', 31),
}

PROFILES = [
    {
        'Id': 1,
        'Name': 'x86-64-v1',
        'Features': ['CMOV', 'CX8', 'FPU', 'FXSR', 'MMX', 'OSFXSR', 'SCE', 'SSE', 'SSE2'],
        'CR4Mask': 1 << 9,
        'XCR0Mask': 0,
    },
    {
        'Id': 2,
        'Name': 'x86-64-v2',
        'Features': ['CMPXCHG16B', 'LAHF_SAHF', 'POPCNT', 'SSE3', 'SSE4_1', 'SSE4_2', 'SSSE3'],
        'CR4Mask': 0,
        'XCR0Mask': 0,
    },
    {
        'Id': 3,
        'Name': 'x86-64-v3',
        'Features': ['AVX', 'AVX2', 'BMI1', 'BMI2', 'F16C', 'FMA', 'LZCNT', 'MOVBE', 'OSXSAVE'],
        'CR4Mask': 0,
        'XCR0Mask': 0x6,
    },
    {
        'Id': 4,
        'Name': 'x86-64-v4',
        'Features': ['AVX512F', 'AVX512BW', 'AVX512CD', 'AVX512DQ', 'AVX512VL'],
        'CR4Mask': 0,
        'XCR0Mask': 0xE6,
    },
]

PROFILE_BY_NAME = {profile['Name']: profile for profile in PROFILES}
PROFILE_BY_ID = {profile['Id']: profile for profile in PROFILES}


def profile_id(name):
    """Return the stable SBEF profile id, or reject an unknown profile."""
    if name not in PROFILE_BY_NAME:
        raise Rejection('SBEF-ISA-PROFILE', 24, 'isa_profile')
    return PROFILE_BY_NAME[name]['Id']


def profile_name(identifier):
    """Return the profile name encoded in the v2 flags field."""
    profile = PROFILE_BY_ID.get(identifier)
    if profile is None:
        raise Rejection('SBEF-ISA-PROFILE', 24, 'isa_profile')
    return profile['Name']


def profile_requirements(profile):
    """Expand a profile to the cumulative CPU and enabled-state requirements."""
    if isinstance(profile, str):
        if profile not in PROFILE_BY_NAME:
            raise Rejection('SBEF-ISA-PROFILE', 24, 'isa_profile')
        index = PROFILE_BY_NAME[profile]['Id']
    else:
        if profile not in PROFILE_BY_ID:
            raise Rejection('SBEF-ISA-PROFILE', 24, 'isa_profile')
        index = profile

    features = set()
    cr4_mask = 0
    xcr0_mask = 0
    for item in PROFILES[:index]:
        features.update(item['Features'])
        cr4_mask |= item['CR4Mask']
        xcr0_mask |= item['XCR0Mask']

    cpuid = {}
    for feature in sorted(features):
        if feature == 'OSFXSR':
            continue
        if feature == 'SCE':
            leaf, subleaf, register, bit = (0x80000001, 0, 'EDX', 11)
        else:
            leaf, subleaf, register, bit = FEATURES[feature]
        key = (leaf, subleaf, register)
        cpuid.setdefault(key, []).append(feature)

    checks = []
    for (leaf, subleaf, register), names in sorted(cpuid.items()):
        mask = 0
        for feature in names:
            bit = 11 if feature == 'SCE' else FEATURES[feature][3]
            mask |= 1 << bit
        checks.append({
            'Leaf': f'0x{leaf:08X}',
            'Subleaf': subleaf,
            'Register': register,
            'Mask': f'0x{mask:08X}',
            'Features': names,
        })
    return {
        'Name': PROFILE_BY_ID[index]['Name'],
        'Features': sorted(features),
        'MinimumBasicLeaf': '0x00000007' if index >= 3 else '0x00000001',
        'MinimumExtendedLeaf': '0x80000001',
        'CPUID': checks,
        'CR4Mask': f'0x{cr4_mask:08X}',
        'XCR0Mask': f'0x{xcr0_mask:08X}',
    }
