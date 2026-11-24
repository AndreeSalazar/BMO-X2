"""Read the frozen UEFI bridge from its checked HEX fragments."""
import re


def assemble(paths):
    output = bytearray()
    for path in paths:
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            for token in line.split(';', 1)[0].split():
                if re.fullmatch(r'[@=][0-9A-Fa-f]+', token):
                    target = int(token[1:], 16)
                    if target > 1048576 or target < len(output) or (token[0] == '=' and target != len(output)):
                        raise ValueError('BRIDGE-OFFSET')
                    output.extend(bytes(target - len(output)))
                elif re.fullmatch('[0-9A-Fa-f]{2}', token):
                    output.append(int(token, 16))
                else:
                    raise ValueError(f'BRIDGE-TOKEN: {token}')
    if len(output) != 12288 or output[:2] != b'MZ' or output[0x40:0x44] != b'PE\0\0':
        raise ValueError('BRIDGE-IMAGE')
    return bytes(output)
