// Actual RmlUi/FreeType and shared Rust rasterizer in one Ring 3 application.
#include "../renderer.h"
#include "../memory_files.h"
#include "guest_invoke.h"
#include <cstdio>
#include <cstdlib>
extern "C" {
void bmo_native_clock(uint64_t);
[[noreturn]] void bmo_native_fail(const char*);
void bmo_native_exit_handlers();
int bmo_uj_action();
extern const unsigned char resource_0[], resource_0_end[],resource_1[],resource_1_end[];
extern const unsigned char resource_2[], resource_2_end[],resource_3[],resource_3_end[];
extern size_t bmo_heap_live,bmo_heap_peak;
extern void (*__init_array_start[])(void),(*__init_array_end[])(void);
struct NativeState { uint64_t magic,phase,frames,clicks,accepted,triangles,heap_live,heap_peak; };
volatile NativeState bmo_ui_state;
uint32_t bmo_ui_pixels[1280*800];
#ifdef BMO_DESKTOP_UI
void bmo_director_init();uint64_t bmo_director_open();uint64_t bmo_director_state();uint32_t bmo_director_key(uint32_t);
volatile uint64_t bmo_ui_director;
#endif
#ifdef BMO_USB_INPUT
void bmo_usb_init(uint32_t);uint32_t bmo_usb_report(uint64_t);uint64_t bmo_usb_event();
volatile uint64_t bmo_ui_usb_reports;
#ifdef BMO_USB_DUAL
uint32_t bmo_usb_report_kind(uint64_t,uint32_t);uint32_t bmo_usb_disconnect();
uint32_t bmo_mouse_format(const uint8_t*,size_t);uint64_t bmo_mouse_decode(uint64_t,uint32_t);
volatile uint64_t bmo_ui_usb_keyboard_reports,bmo_ui_usb_mouse_reports;
#endif
#endif
}
namespace BmoUi {[[noreturn]] void native_failure(const char* s) {bmo_native_fail(s);}}
static void log(const char* s) {while(*s)doom_invoke(5,7,(unsigned char)*s++,0);}
class Clock final:public Rml::SystemInterface {
public: double now=0;
    double GetElapsedTime() override {return now;}
    bool LogMessage(Rml::Log::Type type,const Rml::String& text) override {
        if(type<=Rml::Log::LT_WARNING) {log(text.c_str());log("\n");}
        return true;
    }
};
class Action final:public Rml::EventListener {
    void ProcessEvent(Rml::Event& event) override {
        if(event.GetType()!="click")return;
        bmo_ui_state.phase=2; // A new action is not observable as complete before presentation.
        bmo_ui_state.clicks=bmo_ui_state.clicks+1;
        const int ok=bmo_uj_action();
        if(ok!=1)bmo_native_fail("ULTRA-J action");
        bmo_ui_state.accepted=bmo_ui_state.accepted+1;
        auto doc=event.GetCurrentElement()->GetOwnerDocument();
        doc->GetElementById("result")->SetInnerRML("ULTRA-J nativo: evento ejecutado y region cerrada.");
        doc->GetElementById("state")->SetInnerRML("Accion nativa verificada");
        doc->GetElementById("state")->SetClass("ready",true);
        log("BMO UI ACTION\n");
    }
};
#ifdef BMO_DESKTOP_UI
class Launcher final:public Rml::EventListener {
    void ProcessEvent(Rml::Event& e) override {if(e.GetType()=="click")bmo_director_open();}
};
#endif
static void check(bool ok,const char* error) {if(!ok)bmo_native_fail(error);}
extern "C" void bmo_main() {
    // The loader enters _start with a 16-byte-aligned stack, as for the Rust client.
    log("BMO UI CTORS\n");
    for(auto init=__init_array_start;init!=__init_array_end;++init)(*init)();
    bmo_ui_state.magic=0x3149554f4d42;
    bmo_ui_state.phase=1;log("BMO UI START\n");
    char number[64];snprintf(number,sizeof(number),"%.2f",1.25);
    check(std::strcmp(number,"1.25")==0,"decimal format");
    void* aligned=aligned_alloc(64,128);check(aligned && (uintptr_t(aligned)%64)==0,"alignment");free(aligned);
    auto first=static_cast<unsigned char*>(calloc(1,256));check(first,"calloc");
    for(size_t n=0;n<256;++n)check(first[n]==0,"calloc zero");
    first[0]=91;auto moved=static_cast<unsigned char*>(realloc(first,512));
    check(moved && moved[0]==91,"realloc preservation");
    check(!realloc(moved,SIZE_MAX) && moved[0]==91,"failed realloc preservation");free(moved);
    check(!calloc(SIZE_MAX,2) && !malloc(5*1024*1024),"heap bound");
    check(!fopen("forbidden","rb"),"disk denied");
    check(doom_invoke(1,9,0,0)==257 && doom_invoke(2,9,(uintptr_t)bmo_ui_pixels,0)==257 &&
          doom_invoke(1,9,(uintptr_t)bmo_ui_pixels+1,0)==257 &&
          doom_invoke(1,9,0x40e00000-1280*800*4+4,0)==257 &&
          doom_invoke(1,6,(uintptr_t)bmo_ui_pixels,0)==257,"presentation boundary");
    log("BMO UI SELFTEST OK\n");
    const BmoUiBlob blobs[]={
        {"main.rml",resource_0,size_t(resource_0_end-resource_0)},
        {"style.rcss",resource_1,size_t(resource_1_end-resource_1)},
        {"LatoLatin-Regular.ttf",resource_2,size_t(resource_2_end-resource_2)},
        {"LatoLatin-Bold.ttf",resource_3,size_t(resource_3_end-resource_3)}};
    BmoUi::Renderer renderer;BmoUi::MemoryFiles files;Clock clock;Action action;
    check(files.assign(blobs,4),"resources");
    Rml::SetRenderInterface(&renderer);Rml::SetSystemInterface(&clock);Rml::SetFileInterface(&files);
    check(Rml::Initialise(),"initialise");
    log("BMO UI INITIALISED\n");
    check(Rml::LoadFontFace("LatoLatin-Regular.ttf") && Rml::LoadFontFace("LatoLatin-Bold.ttf"),"fonts");
    log("BMO UI FONTS\n");
    auto context=Rml::CreateContext("BMO-X2 native",{1280,800});check(context,"context");
    auto doc=context->LoadDocument("main.rml");check(doc && !files.denied,"document");
    log("BMO UI DOCUMENT\n");
    doc->SetClass("reduced-motion",true);
    doc->SetClass("arrived",true);doc->SetClass("intro-ready",true);
    auto button=doc->GetElementById("activate");check(button,"button");button->AddEventListener("click",&action);
    doc->Show();
#ifdef BMO_DESKTOP_UI
    bmo_director_init();bmo_director_open();Launcher launcher;
    doc->GetElementById("open-app")->AddEventListener("click",&launcher);
    auto sync_policy=[&]() {
        auto policy=bmo_director_state();char label[128];
        snprintf(label,sizeof(label),"Espacio %u / %s",unsigned(policy&255),(policy>>8)?"ULTRA-J activo":"Sin ventanas. Abre ULTRA-J.");
#ifdef BMO_USB_DUAL
        auto usb=doom_invoke(3,3,21,0);
        snprintf(label,sizeof(label),"Espacio %u / USB %s / K:%s M:%s / fase %u CC %u",unsigned(policy&255),
            (usb>>24)&1?"ON":"OFF",usb&0x100?"OK":"espera",usb&0x200?"OK":"espera",unsigned(usb&255),unsigned((usb>>16)&255));
#endif
        doc->GetElementById("desktop-status")->SetInnerRML(label);
        doc->GetElementById("workspace")->SetProperty("display",(policy>>8)?"flex":"none");
    };
#endif
    int pointer_x=640,pointer_y=400,packet_index=0;
    unsigned flags=0,dx=0;bool left=false;
    static constexpr char pointer[][13]={
        "#           ", "##          ", "#.#         ", "#..#        ",
        "#...#       ", "#....#      ", "#.....#     ", "#......#    ",
        "#.......#   ", "#........#  ", "#.....##### ", "#..#..#     ",
        "#.# #..#    ", "##  #..#    ", "#    #..#   ", "     #..#   ",
        "      ##    ",
    };
    uint32_t under_pointer[17][12];
    int drawn_x=pointer_x,drawn_y=pointer_y;
    auto draw_pointer=[&]() {
        drawn_x=pointer_x;drawn_y=pointer_y;
        for(int y=0;y<17 && drawn_y+y<800;++y)
            for(int x=0;x<12 && drawn_x+x<1280;++x) {
                auto& pixel=bmo_ui_pixels[(drawn_y+y)*1280+drawn_x+x];
                under_pointer[y][x]=pixel;
                if(pointer[y][x]!=' ')pixel=pointer[y][x]=='#'?0x0b1019:0xf4f8ff;
            }
    };
    auto present=[&]() {
        check(doom_invoke(1,9,(uintptr_t)bmo_ui_pixels,0)==0,"present");
    };
    auto frame=[&]() {
        bmo_ui_state.phase=1;
#ifdef BMO_DESKTOP_UI
        sync_policy();
#endif
        renderer.pixels=bmo_ui_pixels;renderer.pixel_count=1280*800;
        renderer.frame(context);renderer.pixels=nullptr;renderer.pixel_count=0;
        draw_pointer();
        check(!files.denied,"resource access");
        bmo_ui_state.frames=bmo_ui_state.frames+1;
        bmo_ui_state.triangles=renderer.triangles;
        bmo_ui_state.heap_live=bmo_heap_live;bmo_ui_state.heap_peak=bmo_heap_peak;
        present();
#ifdef BMO_DESKTOP_UI
        bmo_ui_director=bmo_director_state();
#endif
        bmo_ui_state.phase=bmo_ui_state.accepted?3:2;
    };
    #ifdef BMO_USB_INPUT
    bmo_usb_init(
    #ifdef BMO_USB_DUAL
        2
    #elif defined(BMO_USB_MOUSE)
        1
    #else
        0
    #endif
    );
    doom_invoke(3,3,4,0);
#ifdef BMO_USB_DUAL
    uint64_t descriptor[64]={};
    const auto descriptor_size=doom_invoke(3,3,22,~0UL);
    bool mouse_format_ready=false;
    if(descriptor_size && descriptor_size<=sizeof(descriptor)) {
        for(size_t i=0;i<descriptor_size;i+=8)descriptor[i/8]=doom_invoke(3,3,22,i);
        mouse_format_ready=bmo_mouse_format(reinterpret_cast<const uint8_t*>(descriptor),descriptor_size)==1;
    }
    if(!mouse_format_ready)log("BMO UI USB MOUSE FORMAT UNSUPPORTED\n");
    if(doom_invoke(3,3,18,0)!=1)log("BMO UI USB TRANSPORT PENDING\n");
    else log("BMO UI USB TRANSPORT READY\n");
#else
    check(doom_invoke(3,3,18,0)==1,"USB transport start");
    log("BMO UI USB TRANSPORT READY\n");
#endif
    #endif
    auto hovered_button=[&]() -> Rml::Element* {
        for(auto* element=context->GetHoverElement();element;element=element->GetParentNode())
            if(element->GetTagName()=="button")return element;
        return nullptr;
    };
    auto mouse_input=[&](int dx,int dy,unsigned buttons) {
        pointer_x=std::clamp(pointer_x+dx,0,1279);pointer_y=std::clamp(pointer_y+dy,0,799);
        // Only buttons use hover styles in the bundled desktop document.
        auto* hover=hovered_button();
        context->ProcessMouseMove(pointer_x,pointer_y,0);
        bool pressed=(buttons&1)!=0;
        const bool redraw=hover!=hovered_button() || pressed!=left;
        if(pressed!=left) {
            if(pressed)context->ProcessMouseButtonDown(0,0);else context->ProcessMouseButtonUp(0,0);
            left=pressed;
        }
        return redraw;
    };
    context->ProcessMouseMove(pointer_x,pointer_y,0);
    frame();bmo_ui_state.phase=2;log("BMO UI READY\n");
#ifdef BMO_USB_DUAL
    bool transport_lost=false;
#endif
    for(;;) {
        bool dirty=false,closing=false;
        for(int pending=0;pending<64;++pending) {
            unsigned scan=256;
#ifdef BMO_USB_INPUT
            auto usb=bmo_usb_event();
            if(usb==256) {
                auto raw=doom_invoke(3,3,5,0);
                uint32_t admitted=1;
#ifdef BMO_USB_DUAL
                const auto metadata=doom_invoke(3,3,20,0);
                const auto kind=uint32_t(metadata);
                if(kind==2 && mouse_format_ready) {
                    const auto motion=bmo_mouse_decode(raw,uint32_t(metadata>>32));
                    if(motion) {
                        dirty|=mouse_input(int(int16_t(motion>>8)),int(int16_t(motion>>24)),unsigned(motion&7));
                        bmo_ui_usb_mouse_reports=bmo_ui_usb_mouse_reports+1;
                        bmo_ui_usb_reports=bmo_ui_usb_reports+1;
                        continue;
                    }
                }
                if(kind==1) {
                    admitted=bmo_usb_report_kind(raw,1);
                    if(admitted==0)bmo_ui_usb_keyboard_reports=bmo_ui_usb_keyboard_reports+1;
                }
#else
                if(raw!=256 && raw!=257) admitted=bmo_usb_report(raw);
#endif
                if(admitted==0) {
                    bmo_ui_usb_reports=bmo_ui_usb_reports+1;usb=bmo_usb_event();
                }
#ifdef BMO_USB_DUAL
                if(!transport_lost && doom_invoke(3,3,18,0)!=1) {
                    transport_lost=true;bmo_usb_disconnect();mouse_input(0,0,0);dirty=true;
                }
#endif
            }
            if(usb&(uint64_t(1)<<63)) {
                dirty|=mouse_input(int(int8_t(usb>>8)),int(int8_t(usb>>16)),unsigned(usb&7));
                continue;
            }
            if(usb!=256)scan=unsigned(usb);
#endif
            if(scan==256) {
                scan=doom_invoke(2,2,0,0);
                // Tests cannot satisfy USB input through the PS/2 fallback.
#ifdef BMO_USB_INPUT
#ifdef BMO_USB_DUAL
                if(scan!=256)continue;
#elif defined(BMO_USB_MOUSE)
                if(scan!=256 && (scan&512))continue;
#else
                if(scan!=256 && !(scan&512))continue;
#endif
#endif
            }
            if(scan==256)break;
            if(scan&512) {
                unsigned byte=scan&255;
                if(!packet_index) {if((byte&8) && byte!=0xfa){flags=byte;packet_index=1;}}
                else if(packet_index==1) {dx=byte;packet_index=2;}
                else {
                    packet_index=0;if(flags&0xc0)continue;
                    dirty|=mouse_input(int(dx)-int(flags&16)*16,-int(byte)+int(flags&32)*8,flags&7);
                }
            } else {
#ifdef BMO_USB_DUAL
                if(scan==0x58) {doom_invoke(3,3,19,0);bmo_usb_disconnect();mouse_input(0,0,0);transport_lost=true;dirty=true;continue;}
#endif
#ifdef BMO_DESKTOP_UI
                auto route=bmo_director_key(scan);
                if(route&1){dirty|=bool(route&2);continue;}
                if(scan==0x3b){bmo_director_open();dirty=true;}
#endif
                if(scan==0x1c
#ifdef BMO_DESKTOP_UI
                   && (bmo_director_state()>>8)
#endif
                  ) {button->Click();dirty=true;}
#ifndef BMO_DESKTOP_UI
                if(scan==0x01) {closing=true;break;}
#endif
            }
        }
        if(closing)break;
        if(dirty) frame();
        else if(drawn_x!=pointer_x || drawn_y!=pointer_y) {
#ifdef BMO_USB_DUAL
            const auto old_position=unsigned(drawn_x)|(unsigned(drawn_y)<<16);
#endif
            for(int y=0;y<17 && drawn_y+y<800;++y)
                for(int x=0;x<12 && drawn_x+x<1280;++x)
                    bmo_ui_pixels[(drawn_y+y)*1280+drawn_x+x]=under_pointer[y][x];
            draw_pointer();
#ifdef BMO_USB_DUAL
            const auto new_position=unsigned(drawn_x)|(unsigned(drawn_y)<<16);
            if(doom_invoke(1,10,(uintptr_t)bmo_ui_pixels,old_position)!=0 ||
                doom_invoke(1,10,(uintptr_t)bmo_ui_pixels,new_position)!=0)
                present();
#else
            present();
#endif
        }
        register unsigned long service __asm__("rax")=1;
        unsigned long cap=2,op=1,duration=1;
        __asm__ volatile("syscall":"+a"(service),"+D"(cap),"+S"(op),"+d"(duration)::"rcx","r11","r8","r9","r10","memory");
    }
    doc->Close();Rml::Shutdown();
    check(renderer.geometries.empty() && renderer.textures.empty() && files.open_count==0,"shutdown resources");
    bmo_ui_state.phase=4;log("BMO UI CLOSED\n");
    for(;;)__asm__ volatile("pause");
}
