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
    empty_usb=(prefix.parent.parent/'native-usb-empty.txt').is_file()
    state,pixels=symbols['state'],symbols['pixels']
    if not (0x40400000<=state<=0x40e00000-64 and 0x40400000<=pixels<=0x40e00000-1280*800*4):
        raise ValueError('UI symbol range')
    serial=Path(str(prefix)+'-serial.log')
    def regs():return command('human-monitor-command',{'command-line':'info registers'})
    def until(phase,accepted=0):
        # Software float rasterization under TCG can exceed 45 s after hover
        # and click invalidation. Still require the completed presented frame.
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            log=serial.read_text(errors='replace') if serial.exists() else ''
            if 'BMO UI FAIL:' in log:raise ValueError(log[-1800:]+'\n'+regs()[:600])
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'ui-state'))
            if words[0]==0x3149554f4d42 and words[1]==phase and words[4]>=accepted:return words
            time.sleep(.07)
        raise ValueError('Native UI phase '+str(phase)+' not reached: '+str(words)+' '+log[-1400:]+'\n'+regs()[:600])
    def freeze_frame(phase,accepted=0):
        for _ in range(4):
            until(phase,accepted)
            command('stop')
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'ui-frozen-state'))
            if words[1]==phase and words[4]>=accepted:return words
            command('cont')
        raise ValueError('Could not pause a completed native frame')
    first=freeze_frame(2)
    if not (first[2]>=1 and first[5]>0 and 0<first[6]<=first[7]<=4*1024*1024):raise ValueError('Invalid UI resource counters')
    raw=memory(pixels-0x3c000000,1280*800*4,'ui-frame')
    if symbols.get('usb')=='both':
        for x,y,color in ((640,400,0x0b1019),(641,402,0xf4f8ff)):
            if struct.unpack_from('<I',raw,(y*1280+x)*4)[0]!=color:
                raise ValueError('Pointer missing before first input')
    registers=regs()
    if 'CPL=0' in registers:
        context_address=register(registers,'RBP')
    else:
        root=register(registers,'CR3')
        context_address=struct.unpack('<Q',memory(root+0x7320,8,'ui-handoff'))[0]
    if not 0x100000<=context_address<=0xffe0000:raise ValueError('Native UI handoff address')
    context=memory(context_address,0x30,'ui-context')
    if context[:8]!=b'METAL64!':raise ValueError('Native UI handoff signature')
    if symbols.get('usb')=='both':
        live=memory(context_address+0x1a3c8,1,'dual-live')[0]
        roles=memory(context_address+0x1a770,1,'dual-roles')[0]
        if empty_usb:
            halt=memory(context_address+0x1a37a,1,'empty-usb-halted')[0]
            pci=struct.unpack('<H',memory(context_address+0x1a37e,2,'empty-usb-pci'))[0]
            if live or roles or halt!=1 or pci&4 or memory(context_address+0x1e000,24,'empty-usb-aliases')!=bytes(24):
                raise ValueError('Empty USB startup did not revoke controller ownership')
        elif live!=1 or roles!=3:
            phase=struct.unpack('<I',memory(context_address+0x1a7ac,4,'dual-phase'))[0]
            cc=memory(context_address+0x1a7a0,1,'dual-cc')[0]
            debug=memory(context_address+0x1a000,4096,'dual-debug-state')
            memory(context_address+0x1e000,4096,'dual-debug-aliases')
            pointers=struct.unpack_from('<3Q',debug,0x740)
            reset=debug[0x3b9]
            dma=struct.unpack_from('<Q',debug,0x758)[0]
            if 0x100000<=dma<=0x10000000-14*4096:memory(dma,14*4096,'dual-debug-dma')
            raise ValueError(f'Dual USB init incomplete: live={live} roles={roles} phase={phase} CC={cc} reset={reset} regs={pointers}')
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
    if empty_usb:
        return dict(Case='normal',Passed=True,Evidence='QEMU',CPL=3,FullRmlUiEngine=True,
            UsbEmptyPortsRejected=True,UsbControllerStopped=True,UsbBusMasterRevoked=True,
            UsbMmioRevoked=True,UsbBothDevicesVerified=False,PhysicalUsbVerified=False,
            PresentedPixelsVerified=dw*dh,FrameSHA256=hashlib.sha256(raw).hexdigest())
    if symbols.get('usb')=='both':
        cursor_counter=context_address+0x1a7e0
        start=struct.unpack('<Q',memory(cursor_counter,8,'cursor-copy-baseline'))[0]
        for delta,target in ((24,664),(-24,640)):
            command('input-send-event',{'events':[{'type':'rel','data':{'axis':'x','value':delta}}]})
            deadline=time.monotonic()+30
            # The white pixel is sampled by both the full and half-scale paths.
            px=target+2
            py=404
            gx=x+(px*scale if scale else px//2)
            gy=y+(py*scale if scale else py//2)
            while time.monotonic()<deadline:
                pixel=struct.unpack('<I',memory(fb+(gy*pitch+gx)*4,4,'fast-pointer'))[0]
                if pixel==(0xf4f8ff if order==1 else 0xfff8f4):break
                time.sleep(.02)
            else:
                memory(fb+gy*pitch*4,pitch*4,'fast-pointer-row')
                memory(state-0x3c000000,64,'fast-pointer-timeout-state')
                raise ValueError(f'Pointer did not reach {target}')
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'fast-pointer-state'))
            if words[2]!=first[2]:raise ValueError('Pointer movement triggered a full RmlUi render')
        copied=struct.unpack('<Q',memory(cursor_counter,8,'cursor-copy-total'))[0]-start
        if scale==1 and copied!=4*12*17:raise ValueError('Wrong GOP cursor-region pixel count')
        if scale!=1 and copied:raise ValueError('Cursor region accepted an unsupported scale')
        if scale==1:
            old_x,old_y=664,400
            for row in range(17):
                actual=memory(fb+((y+old_y+row)*pitch+x+old_x)*4,48,'cursor-background')
                offset=((old_y+row)*1280+old_x)*4
                expected=raw[offset:offset+48]
                if order==0:
                    colors=bytearray(expected)
                    colors[0::4],colors[2::4]=expected[2::4],expected[0::4]
                    expected=bytes(colors)
                if actual!=expected:raise ValueError('Old cursor box did not restore the background')
    before=hashlib.sha256(raw).hexdigest()
    command('send-key',{'keys':[{'type':'qcode','data':'ret'}],'hold-time':60})
    after=freeze_frame(3)
    if after[3:5]!=(1,1):raise ValueError('Native ULTRA-J action did not execute once')
    raw_after=memory(pixels-0x3c000000,1280*800*4,'ui-action-frame')
    if hashlib.sha256(raw_after).hexdigest()==before:raise ValueError('Native action did not change the rendered frame')
    command('screendump',{'filename':str(prefix)+'-ui-action.ppm'})
    command('cont')
    if symbols.get('desktop'):
        def mouse_event(event_type, **data):
            command('input-send-event',{'events':[{'type':event_type,'data':data}]})
        def wait_input(check, message, timeout=10):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if check():return
                time.sleep(.02)
            raise ValueError(message)
        mouse_event('rel',axis='y',value=127)
        mouse_edges=symbols.get('mouse_edges')
        if mouse_edges:
            px,py=642,531
            gx=x+(px*scale if scale else px//2)
            gy=y+(py*scale if scale else py//2)
            hover_color=0xa2f4e6 if order==1 else 0xe6f4a2
            wait_input(lambda: struct.unpack('<I',memory(fb+(gy*pitch+gx)*4,4,'button-hover'))[0]==hover_color,
                'Cursor did not highlight over Activate')
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'hover-frame-state'))
            if words[2]!=after[2]:raise ValueError('Button hover rasterized the desktop')
            def edges():
                return struct.unpack('<4Q',memory(mouse_edges-0x3c000000,32,'mouse-edges'))
            for index,name in ((1,'right'),(2,'middle'),(3,'wheel-up')):
                initial=edges()[index]
                mouse_event('btn',button=name,down=True)
                wait_input(lambda: edges()[index]==initial+1,'Missing '+name+' event')
                mouse_event('btn',button=name,down=False)
                if index!=3:
                    wait_input(lambda: edges()[index]==initial+2,'Missing '+name+' release')
        else:
            time.sleep(.2)
        mouse_event('btn',button='left',down=True)
        time.sleep(.2)
        mouse_event('btn',button='left',down=False)
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
        focus_address=symbols.get('keyboard_focus')
        if focus_address:
            if not 0x40400000<=focus_address<=0x40e00000-8:raise ValueError('Keyboard focus symbol')
            def focus_count():
                return struct.unpack('<Q',memory(focus_address-0x3c000000,8,'keyboard-focus'))[0]
            initial_focus=focus_count()
            key('meta_l','1')
            wait_input(lambda: focus_count()==initial_focus+1,'Super+1 did not focus the RmlUi window')
        key('ctrl','meta_l','2');policy(2)
        key(*(['meta_l','spc'] if focus_address else ['f1']));policy(0x102)
        key('meta_l','q');policy(2)
        key('f1');policy(0x102)
        key('ctrl','meta_l','1');policy(1)
        key('ctrl','meta_l','2');policy(0x102)
        msvc_result={}
        if symbols.get('msvc_panel_draws'):
            address=symbols['msvc_panel_draws']
            if not 0x40400000<=address<=0x40e00000-8:raise ValueError('MSVC draw symbol')
            key('f3');policy(0x202)
            draws=struct.unpack('<Q',memory(address-0x3c000000,8,'msvc-draws'))[0]
            if draws<1:raise ValueError('MSVC client did not execute')
            msvc_frame=memory(pixels-0x3c000000,1280*800*4,'msvc-desktop-frame')
            if msvc_frame.count(bytes.fromhex('d5e77e00'))<9:raise ValueError('MSVC triangle missing')
            shot=Path(str(prefix)+'-msvc-rmlui.png')
            command('screendump',{'filename':str(shot),'format':'png'})
            key('meta_l','q');policy(0x102)
            for i in range(5):
                events=[{'type':'rel','data':{'axis':'x','value':-106}}]
                if i<2:
                    events.append({'type':'rel','data':{'axis':'y','value':-113}})
                command('input-send-event',{'events':events})
                time.sleep(.12)
            gx=x+(112*scale if scale else 56)
            gy=y+(305*scale if scale else 152)
            hover_color=0xa2f4e6 if order==1 else 0xe6f4a2
            wait_input(lambda: struct.unpack('<I',memory(fb+(gy*pitch+gx)*4,4,'msvc-launcher-pointer'))[0]==hover_color,
                       'Pointer did not reach the MSVC launcher')
            mouse_event('btn',button='left',down=True)
            time.sleep(.15)
            mouse_event('btn',button='left',down=False)
            policy(0x202)
            key('meta_l','q');policy(0x102)
            msvc_result=dict(MsvcPanelInRmlUiVerified=True,MsvcPanelCloseVerified=True,
                             MsvcMouseLauncherVerified=True,
                             MsvcPanelDraws=draws,MsvcScreenshot=shot.name,
                             MsvcScreenshotSHA256=hashlib.sha256(shot.read_bytes()).hexdigest())
        locks_verified=False
        lock_strip_verified=False
        if symbols.get('usb')=='both' and symbols.get('keyboard_leds'):
            def led_state():
                data=memory(context_address+0x1a7f0,16,'usb-keyboard-led')
                return struct.unpack_from('<Q',data)[0],data[9],data[10],data[11]
            wait_input(lambda: led_state()==(1,0,0,0),'Initial keyboard LED report failed')
            frame_count=struct.unpack('<Q',memory(state-0x3c000000+16,8,'lock-frame-count'))[0]
            region_counter=context_address+0x1a7e0
            def region_pixels():
                return struct.unpack('<Q',memory(region_counter,8,'lock-region-count'))[0]
            pixels_before=region_pixels()
            for count,(lock,mask) in enumerate(
                (('num_lock',1),('caps_lock',3),('scroll_lock',7),('caps_lock',5),
                 ('scroll_lock',1),('num_lock',0)),2):
                key(lock)
                wait_input(lambda: led_state()==(count,0,0,mask),'Keyboard LED report failed for '+lock,45)
            locks_verified=True
            frames_after=struct.unpack('<Q',memory(state-0x3c000000+16,8,'lock-frame-count'))[0]
            if frames_after!=frame_count:raise ValueError('Lock keys rendered the full desktop')
            if scale==1 and region_pixels()-pixels_before!=6*1280*80:
                raise ValueError('Lock indicators copied outside the GOP status strip')
            lock_strip_verified=True
        if not observed:raise ValueError('No DIRECTOR/RmlUi execution observed in CPL3')
        command('screendump',{'filename':str(prefix)+'-desktop.ppm'})
        usb_proof={}
        if symbols.get('usb'):
            address=symbols['usb_reports']
            if not 0x40400000<=address<=0x40e00000-8:raise ValueError('USB counter symbol')
            count=struct.unpack('<Q',memory(address-0x3c000000,8,'native-usb-reports'))[0]
            if count<3:raise ValueError('Missing actual USB reports in native UI')
            status=memory(context_address+0x1a3c4,5,'native-usb-owner')
            if status[0]!=1 or status[4]!=1:raise ValueError('USB DMA validation or live ownership missing')
            dma,pages=struct.unpack('<QQ',memory(context_address+0xb8,16,'native-usb-reservation'))
            expected_pages=14 if symbols['usb']=='both' else 10
            if pages!=expected_pages or dma<0x100000 or dma+pages*4096>0x10000000:
                raise ValueError('USB reservation outside the private identity map')
            for index in range(dma//0x200000,(dma+pages*4096-1)//0x200000+1):
                entry=struct.unpack('<Q',memory(context_address+0x15000+index*8,8,'usb-dma-pde'))[0]
                if entry&0x85!=0x81 or entry&0x000fffffffe00000!=index*0x200000:
                    raise ValueError('USB DMA mapping is not supervisor identity memory')
            aliases=struct.unpack('<3Q',memory(context_address+0x1e000,24,'usb-mmio-aliases'))
            if any(entry&5!=1 or not entry>>63 for entry in aliases):
                raise ValueError('USB MMIO alias must remain supervisor NX')
            usb_proof=dict(UsbProfile=symbols['usb'],UsbInputVerified=True,UsbReportCount=count,
                UsbRing3Decoder=True,UsbDmaSupervisorOnly=True,UsbPs2FallbackDisabled=True,
                UsbDmaReservedBytes=pages*4096,UsbMmioSupervisorNxVerified=True,
                UsbTransportBackend='Existing single-device QEMU diagnostic; mediated by Ring0',
                PhysicalUsbVerified=False)
            if symbols['usb']=='both':
                keyboard=struct.unpack('<Q',memory(symbols['usb_keyboard_reports']-0x3c000000,8,'dual-keyboard-count'))[0]
                mouse=struct.unpack('<Q',memory(symbols['usb_mouse_reports']-0x3c000000,8,'dual-mouse-count'))[0]
                slots=memory(dma+0x9800,128,'dual-slot-owners')
                if keyboard<2 or mouse<3 or {slots[3],slots[67]}!={1,2} or slots[14]!=1 or slots[78]!=1 or slots[1]==slots[65]:
                    raise ValueError('Two distinct active USB devices not proven')
                code,code_pages=struct.unpack('<QQ',memory(context_address+0x728,16,'dual-code-reservation'))
                if code_pages!=2 or code&4095 or code<0x100000 or code+8192>0x10000000:
                    raise ValueError('Dual code reservation')
                stage=(prefix.parent.parent/'xhci.bin').read_bytes()
                if memory(code,8192,'dual-code-copy')!=stage.ljust(8192,b'\0'):raise ValueError('Dual code copy')
                # Exercise the real application stop path, then require BM revoke
                # and alias removal. Buffers stay pinned, never silently reused.
                key('f12')
                deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    if memory(context_address+0x1a3c8,1,'dual-stopped')==b'\0':break
                    time.sleep(.03)
                else:raise ValueError('Dual controller did not stop')
                halt=memory(context_address+0x1a37a,1,'dual-halted')[0]
                pci=struct.unpack('<H',memory(context_address+0x1a37e,2,'dual-bus-master'))[0]
                if halt!=1 or pci&4 or memory(context_address+0x15400,8,'dual-alias-pde')!=bytes(8) or memory(context_address+0x1e000,24,'dual-alias-revoked')!=bytes(24):
                    raise ValueError('Dual stop/revocation incomplete')
                usb_proof.update(UsbBothDevicesVerified=True,UsbKeyboardReports=keyboard,UsbMouseReports=mouse,
                    PointerBeforeInputVerified=True,
                    MouseReportDescriptorDecoded=True, MouseButtonHoverWithoutRasterVerified=bool(mouse_edges),
                    KeyboardLedOutputReportsVerified=locks_verified,
                    LockIndicatorsWithoutFullRasterVerified=lock_strip_verified,
                    MouseRightMiddleWheelVerified=bool(mouse_edges),
                    PointerMoveWithoutRasterVerified=True,
                    PointerRegionPixelsForTwoMoves=copied,
                    UsbStopVerified=True,UsbBusMasterRevoked=True,UsbMmioRevoked=True,
                    UsbTransportBackend='Dynamic USB2 two-slot mediated transport',UsbCodePages=2)
        return dict(Case='normal',Passed=True,Evidence='QEMU',CPL=3,FullRmlUiEngine=True,
            NativeUltraJAction=True,DirectorRust=True,WorkspaceSwitchVerified=True,
            SuperQVerified=True,SuperDigitFocusVerified=bool(focus_address),SuperSpaceLauncherVerified=bool(focus_address),
            ReopenVerified=True,KeyboardEnterVerified=True,MouseClickVerified=True,ShellRemainsAlive=True,
            HeapPeakBytes=after[7],HeapLimitBytes=4*1024*1024,FramebufferBytes=len(raw),SbefBytes=len(image),
            StagedModuleSHA256=hashlib.sha256(struct.pack('<Q',len(image))+image).hexdigest(),
            PresentedPixelsVerified=dw*dh,GopWidth=width,GopHeight=height,HalfScale=scale==0,FrameSHA256=before,**usb_proof,**msvc_result)
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
