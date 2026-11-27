"""Validate and optimize SPIR-V for the bounded VERRANO triangle profile."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


TARGET = 'vulkan1.3'
MAX_BYTES = 16 * 1024
STAGES = {'vertex': 'Vertex', 'fragment': 'Fragment', 'textured-fragment': 'Fragment'}
OPERATIONS = frozenset("""
    OpAccessChain OpCapability OpCompositeConstruct OpCompositeExtract
    OpConstant OpConstantComposite OpDecorate OpDot OpEntryPoint OpExecutionMode
    OpExtInst OpExtInstImport OpFAdd OpFMul OpFSub OpFunction OpFunctionEnd
    OpLabel OpLoad OpMemberDecorate OpMemberName OpMemoryModel OpName OpReturn
    OpSource OpSourceExtension OpStore OpTypeArray OpTypeFloat OpTypeFunction
    OpTypeInt OpTypePointer OpTypeStruct OpTypeVector OpTypeVoid OpVariable
    OpVectorShuffle OpVectorTimesScalar
""".split())
TEXTURE_OPERATIONS = {'OpTypeImage', 'OpTypeSampledImage', 'OpImageSampleImplicitLod'}
INSTRUCTION = re.compile(r'^\s*(?:(%\d+)\s*=\s*)?(Op\w+)\b(.*)$')


def run_tool(sdk, name, *arguments):
    result = subprocess.run([sdk / 'Bin' / f'{name}.exe', *arguments],
                            capture_output=True, encoding='utf-8', errors='replace',
                            timeout=30, check=False)
    if result.returncode:
        raise ValueError(f'{name}: {result.stderr.strip() or result.stdout.strip()}')
    return result.stdout


def validate(sdk, module, stage):
    run_tool(sdk, 'spirv-val', '--target-env', TARGET, module)
    assembly = run_tool(sdk, 'spirv-dis', '--no-color', '--raw-id', module)
    instructions = [match.groups() for line in assembly.splitlines()
                    if (match := INSTRUCTION.match(line))]
    textured = stage == 'textured-fragment'
    allowed = OPERATIONS | TEXTURE_OPERATIONS if textured else OPERATIONS
    entries = []
    bindings = []
    samplers = []
    for result, op, raw in instructions:
        operands = raw.split()
        if op not in allowed:
            raise ValueError(f'VERRANO-OP: {op}')
        if op == 'OpCapability' and operands != ['Shader']:
            raise ValueError(f'VERRANO-CAPABILITY: {raw.strip()}')
        if op == 'OpMemoryModel' and operands != ['Logical', 'GLSL450']:
            raise ValueError(f'VERRANO-MEMORY-MODEL: {raw.strip()}')
        if op == 'OpExtInstImport' and operands != ['"GLSL.std.450"']:
            raise ValueError(f'VERRANO-EXT-SET: {raw.strip()}')
        if op == 'OpExtInst' and operands[2] not in {'Sin', 'Cos', 'Normalize', 'Cross'}:
            raise ValueError(f'VERRANO-EXT-OP: {operands[2]}')
        if op == 'OpVariable':
            storage = operands[1]
            if textured and storage == 'UniformConstant':
                samplers.append(result)
            elif storage not in {'Input', 'Output', 'Function', 'PushConstant'}:
                raise ValueError(f'VERRANO-STORAGE: {storage}')
        if op == 'OpDecorate' and operands[1] in {'Binding', 'DescriptorSet'}:
            bindings.append(tuple(operands))
        if op == 'OpTypeImage' and operands[1:] != ['2D', '0', '0', '0', '1', 'Unknown']:
            raise ValueError('VERRANO-TEXTURE: expected a sampled 2D image')
        if op == 'OpImageSampleImplicitLod' and len(operands) != 3:
            raise ValueError('VERRANO-TEXTURE: optional sample operands are outside this profile')
        if op == 'OpEntryPoint':
            entries.append((operands[0], operands[2]))
    if entries != [(STAGES[stage], '"main"')]:
        raise ValueError(f'VERRANO-ENTRY: expected one {stage} entry named main')
    if textured:
        if len(samplers) != 1 or set(bindings) != {
            (samplers[0], 'Binding', '0'), (samplers[0], 'DescriptorSet', '0'),
        }:
            raise ValueError('VERRANO-TEXTURE: expected exactly set 0 binding 0')
        if sum(op == 'OpImageSampleImplicitLod' for _, op, _ in instructions) != 1:
            raise ValueError('VERRANO-TEXTURE: expected exactly one sample')
    elif bindings:
        raise ValueError('VERRANO-TEXTURE: this stage accepts no descriptor bindings')


def prepare(sdk, source, stage, output):
    if source.resolve() == output.resolve():
        raise ValueError('VERRANO-OUTPUT: input and output must differ')
    with source.open('rb') as file:
        original = file.read(MAX_BYTES + 1)
    if not 20 <= len(original) <= MAX_BYTES or len(original) % 4:
        raise ValueError('VERRANO-SIZE: expected 20 to 16384 aligned bytes')
    with TemporaryDirectory(dir=output.parent) as temporary:
        raw = Path(temporary) / 'input.spv'
        prepared = raw.with_name('prepared.spv')
        raw.write_bytes(original)
        validate(sdk, raw, stage)
        run_tool(sdk, 'spirv-opt', f'--target-env={TARGET}', '--strip-debug',
                 '--compact-ids', raw, '-o', prepared)
        validate(sdk, prepared, stage)
        contents = prepared.read_bytes()
        prepared.replace(output)
    return dict(profile='verrano-texture-v1' if stage == 'textured-fragment' else 'verrano-triangle-v1', stage=stage,
                input_bytes=len(original), output_bytes=len(contents),
                sha256=hashlib.sha256(contents).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('stage', choices=STAGES)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.sdk, args.source, args.stage, args.output)))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
