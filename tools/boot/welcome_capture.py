"""Verify the real privilege transition and finite/skippable Rust welcome."""
import struct
import time
from cpu_config import register
from splash_capture import compare_frame


def verify_welcome(command, memory, prefix, intro, *, skip=False):
    frames=set(); phases=set(); context=None
    deadline=time.monotonic()+30
    suffix='-skip' if skip else ''
    def regs():
        return command('human-monitor-command', {'command-line':'info registers'})
    def shot(name):
        command('screendump',{'filename':str(prefix)+suffix+name+'.png','format':'png'})
    def logical(x,y,color):
        raw=color.to_bytes(4,'little')
        if order==0: raw=raw[:3][::-1]+b'\0'
        return memory(fb+(y*scale*pitch+x*scale)*4,4,'welcome-pixel')==raw
    while time.monotonic()<deadline:
        snapshot=regs(); rbp=register(snapshot,'RBP'); rip=register(snapshot,'RIP')
        if 0x100000<=rbp<=0xffe0000 and rbp%4096==0:
            candidate=memory(rbp,0x30,'welcome-context')
            if candidate[:8]==b'METAL64!':
                context=candidate
                code=struct.unpack_from('<Q',context,8)[0]
                frame=register(snapshot,'R12')
                low,high=(0xb6,0xd0) if len(intro)==64 else (0xb3,0xcd)
                if frame in (1,2) and frame not in frames and low<=rip-code<high:
                    command('stop')
                    compare_frame(memory,context,intro,frame)
                    shot('-ring0-'+str(frame))
                    frames.add(frame)
                    command('cont')
        if context:
            fb=struct.unpack_from('<Q',context,0x10)[0]
            width,height,pitch,order=struct.unpack_from('<IIII',context,0x20)
            if not (640<=width<=4096 and 400<=height<=4096 and width<=pitch<=8192 and order in (0,1)):
                raise ValueError('Framebuffer invalido')
            scale=2 if width>=1280 and height>=800 else 1
            if 'HLT=1' in snapshot and 'CPL=0' in snapshot and logical(112,72,0x2b3b4c):
                # The actual SYSCALL/IRET frame identifies a CPL3 caller while WAIT sleeps in Ring 0.
                stack=memory(register(snapshot,'RSP')+8,16,'welcome-return')
                user_rip,user_cs=struct.unpack('<QQ',stack)
                if not (0x40000000<=user_rip<0x40002000 and user_cs==0x23):
                    raise ValueError('Bienvenida sin llamador CPL3')
                phase=max((p for p in range(3) if logical(192+p*88,258,0x7de3d2)),default=-1)
                if phase>=0 and phase not in phases:
                    shot('-welcome-'+str(phase))
                    phases.add(phase)
                    if skip:
                        command('send-key',{'keys':[{'type':'qcode','data':'f2'}],'hold-time':100})
            if skip:
                # F2 consumed by the welcome must be replayed once into CABINA, not lost.
                ready=logical(24,24,0x232638) and logical(40,86,0x40465d)
            else:
                ready=logical(52,99,0x5ad8ff) and logical(70,55,0xa8c5ff)
            if ready:
                if frames!={1,2} or (not skip and phases!={0,1,2}) or (skip and not phases):
                    raise ValueError(f'Faltan fases reales: gato={frames}, bienvenida={phases}')
                shot('-desktop')
                return dict(Case='normal',Passed=True,Evidence='QEMU',Ring0CatFrames=sorted(frames),
                    Ring3WelcomePhases=sorted(phases),Cpl3WelcomeCaller=True,
                    WelcomeUsesWait=True,WelcomeSkipped=skip,FirstInputReplayed=skip,
                    DesktopReached=True,FullRmlUiEngine=False,
                    Scope='Existing ULTRA-J launcher desktop, not the full RmlUi port')
        time.sleep(0.01)
    raise ValueError(f'No termino la transicion: gato={frames}, bienvenida={phases}; {snapshot[:420]}')
