"""Measure retained texture payload and idle work, preserving real RmlUi pixels."""
import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import time
from PIL import Image
from live import Engine, Callback, W, H, main as live_checks
from preview import ROOT, package, run


def main():
    if not __debug__:
        raise RuntimeError('Las comprobaciones requieren Python sin -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, help='Prior results.json with images from the same scene')
    args = parser.parse_args()
    live_checks()
    output = ROOT / 'build/rmlui-memory'
    output.mkdir(exist_ok=True)
    visuals = {}
    if args.baseline:
        baseline = json.loads(args.baseline.read_text())
        current = json.loads((ROOT / 'build/rmlui-live/results.json').read_text())
        for name in current['manifest']['engine_resources']:
            assert baseline['manifest']['files'][name]['sha256'] == current['manifest']['files'][name]['sha256'], name
        for name in ('start.png', 'middle.png', 'desktop.png'):
            old = Image.open(args.baseline.parent / name).convert('RGB')
            new = Image.open(ROOT / 'build/rmlui-live' / name).convert('RGB')
            assert old.size == new.size and old.tobytes() == new.tobytes(), name
            visuals[name] = dict(IdenticalPixels=True, RGB_SHA256=hashlib.sha256(new.tobytes()).hexdigest())
    assets, program, _ = package()
    actions = []

    @Callback
    def action():
        try:
            result = run(program)
            if len(result['Calls']) != 2 or result['LiveObjectBytes']:
                return 0
            actions.append(result)
            return 1
        except Exception:
            return 0

    engine = Engine(assets, action)
    did_render = c.c_uint32()
    count = 30
    try:
        engine.require(engine.start())
        engine.require(engine.motion(0))
        # Even a preservation hint cannot bypass the first render.
        engine.require(engine.frame_if_due(0, engine.pixels, W*H, 1, c.byref(did_render)))
        assert did_render.value == 1
        texture_stats = engine.optimization_counters()
        payload = engine.counters()['texture_bytes']
        assert texture_stats['alpha_textures'] > 0
        assert payload < texture_stats['texture_rgba_equivalent_bytes']
        start = time.perf_counter_ns()
        for i in range(1, count+1):
            engine.require(engine.frame(i*1_000_000, engine.pixels, W*H))
        forced_ns = time.perf_counter_ns()-start
        reference = bytes(engine.pixels)
        before = engine.counters()
        before_opt = engine.optimization_counters()
        start = time.perf_counter_ns()
        for i in range(count+1, 2*count+1):
            engine.require(engine.frame_if_due(i*1_000_000, engine.pixels, W*H, 1, c.byref(did_render)))
            assert did_render.value == 0
        skipped_ns = time.perf_counter_ns()-start
        after = engine.counters()
        after_opt = engine.optimization_counters()
        assert bytes(engine.pixels) == reference and after['triangles'] == before['triangles']
        assert after_opt['frames_rendered'] == before_opt['frames_rendered']
        assert after_opt['frames_skipped']-before_opt['frames_skipped'] == count
        assert after['next_delay_ms'] == 0xffffffff
        # Incorrect buffer/time is rejected even if the engine is idle.
        engine.require(engine.frame_if_due(0, engine.pixels, W*H, 1, c.byref(did_render)), 5)
        engine.require(engine.frame_if_due(61_000_000, engine.pixels, W*H-1, 1, c.byref(did_render)), 2)
        assert bytes(engine.pixels) == reference
        # A new target without preserved content always gets a complete frame.
        replacement = (c.c_uint32*(W*H))()
        engine.require(engine.frame_if_due(61_000_000, replacement, W*H, 0, c.byref(did_render)))
        assert did_render.value == 1 and bytes(replacement) == reference
        del replacement
        x,y,width,height = engine.bounds('activate')
        for kind in (0,1,2):
            engine.require(engine.input(kind,int(x+width/2),int(y+height/2)))
        assert engine.counters()['next_delay_ms'] == 0
        engine.require(engine.frame_if_due(62_000_000,engine.pixels,W*H,1,c.byref(did_render)))
        assert did_render.value == 1 and bytes(engine.pixels) != reference and len(actions) == 1
        event_stats = engine.counters()
        # Active animations must keep rendering; only a quiet preserved target may skip.
    finally:
        engine.require(engine.close())
    try:
        engine.require(engine.start())
        engine.require(engine.frame_if_due(0,engine.pixels,W*H,0,c.byref(did_render)))
        first_width = engine.bounds('arrival')[2]
        engine.require(engine.frame_if_due(100_000_000,engine.pixels,W*H,1,c.byref(did_render)))
        assert did_render.value == 1 and engine.bounds('arrival')[2] > first_width
    finally:
        engine.require(engine.close())
    report = dict(evidence='HOST',full_rmlui_ring3_ready=False,
        texture_payload=dict(RgbaEquivalentBytes=texture_stats['texture_rgba_equivalent_bytes'],
            StoredBytes=payload,SavedBytes=texture_stats['texture_rgba_equivalent_bytes']-payload,
            SavedPercent=100*(1-payload/texture_stats['texture_rgba_equivalent_bytes']),
            AlphaTextures=texture_stats['alpha_textures'],RgbaTextures=texture_stats['rgba_textures']),
        idle_work=dict(Calls=count,RenderedFrames=after_opt['frames_rendered']-before_opt['frames_rendered'],
            SkippedFrames=count,SubmittedTriangles=after['triangles']-before['triangles'],
            AvoidedFullTargetClearBytes=count*W*H*4,ForcedCallsElapsedNs=forced_ns,SkippedCallsElapsedNs=skipped_ns),
        visuals=visuals, first_input_after_idle=event_stats,
        checks=['first render cannot skip','preserved idle target untouched','no submitted triangles in idle',
                'invalid time/target rejected in idle','new target forces redraw','input wakes rendering',
                'active animation keeps rendering','all session closes passed'],
        scope='Retained renderer texture payload and HOST native-call timings, not total OS RAM or METAL input latency')
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
