"""Compare all pixels from a QEMU native UI run against the real HOST engine."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from build import ROOT,OUT,DEPS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    run=args.run.resolve()
    if run.parent!=ROOT/'build/CASM' or (run/'profile.txt').read_text().strip()!='rmlui-native':
        raise ValueError('Expected a native UI run under build/CASM')
    proof=json.loads((run/'qemu-results.json').read_text())
    if proof['Passed']!=proof['Total'] or not proof['Cases'][0]['FullRmlUiEngine']:
        raise ValueError('QEMU run has not passed')
    sys.path.insert(0,str(Path(__file__).parent.parent))
    from live import Engine,Callback
    from preview import package
    assets,_,_=package()
    engine=Engine(assets,Callback(lambda:1))
    try:
        engine.require(engine.start(changes={'main.rml':(OUT/'guest/main.rml').read_bytes()}))
        engine.require(engine.motion(0))
        image=engine.snapshot(0)
        host=bytes(engine.pixels)
        guest=(run/'build/puente-normal-ui-xrgb.bin').read_bytes()
        if len(guest)!=1280*800*4:raise ValueError('Invalid guest frame size')
        different=sum(host[i:i+4]!=guest[i:i+4] for i in range(0,len(host),4))
        report=dict(Evidence=['HOST','QEMU'],IdenticalPixels=different==0,DifferingPixels=different,
            ComparedPixels=1280*800,FrameSHA256=hashlib.sha256(guest).hexdigest(),
            HostFrameSHA256=hashlib.sha256(host).hexdigest(),
            HostEngineSHA256=hashlib.sha256((assets/'bmo_rmlui_host.dll').read_bytes()).hexdigest(),
            Scope='Same reduced-motion RML/RCSS/fonts; HOST atlas cap 1024, native cap 256; no kernel simulation')
        if different:raise ValueError('HOST/native pixel difference: '+str(different))
        image.save(run/'build/native-ui.png')
        (run/'build/native-visual-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
        print(json.dumps(report,indent=2))
    finally:
        engine.require(engine.close())


if __name__=='__main__':main()
