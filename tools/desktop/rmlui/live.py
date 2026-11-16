"""Real C++ RmlUi session: memory resources, injected time, input and ULTRA-J HOST action."""
import ctypes as c
import json
from PIL import Image
from preview import ROOT, package, sha, run

W, H = 1280, 800
Callback = c.CFUNCTYPE(c.c_int)


class Blob(c.Structure):
    _fields_ = [('name', c.c_char_p), ('data', c.c_void_p), ('length', c.c_size_t)]


class Stats(c.Structure):
    _fields_ = [(name, c.c_uint64) for name in (
        'time_ns', 'triangles', 'geometry_bytes', 'texture_bytes', 'peak_geometry_bytes',
        'peak_texture_bytes', 'open_files', 'denied_files', 'click_events', 'action_accepted')]


class OptimizationStats(c.Structure):
    _fields_ = [(name, c.c_uint64) for name in (
        'texture_rgba_equivalent_bytes', 'peak_texture_rgba_equivalent_bytes',
        'alpha_textures', 'rgba_textures', 'frames_rendered', 'frames_skipped')]


class Engine:
    def __init__(self, assets, callback):
        self.assets, self.callback = assets, callback
        self.active = False
        self.lib = c.CDLL(str(assets / 'bmo_rmlui_host.dll'))
        signatures = {
            'open': ([c.POINTER(Blob), c.c_size_t, Callback], c.c_int),
            'frame': ([c.c_uint64, c.POINTER(c.c_uint32), c.c_size_t], c.c_int),
            'frame_if_due': ([c.c_uint64, c.POINTER(c.c_uint32), c.c_size_t, c.c_uint32, c.POINTER(c.c_uint32)], c.c_int),
            'input': ([c.c_uint32, c.c_int32, c.c_int32], c.c_int),
            'box': ([c.c_char_p, c.POINTER(c.c_float)], c.c_int),
            'motion': ([c.c_uint32], c.c_int),
            'next_delay_ms': ([c.POINTER(c.c_uint32)], c.c_int),
            'stats': ([c.POINTER(Stats)], c.c_int),
            'optimization_stats': ([c.POINTER(OptimizationStats)], c.c_int),
            'close': ([], c.c_int), 'error': ([], c.c_char_p),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.lib, 'bmo_ui_' + name)
            function.argtypes, function.restype = args, result
            setattr(self, '_close' if name == 'close' else name, function)
        self.pixels = (c.c_uint32 * (W * H))()
        self.retained = []

    def resources(self, changes=None, omit=()):
        files = {name: (self.assets / name).read_bytes() for name in (
            'main.rml', 'style.rcss', 'LatoLatin-Regular.ttf', 'LatoLatin-Bold.ttf')}
        files.update(changes or {})
        retained, records = [], []
        for name, data in files.items():
            if name in omit:
                continue
            buffer = c.create_string_buffer(data)
            encoded = name.encode('ascii')
            retained.extend((buffer, encoded))
            records.append(Blob(encoded, c.cast(buffer, c.c_void_p), len(data)))
        table = (Blob * len(records))(*records)
        # Keep immutable backing storage alive until close; never retain caller's frame pointer in C++.
        self.retained = [*retained, table]
        return table

    def start(self, **kwargs):
        if self.active:
            return 1
        table = self.resources(**kwargs)
        status = self.open(table, len(table), self.callback)
        self.active = status == 0
        return status

    def close(self):
        status = self._close()
        if status == 0:
            self.active = False
            self.retained = []
        return status

    def require(self, status, expected=0):
        if status != expected:
            raise RuntimeError(f'engine status {status}, expected {expected}: {self.error()}')

    def snapshot(self, ns):
        self.require(self.frame(ns, self.pixels, W * H))
        return Image.frombytes('RGB', (W, H), bytes(self.pixels), 'raw', 'BGRX')

    def bounds(self, element):
        box = (c.c_float * 4)()
        self.require(self.box(element.encode('ascii'), box))
        return list(box)

    def counters(self):
        stats, delay = Stats(), c.c_uint32()
        self.require(self.stats(c.byref(stats)))
        self.require(self.next_delay_ms(c.byref(delay)))
        return {**{name: getattr(stats, name) for name, _ in Stats._fields_},
                'next_delay_ms': delay.value}

    def optimization_counters(self):
        stats = OptimizationStats()
        self.require(self.optimization_stats(c.byref(stats)))
        return {name: getattr(stats, name) for name, _ in OptimizationStats._fields_}


