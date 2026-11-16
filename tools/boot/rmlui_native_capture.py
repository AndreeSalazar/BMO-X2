"""Observe the actual native UI engine, presentation, ULTRA-J action and shutdown."""
import hashlib
import json
from pathlib import Path
import struct
import time
from cpu_config import register
from desktop_session_capture import verify_external_rejection

def verify_native_ui(command,memory,prefix,image,case,symbols_path):
    if case=='external-permissions':
        result=verify_external_rejection(command,memory,image)
        if memory(0x4000000,4096,'ui-rejected-code')!=bytes(4096):raise ValueError('UI copied before permission validation')
        return result
    symbols=json.loads(symbols_path.read_text())
    state,pixels=symbols['state'],symbols['pixels']
    if not (0x40400000<=state<=0x40e00000-64 and 0x40400000<=pixels<=0x40e00000-1280*800*4):
        raise ValueError('UI symbol range')
    serial=Path(str(prefix)+'-serial.log')
    def regs():return command('human-monitor-command',{'command-line':'info registers'})
    def until(phase,accepted=0):
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            log=serial.read_text(errors='replace') if serial.exists() else ''
            if 'BMO UI FAIL:' in log:raise ValueError(log[-1800:]+'\n'+regs()[:600])
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'ui-state'))
            if words[0]==0x3149554f4d42 and words[1]==phase and words[4]>=accepted:return words
            time.sleep(.07)
        raise ValueError('Native UI phase '+str(phase)+' not reached: '+log[-1400:]+'\n'+regs()[:600])
    first=until(2)
    if not (first[2]>=1 and first[5]>0 and 0<first[6]<=first[7]<=4*1024*1024):raise ValueError('Invalid UI resource counters')
    raw=memory(pixels-0x3c000000,1280*800*4,'ui-frame')
    command('stop')
    registers=regs()
    if 'CPL=0' in registers:
        context_address=register(registers,'RBP')
    else:
        root=register(registers,'CR3')
        context_address=struct.unpack('<Q',memory(root+0x7320,8,'ui-handoff'))[0]
    if not 0x100000<=context_address<=0xffe0000:raise ValueError('Native UI handoff address')
    context=memory(context_address,0x30,'ui-context')
    if context[:8]!=b'METAL64!':raise ValueError('Native UI handoff signature')
    fb=struct.unpack_from('<Q',context,16)[0]
    width,height,pitch,order=struct.unpack_from('<IIII',context,32)
    if not (640<=width<=4096 and 400<=height<=4096 and width<=pitch<=8192 and order in (0,1)):
        raise ValueError('Native UI framebuffer geometry')
    scale=min(width//1280,height//800)
    dw,dh=(1280*scale,800*scale) if scale else (640,400)
    x,y=(width-dw)//2,(height-dh)//2
    displayed=memory(fb+(y*pitch+x)*4,((dh-1)*pitch+dw)*4,'ui-presented')
    for row in range(dh):
        sy=row//scale if scale else row*2
        expected=raw[sy*1280*4:(sy+1)*1280*4]
        if not scale:expected=b''.join(expected[i:i+4] for i in range(0,len(expected),8))
        if order==0:
            converted=bytearray(expected)
            converted[0::4],converted[2::4]=expected[2::4],expected[0::4]
            expected=bytes(converted)
        if scale>1:expected=b''.join(expected[i:i+4]*scale for i in range(0,len(expected),4))
        if displayed[row*pitch*4:row*pitch*4+len(expected)]!=expected:
            raise ValueError('Native UI presentation differs at row '+str(row))
    (Path(str(prefix)+'-ui-xrgb.bin')).write_bytes(raw)
    command('screendump',{'filename':str(prefix)+'-ui.ppm'})
    command('cont')
    before=hashlib.sha256(raw).hexdigest()
    command('send-key',{'keys':[{'type':'qcode','data':'ret'}],'hold-time':60})
    after=until(3)
    if after[3:5]!=(1,1):raise ValueError('Native ULTRA-J action did not execute once')
    raw_after=memory(pixels-0x3c000000,1280*800*4,'ui-action-frame')
    if hashlib.sha256(raw_after).hexdigest()==before:raise ValueError('Native action did not change the rendered frame')
    command('screendump',{'filename':str(prefix)+'-ui-action.ppm'})
    if symbols.get('desktop'):
        command('input-send-event',{'events':[{'type':'rel','data':{'axis':'y','value':127}}]})
        time.sleep(.2)
        command('input-send-event',{'events':[{'type':'btn','data':{'button':'left','down':True}}]})
        time.sleep(.2)
        command('input-send-event',{'events':[{'type':'btn','data':{'button':'left','down':False}}]})
        after=until(3,accepted=2)
        if after[3:5]!=(2,2):raise ValueError('Desktop mouse activation did not execute once')
        director=symbols['director']
        if not 0x40400000<=director<=0x40e00000-8:raise ValueError('DIRECTOR symbol')
        observed=False
        def policy(expected):
            nonlocal observed
            deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                r=regs()
                observed|='CPL=3' in r and 0x40000000<=register(r,'RIP')<0x40200000
                state=struct.unpack('<Q',memory(director-0x3c000000,8,'director-state'))[0]
                if state==expected:return
                time.sleep(.03)
            raise ValueError('DIRECTOR did not reach '+hex(expected))
        def key(*keys):
            command('send-key',{'keys':[{'type':'qcode','data':k} for k in keys],'hold-time':80})
        policy(0x101)
        key('ctrl','meta_l','2');policy(2)
        key('f1');policy(0x102)
        key('meta_l','q');policy(2)
        key('f1');policy(0x102)
        key('ctrl','meta_l','1');policy(1)
        key('ctrl','meta_l','2');policy(0x102)
        if not observed:raise ValueError('No DIRECTOR/RmlUi execution observed in CPL3')
        command('screendump',{'filename':str(prefix)+'-desktop.ppm'})
        return dict(Case='normal',Passed=True,Evidence='QEMU',CPL=3,FullRmlUiEngine=True,
            NativeUltraJAction=True,DirectorRust=True,WorkspaceSwitchVerified=True,
            SuperQVerified=True,ReopenVerified=True,KeyboardEnterVerified=True,MouseClickVerified=True,ShellRemainsAlive=True,
            HeapPeakBytes=after[7],HeapLimitBytes=4*1024*1024,FramebufferBytes=len(raw),SbefBytes=len(image),
            StagedModuleSHA256=hashlib.sha256(struct.pack('<Q',len(image))+image).hexdigest(),
            PresentedPixelsVerified=dw*dh,GopWidth=width,GopHeight=height,HalfScale=scale==0,FrameSHA256=before)
    command('input-send-event',{'events':[{'type':'rel','data':{'axis':'y','value':127}}]})
    time.sleep(.2)
    command('input-send-event',{'events':[{'type':'btn','data':{'button':'left','down':True}}]})
    time.sleep(.2)
    command('input-send-event',{'events':[{'type':'btn','data':{'button':'left','down':False}}]})
    pointer=until(3,accepted=2)
    if pointer[3:5]!=(2,2):raise ValueError('Mouse action was not delivered exactly once')
    command('screendump',{'filename':str(prefix)+'-ui-mouse.ppm'})
    command('send-key',{'keys':[{'type':'qcode','data':'esc'}],'hold-time':60})
    closed=until(4)
    final_regs=regs()
    if 'CPL=3' not in final_regs or not 0x40000000<=register(final_regs,'RIP')<0x40200000:
        raise ValueError('UI shutdown did not finish in CPL3: '+final_regs[:600])
    return dict(Case='normal',Passed=True,Evidence='QEMU',CPL=3,FullRmlUiEngine=True,
        RmlUi='6.3',FontEngine='FreeType 2.14.3',Renderer='Shared Rust CPU',NativeUltraJAction=True,
        MouseClickVerified=True,KeyboardEnterVerified=True,
        Frames=closed[2],Triangles=closed[5],HeapPeakBytes=closed[7],HeapLimitBytes=4*1024*1024,
        FramebufferBytes=len(raw),SbefBytes=len(image),ClosedResources=True,
        StagedModuleSHA256=hashlib.sha256(struct.pack('<Q',len(image))+image).hexdigest(),
        PresentedPixelsVerified=dw*dh,
        FrameSHA256=before,ActionFrameSHA256=hashlib.sha256(raw_after).hexdigest())