def main():
    if not __debug__:
        raise RuntimeError('La prueba requiere Python sin -O')
    assets, program, manifest = package()
    output = ROOT / 'build/rmlui-live'
    output.mkdir(exist_ok=True)
    actions, callbacks, checks = [], [], []
    engine = None
    accept_action = True

    @Callback
    def action():
        try:
            # Native API rejects destructive reentry while dispatching an event.
            reentry = engine.close()
            if reentry != 1:
                raise RuntimeError('El callback pudo destruir la sesion activa')
            if not accept_action:
                callbacks.append(dict(rejected=True, reentrant_close_status=reentry))
                return 0
            result = run(program)
            if len(result['Calls']) != 2 or result['LiveObjectBytes'] != 0:
                raise RuntimeError('Accion UJBC incompleta')
            actions.append(result)
            callbacks.append(dict(reentrant_close_status=reentry))
            return 1
        except Exception as error:
            callbacks.append(dict(error=str(error)))
            return 0

    engine = Engine(assets, action)
    engine.require(engine.frame(0, engine.pixels, W * H), 1)
    engine.require(engine.start(omit=('style.rcss',)), 3)
    engine.require(engine.start(changes={'../escape.rml': b'blocked'}), 3)
    bad_style = (assets / 'style.rcss').read_bytes().replace(
        b'transition:color 0.12s linear-in-out', b'transition:color 0.12s invalid-tween')
    engine.require(engine.start(changes={'style.rcss': bad_style}), 3)
    checks.extend(('missing resource rejected', 'path traversal rejected', 'invalid RCSS reported instead of silently ignored'))
    frames, widths, statistics = [], [], []
    try:
        engine.require(engine.start())
        # The legacy file-based entry must not replace the live engine's global interfaces.
        legacy = engine.lib.bmo_rmlui_preview
        legacy.argtypes, legacy.restype = [c.c_char_p, c.c_char_p, Callback], c.c_int
        engine.require(legacy(str(assets).encode(), str(output).encode(), action), 1)
        for ms in range(0, 451, 50):
            image = engine.snapshot(ms * 1_000_000)
            frames.append(image)
            widths.append(engine.bounds('arrival')[2])
            statistics.append(engine.counters())
        assert widths[-1] > widths[0] + 150 and all(a <= b + 0.5 for a, b in zip(widths, widths[1:])), widths
        ix, iy, iw, ih = engine.bounds('intro')
        intro_box = (int(ix), int(iy), int(ix+iw), int(iy+ih))
        intro_pixels = [frames[i].crop(intro_box).tobytes() for i in (0,2,4)]
        assert intro_pixels[0] != intro_pixels[1] != intro_pixels[2]
        checks.append('intro opacity interpolates and remains visible after animationend')
        initial = bytes(engine.pixels)
        engine.require(engine.frame(400_000_000, engine.pixels, W * H), 5)
        engine.require(engine.frame(450_000_000, engine.pixels, W * H - 1), 2)
        assert bytes(engine.pixels) == initial
        checks.extend(('legacy entry cannot steal ownership', 'RCSS width interpolated with injected time',
                       'clock reversal rejected without writing', 'wrong target length rejected without writing'))
        x, y, width, height = engine.bounds('activate')
        for kind in (0, 1, 2):
            engine.require(engine.input(kind, int(x + width / 2), int(y + height / 2)))
        for ms in (500, 550, 600, 650, 700):
            frames.append(engine.snapshot(ms * 1_000_000))
        sx, sy, sw, sh = engine.bounds('state')
        box = (int(sx), int(sy), int(sx + sw), int(sy + sh))
        state_frames = [frames[index].crop(box).tobytes() for index in (10, 11, 13)]
        assert state_frames[0] != state_frames[1] != state_frames[2]
        checks.append('RCSS text color transition interpolates after ULTRA-J action')
        stats = engine.counters()
        assert len(actions) == stats['click_events'] == stats['action_accepted'] == 1
        assert stats['open_files'] == stats['denied_files'] == 0
        assert stats['next_delay_ms'] == 0xffffffff
        checks.extend(('pointer click dispatches ULTRA-J exactly once', 'destructive callback reentry rejected'))
        checks.append('engine requests no updates after animations settle')
        frames[-1].save(output / 'desktop.png')
    finally:
        engine.require(engine.close())
    engine.require(engine.close(), 1)

    accept_action = False
    try:
        engine.require(engine.start())
        engine.snapshot(0)
        x, y, width, height = engine.bounds('activate')
        for kind in (0, 1, 2):
            engine.require(engine.input(kind, int(x + width/2), int(y + height/2)))
        engine.snapshot(200_000_000)
        rejected_stats = engine.counters()
        assert rejected_stats['click_events'] == 1 and rejected_stats['action_accepted'] == 0 and len(actions) == 1
        checks.append('rejected ULTRA-J callback changes view without executing an action')
        for kind in (3, 3, 3, 4):
            engine.require(engine.input(kind, 0, 0))
        engine.snapshot(300_000_000)
        keyboard_stats = engine.counters()
        assert keyboard_stats['click_events'] == 2 and len(actions) == 1
        checks.append('repeated Enter down plus one release dispatches one additional click')
    finally:
        engine.require(engine.close())
    accept_action = True

    # Reduced motion must settle immediately and stay pixel-identical with time changes.
    try:
        engine.require(engine.start())
        engine.require(engine.motion(0))
        reduced = engine.snapshot(0)
        reduced_width = engine.bounds('arrival')[2]
        later = engine.snapshot(700_000_000)
        assert reduced_width == 220 and reduced.tobytes() == later.tobytes()
        reduced_stats = engine.counters()
        checks.append('reduced motion stable without animation')
    finally:
        engine.require(engine.close())

    # Unsupported renderer features must be reported, never silently displayed incorrectly.
    for style, message in ((b'transform:rotate(1deg)', b'transforms outside CPU profile'),
                           (b'filter:blur(2px)', b'layers, masks, filters or shaders outside CPU profile')):
        document = (assets / 'main.rml').read_bytes().replace(b'id="focus-panel"', b'id="focus-panel" style="'+style+b'"')
        try:
            engine.require(engine.start(changes={'main.rml': document}))
            engine.require(engine.frame(0, engine.pixels, W * H), 4)
            assert message in engine.error()
            engine.require(engine.input(0, 10, 10), 1)
            checks.append(style.decode()+': unsupported feature reported, session blocked until close')
        finally:
            engine.require(engine.close())

    # Reinitialization must reproduce the initial animated frame.
    try:
        engine.require(engine.start())
        assert engine.snapshot(0).tobytes() == frames[0].tobytes()
        checks.append('close releases adapter handles and session can reinitialize')
    finally:
        engine.require(engine.close())

    # Artifacts come from real RmlUi frames, not synthesized motion.
    frames[0].save(output / 'start.png')
    frames[4].save(output / 'middle.png')
    frames[0].save(output / 'animation.gif', save_all=True, append_images=frames[1:],
                   duration=50, loop=0, optimize=False)
    report = dict(evidence='HOST', full_rmlui_ring3_ready=False, sbef=False,
        api='bmo-ui-memory-v1', checks=checks, animation_widths=widths,
        timestamps_ms=list(range(0, 451, 50)), animation_stats=statistics,
        final_stats=stats, reduced_motion_stats=reduced_stats, callbacks=callbacks,
        rejected_action_stats=rejected_stats,
        keyboard_stats=keyboard_stats,
        texture_budget_basis='RGBA-equivalent input bytes before lossless mask packing; original limit unchanged',
        ultra_j=actions, manifest=manifest,
        framebuffer_bytes=W * H * 4, frame_target='borrowed from caller per frame, no second native framebuffer',
        resource_limits=dict(files=8, each_bytes=2*1024*1024, total_bytes=8*1024*1024,
                             open_cursors=32, geometry_bytes=16*1024*1024, texture_bytes=16*1024*1024),
        limits_scope='Adapter resources only; not a global bound on RmlUi, FreeType or the C++ runtime',
        images={p.name: sha(p) for p in output.glob('*') if p.suffix in ('.png', '.gif')})
    (output / 'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='ascii')
    print(json.dumps(dict(Checks=len(checks),Widths=widths,Stats=stats,Output=str(output)),indent=2))


if __name__ == '__main__':
    main()
