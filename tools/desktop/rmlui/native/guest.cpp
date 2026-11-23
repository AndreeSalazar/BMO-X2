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
#ifdef BMO_FULL_HD
uint32_t bmo_ui_pixels[1920*1080];
#else
uint32_t bmo_ui_pixels[1280*800];
#endif
#ifdef BMO_DESKTOP_UI
void bmo_director_init();uint64_t bmo_director_open();uint64_t bmo_director_state();uint32_t bmo_director_key(uint32_t);
uint32_t bmo_director_locks();
volatile uint64_t bmo_ui_director;
volatile uint64_t bmo_ui_keyboard_focus;
#ifdef BMO_MSVC_PANEL
uint64_t bmo_director_open_msvc();
__attribute__((ms_abi)) unsigned bmo_msvc_panel(unsigned*, unsigned);
volatile uint64_t bmo_ui_msvc_draws;
#endif
#endif
#ifdef BMO_USB_INPUT
void bmo_usb_init(uint32_t);uint32_t bmo_usb_report(uint64_t);uint64_t bmo_usb_event();
volatile uint64_t bmo_ui_usb_reports;
#ifdef BMO_USB_DUAL
uint32_t bmo_usb_report_kind(uint64_t,uint32_t);uint32_t bmo_usb_disconnect();
uint32_t bmo_mouse_format(const uint8_t*,size_t);uint64_t bmo_mouse_decode(uint64_t,uint32_t);
volatile uint64_t bmo_ui_usb_keyboard_reports,bmo_ui_usb_mouse_reports;
volatile uint64_t bmo_ui_mouse_edges[4];
#endif
#endif
}
namespace BmoUi {[[noreturn]] void native_failure(const char* s) {bmo_native_fail(s);}}
static void log(const char* s) {while(*s)doom_invoke(5,7,(unsigned char)*s++,0);}
#ifdef BMO_DMA_CENSUS
static void check(bool ok,const char* error);
#ifdef BMO_STORAGE_STATE
static void read_storage_state(Rml::String& page) {
    constexpr unsigned system=26, start=256;
    const auto header=doom_invoke(3,3,system,start);
    const unsigned stored=header,total=header>>32;
    check(stored<=2 && stored<=total,"storage snapshot bounds");
    check(doom_invoke(3,3,system,start+stored*6+1)==257,"storage snapshot rejection");
    char line[200];
    snprintf(line,sizeof(line),"STORAGE_COUNT=%08X %08X\n",stored,total);
    log(line);
    page="<h2>Almacenamiento al salir de UEFI</h2><p>F2 cerrar / F3 volver al inventario PCI</p>";
    if(total==~0u)page+="<p>Inventario UEFI no disponible.</p>";
    else {
        snprintf(line,sizeof(line),"<p>Controladores AHCI y NVMe registrados %u de %u.</p>",stored,total);
        page+=line;
    }
    bool handoff_attempted=false;
    for(unsigned i=0;i<stored;++i) {
        uint64_t word[6];
        for(unsigned j=0;j<6;++j)word[j]=doom_invoke(3,3,system,start+1+i*6+j);
        const unsigned bdf=word[0]&0xffff, before=(word[0]>>16)&0xffff, kind=word[0]>>32;
        const unsigned after=(word[3]>>32)&0xffff, status=word[3]>>48;
        const unsigned a=word[4], b=word[4]>>32, engines=word[5], pending=word[5]>>32;
        snprintf(line,sizeof(line),"STORAGE_ROW=%04X %06X %04X %04X %u %08X %08X %08X %08X\n",
                 bdf,kind,before,after,status,a,b,engines,pending);
        log(line);
        const bool ahci=kind==0x010601;
        snprintf(line,sizeof(line),"<p><strong>%s %02X:%02X.%u</strong> &nbsp; PCI antes %04X / despues %04X</p>",
                 ahci?"SATA AHCI":"NVMe",bdf>>8,(bdf>>3)&31,bdf&7,before,after);
        page+=line;
        if(status==3 || status==4) {
            handoff_attempted=true;
            page+=status==3?"<p>Parada confirmada y bus mastering retirado.</p>":
                            "<p>Parada incompleta. Reservas DMA retenidas.</p>";
            continue;
        }
        if(status!=2) {
            page+=status==1?"<p>BAR UEFI identificado. Estado MMIO sin confirmar.</p>":"<p>BAR UEFI no validado.</p>";
            continue;
        }
        if(ahci) {
            snprintf(line,sizeof(line),"<p>GHC %08X / PI %08X</p><p>Motores %08X / Comandos pendientes %08X</p>",
                     a,b,engines,pending);
        } else {
            snprintf(line,sizeof(line),"<p>CC %08X / CSTS %08X &nbsp; EN %u / RDY %u / CFS %u</p>",
                     a,b,a&1,b&1,(b>>1)&1);
        }
        page+=line;
    }
    if(!handoff_attempted)page+="<p>Lectura de registros. La traduccion DMA y los discos conservan su estado.</p>";
}
#endif
#ifdef BMO_RTX_LAB_PANEL
#include "rtx_lab.inc"
#endif
static unsigned read_dma_inventory(Rml::String* pages) {
    constexpr unsigned selector=26;
    constexpr unsigned per_page=16;
    const auto header=doom_invoke(3,3,selector,0);
    const unsigned stored=header&0xffff, xhci=(header>>16)&0xffff, total=header>>32;
    check(stored<=64 && stored<=total,"PCI DMA inventory bounds");
    check(doom_invoke(3,3,selector,stored*2+1)==257,"PCI DMA inventory rejection");
    char line[144];
    snprintf(line,sizeof(line),"DMA_CENSUS=%08X %04X %04X\n",total,xhci,stored);
    log(line);
    const unsigned pci_pages=std::max(1u,(stored+per_page-1)/per_page);
    unsigned page_count=pci_pages;
#ifdef BMO_STORAGE_STATE
    read_storage_state(pages[page_count++]);
#endif
    for(unsigned i=0;i<pci_pages;++i) {
        snprintf(line,sizeof(line),"<h2>DMA habilitado en PCI</h2><p>Funciones %u de %u / xHCI %04X / Pagina %u de %u</p>",
                 stored,total,xhci,i+1,page_count);
        pages[i]=line;
        pages[i]+=page_count>1?"<p>F2 cerrar / F3 siguiente</p>":"<p>F2 cerrar</p>";
        pages[i]+="<p>BDF &nbsp;&nbsp;&nbsp; Dispositivo &nbsp;&nbsp;&nbsp; Clase &nbsp;&nbsp;&nbsp; Comando</p>";
    }
    for(unsigned i=0;i<stored;++i) {
        const auto entry=doom_invoke(3,3,selector,2*i+1);
        const unsigned bdf=entry&0xffff, control=(entry>>16)&0xffff;
        const unsigned ids=entry>>32, kind=doom_invoke(3,3,selector,2*i+2);
        snprintf(line,sizeof(line),"DMA_REQ=%04X %04X %08X %06X\n",bdf,control,ids,kind);
        log(line);
        snprintf(line,sizeof(line),"<p>%02X:%02X.%u &nbsp;&nbsp;&nbsp; %04X:%04X &nbsp;&nbsp;&nbsp; %06X &nbsp;&nbsp;&nbsp; %04X</p>",
                 bdf>>8,(bdf>>3)&31,bdf&7,ids&0xffff,ids>>16,kind,control);
        pages[i/per_page]+=line;
    }
    return page_count;
}
#endif
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
    uint64_t (*open)();
public:
    explicit Launcher(uint64_t (*action)()):open(action) {}
    void ProcessEvent(Rml::Event& e) override {if(e.GetType()=="click")open();}
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
    int desktop_width=1280,desktop_height=800;
    int pointer_y=400;
#ifdef BMO_DESKTOP_UI
    int status_rows=80;
#endif
#ifdef BMO_FULL_HD
    const auto geometry=doom_invoke(3,3,26,512);
    const bool full_hd=uint32_t(geometry)==1920 && geometry>>32==1080;
    if(full_hd) {
        desktop_width=1920;desktop_height=1080;
        pointer_y=600;status_rows=120;
        check(doom_invoke(1,9,0x41000000-1920*1080*4+4,0)==257 &&
              doom_invoke(1,10,0x41000000-1920*1080*4+4,0)==257,"1080p presentation boundary");
    }
    log(full_hd?"GOP_FULL_HD=1\n":"GOP_FULL_HD=0\n");
#endif
    auto context=Rml::CreateContext("BMO-X2 native",{desktop_width,desktop_height});check(context,"context");
    renderer.width=desktop_width;renderer.height=desktop_height;
    const size_t frame_pixels=size_t(desktop_width)*desktop_height;
#ifdef BMO_FULL_HD
    if(full_hd)context->SetDensityIndependentPixelRatio(1.5f);
#endif
    auto doc=context->LoadDocument("main.rml");check(doc && !files.denied,"document");
    log("BMO UI DOCUMENT\n");
    doc->SetClass("reduced-motion",true);
    doc->SetClass("native-pointer",true);
#ifdef BMO_FULL_HD
    if(full_hd) {
        doc->SetClass("full-hd",true);
        doc->GetElementById("host-badge")->SetInnerRML("CPU / 1080p nativo");
    }
#endif
    doc->SetClass("arrived",true);doc->SetClass("intro-ready",true);
    auto button=doc->GetElementById("activate");check(button,"button");button->AddEventListener("click",&action);
    doc->Show();
#ifdef BMO_AMDVI_POST
    // Request the one-time supervisor snapshot before starting USB.
    constexpr unsigned amdvi_diagnostic=25;
    const auto amdvi_snapshot=doom_invoke(3,3,amdvi_diagnostic,0);
    const auto amdvi_status=static_cast<unsigned long>(uint32_t(amdvi_snapshot));
    char amdvi_line[180];
    auto* amdvi_panel=doc->GetElementById("amdvi-post");
    check(amdvi_panel,"AMD-Vi report");
#ifdef BMO_RTX_LAB_PANEL
    bool translation=false;
#endif
    if(amdvi_status==4) {
        unsigned long words[5];
        for(unsigned i=0;i<5;++i)words[i]=doom_invoke(3,3,amdvi_diagnostic,i+1);
#ifdef BMO_RTX_LAB_PANEL
        translation=(words[0]&1)!=0;
#endif
        snprintf(amdvi_line,sizeof(amdvi_line),
                 "AMDVI_POST=04 %016lX %016lX %016lX %016lX %016lX\n",
                 words[0],words[1],words[2],words[3],words[4]);
        log(amdvi_line);
        snprintf(amdvi_line,sizeof(amdvi_line),
                 "AMD-Vi Ring 0 / CTRL %016lX / TABLA %016lX<br/>"
                 "CMD %016lX / EVT %016lX / ESTADO %016lX",
                 words[0],words[1],words[2],words[3],words[4]);
    } else {
        snprintf(amdvi_line,sizeof(amdvi_line),"AMDVI_POST=%02lX\n",amdvi_status);
        log(amdvi_line);
        snprintf(amdvi_line,sizeof(amdvi_line),"AMD-Vi Ring 0 / captura %02lX",amdvi_status);
    }
    Rml::String hardware_report=amdvi_line;
#ifdef BMO_AMDVI_MMIO_REPORT
    const auto mmio_result=static_cast<unsigned>(amdvi_snapshot>>32);
    const char* mmio_message;
    switch(mmio_result) {
        case 0: mmio_message="omitida por requisitos de la placa o del firmware"; break;
        case 0x100: mmio_message="rechazada antes de publicar"; break;
        case 0x101: mmio_message="bases escritas y restauradas"; break;
        case 0x102: mmio_message="lectura distinta, restauracion confirmada"; break;
        default: mmio_message="restauracion sin confirmar"; break;
    }
    snprintf(amdvi_line,sizeof(amdvi_line),"AMDVI_MMIO_TEST=%03X\n",mmio_result);
    log(amdvi_line);
    snprintf(amdvi_line,sizeof(amdvi_line),"Prueba AMD-Vi %03X / %s",
             mmio_result,mmio_message);
    hardware_report+="<br/>";
    hardware_report+=amdvi_line;
#endif
    const auto gsp=doom_invoke(3,3,amdvi_diagnostic,6);
    const unsigned file_status=unsigned(gsp);
    const unsigned dma_status=unsigned(gsp>>32);
    if(file_status>=1 && file_status<=5) {
        snprintf(amdvi_line,sizeof(amdvi_line),"GSP_PREP=%u %u\n",file_status,dma_status);
        log(amdvi_line);
        hardware_report+="<br/>";
        if(dma_status==7)hardware_report+="NVIDIA / FWSEC listo para cargar";
        else if(dma_status==6)hardware_report+="NVIDIA / WPR preparada / DMA pendiente";
        else if(dma_status==5)hardware_report+="NVIDIA / LIBOS y colas GSP listos / DMA pendiente";
        else if(dma_status==4)hardware_report+="NVIDIA / Colas GSP listas / DMA pendiente";
        else if(dma_status==3)hardware_report+="NVIDIA / Radix3 listo / DMA pendiente";
        else if(file_status==5)hardware_report+="NVIDIA / No se preparo Radix3";
        else hardware_report+="NVIDIA / Firmware no disponible";
    }
#ifdef BMO_AMDVI_DTE_REPORT
    const auto dte=doom_invoke(3,3,amdvi_diagnostic,7);
    const auto dte_status=unsigned(dte);
    const auto zero_qwords=unsigned(dte>>32);
    snprintf(amdvi_line,sizeof(amdvi_line),"AMDVI_DTE_POST=%02X %08X\n",dte_status,zero_qwords);
    log(amdvi_line);
    const char* dte_message;
    switch(dte_status) {
        case 0: dte_message="lectura no iniciada"; break;
        case 1: dte_message="2 MiB leidos, alias revocado"; break;
        case 2: dte_message="reserva UEFI no disponible"; break;
        case 3: dte_message="rango fuera del descriptor EFI"; break;
        case 4: dte_message="lectura distinta de cero"; break;
        case 5: dte_message="revocacion del alias no verificada"; break;
        default: dte_message="estado desconocido"; break;
    }
    snprintf(amdvi_line,sizeof(amdvi_line),"AMDVI_DTE_POST=%02X %08X / %s",
             dte_status,zero_qwords,dte_message);
    hardware_report+="<br/>";
    hardware_report+=amdvi_line;
#endif
    amdvi_panel->SetInnerRML(hardware_report);
#endif
#ifdef BMO_DESKTOP_UI
    bmo_director_init();bmo_director_open();Launcher launcher(bmo_director_open);
    doc->GetElementById("open-app")->AddEventListener("click",&launcher);
#ifdef BMO_MSVC_PANEL
    Launcher msvc_launcher(bmo_director_open_msvc);
    doc->GetElementById("open-msvc")->AddEventListener("click",&msvc_launcher);
    auto* msvc_panel=doc->GetElementById("msvc-panel");
    auto* msvc_surface=doc->GetElementById("msvc-surface");
    static unsigned msvc_pixels[160*100];
#endif
    auto sync_locks=[&]() {
        const unsigned locks=bmo_director_locks();
        doc->GetElementById("lock-num")->SetClass("on",locks&1);
        doc->GetElementById("lock-caps")->SetClass("on",locks&2);
        doc->GetElementById("lock-scroll")->SetClass("on",locks&4);
    };
    auto sync_policy=[&]() {
        auto policy=bmo_director_state();char label[128];
        sync_locks();
        for(unsigned w=1;w<=4;++w) {
            char id[]="space-1";id[6]=char('0'+w);
            doc->GetElementById(id)->SetClass("on",(policy&255)==w);
        }
        snprintf(label,sizeof(label),"Espacio %u / %s",unsigned(policy&255),(policy>>8)?"ULTRA-J activo":"Sin ventanas. Abre ULTRA-J.");
#ifdef BMO_USB_DUAL
        auto usb=doom_invoke(3,3,21,0);
        snprintf(label,sizeof(label),"Espacio %u / USB %s / K:%s M:%s / fase %u CC %u",unsigned(policy&255),
            (usb>>24)&1?"ON":"OFF",usb&0x100?"OK":"espera",usb&0x200?"OK":"espera",unsigned(usb&255),unsigned((usb>>16)&255));
#endif
        doc->GetElementById("desktop-status")->SetInnerRML(label);
        doc->GetElementById("workspace")->SetProperty("display",(policy>>8)==1?"flex":"none");
#ifdef BMO_MSVC_PANEL
        msvc_panel->SetProperty("display",(policy>>8)==2?"block":"none");
#endif
    };
#endif
    int pointer_x=desktop_width/2,packet_index=0;
    unsigned flags=0,dx=0,held_buttons=0;
    auto cursor_color=[&]() -> uint32_t {
        for(auto* element=context->GetHoverElement();element;element=element->GetParentNode())
            if(element->GetTagName()=="button" || element->GetId()=="open-app")
                return held_buttons&1?0x43bbaa:0xa2f4e6;
        return 0xf4f8ff;
    };
    static constexpr char pointer[][13]={
        "#           ", "##          ", "#.#         ", "#..#        ",
        "#...#       ", "#....#      ", "#.....#     ", "#......#    ",
        "#.......#   ", "#........#  ", "#.....##### ", "#..#..#     ",
        "#.# #..#    ", "##  #..#    ", "#    #..#   ", "     #..#   ",
        "      ##    ",
    };
    uint32_t under_pointer[17][12];
    int drawn_x=pointer_x,drawn_y=pointer_y;
    uint32_t drawn_color=0;
    auto draw_pointer=[&]() {
        drawn_x=pointer_x;drawn_y=pointer_y;
        drawn_color=cursor_color();
        for(int y=0;y<17 && drawn_y+y<desktop_height;++y)
            for(int x=0;x<12 && drawn_x+x<desktop_width;++x) {
                auto& pixel=bmo_ui_pixels[(drawn_y+y)*desktop_width+drawn_x+x];
                under_pointer[y][x]=pixel;
                if(pointer[y][x]!=' ')pixel=pointer[y][x]=='#'?0x0b1019:drawn_color;
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
        renderer.pixels=bmo_ui_pixels;renderer.pixel_count=frame_pixels;
        renderer.frame(context);renderer.pixels=nullptr;renderer.pixel_count=0;
#ifdef BMO_MSVC_PANEL
        if((bmo_director_state()>>8)==2) {
            const auto position=msvc_surface->GetAbsoluteOffset(Rml::BoxArea::Content);
            const int x=int(position.x), y=int(position.y);
            check(x>=0 && y>=0 && x+480<=1280 && y+300<=800,"MSVC layout");
            check(bmo_msvc_panel(msvc_pixels,160*100)==1,"MSVC draw");
            for(int row=0;row<300;++row)
                for(int col=0;col<480;++col)
                    bmo_ui_pixels[(y+row)*1280+x+col]=msvc_pixels[(row/3)*160+col/3];
            bmo_ui_msvc_draws=bmo_ui_msvc_draws+1;
        }
#endif
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
#ifdef BMO_DMA_CENSUS
    auto* dma_panel=doc->GetElementById("dma-census");
    check(dma_panel,"PCI DMA panel");
#ifdef BMO_RTX_LAB_PANEL
    auto* rtx_panel=doc->GetElementById("rtx-lab");
    check(rtx_panel,"RTX lab panel");
    rtx_panel->SetInnerRML(rtx_lab_report(amdvi_status,translation,file_status,dma_status));
    bool rtx_panel_open=false;
#endif
#ifdef BMO_STORAGE_STATE
    Rml::String dma_pages[5];
#else
    Rml::String dma_pages[4];
#endif
    const auto dma_page_count=read_dma_inventory(dma_pages);
    unsigned dma_page=0;
    bool dma_panel_open=false;
#endif
    bool motion_pending=false;
    auto flush_motion=[&]() {
        if(!motion_pending)return;
        context->ProcessMouseMove(pointer_x,pointer_y,0);
        motion_pending=false;
    };
    auto mouse_input=[&](int dx,int dy,unsigned buttons,unsigned mask=7,int wheel=0) {
        if(dx || dy) {
            const int x=std::clamp(pointer_x+dx,0,desktop_width-1);
            const int y=std::clamp(pointer_y+dy,0,desktop_height-1);
            motion_pending|=x!=pointer_x || y!=pointer_y;
            pointer_x=x;pointer_y=y;
        }
        const unsigned next=(held_buttons&~mask) | buttons;
        const unsigned changed=held_buttons^next;
        // Keep drag and button/scroll ordering. Idle motion can share one hit test.
        if(held_buttons || changed || wheel)flush_motion();
        if(!changed && !wheel)return false;
        auto accepted=bmo_ui_state.accepted;
#ifdef BMO_DESKTOP_UI
        auto policy=bmo_director_state();
#endif
        held_buttons=next;
        for(int index=0;index<3;++index) {
            const unsigned bit=1u<<index;
            if(!(changed&bit))continue;
            if(next&bit)context->ProcessMouseButtonDown(index,0);
            else context->ProcessMouseButtonUp(index,0);
#ifdef BMO_USB_DUAL
            bmo_ui_mouse_edges[index]=bmo_ui_mouse_edges[index]+1;
#endif
        }
        bool redraw=false;
        if(wheel) {
            redraw=!context->ProcessMouseWheel(Rml::Vector2f{0.f,-float(wheel)},0);
#ifdef BMO_USB_DUAL
            bmo_ui_mouse_edges[3]=bmo_ui_mouse_edges[3]+1;
#endif
        }
#ifdef BMO_DESKTOP_UI
        redraw|=policy!=bmo_director_state();
#endif
        redraw|=accepted!=bmo_ui_state.accepted;
        return redraw;
    };
    context->ProcessMouseMove(pointer_x,pointer_y,0);
    frame();bmo_ui_state.phase=2;log("BMO UI READY\n");
#ifdef BMO_USB_DUAL
    bool transport_lost=false;
    unsigned queued_leds=8;
#endif
    for(;;) {
        bool dirty=false,closing=false;
#ifdef BMO_DESKTOP_UI
        bool focus_window=false,locks_dirty=false;
#endif
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
                        dirty|=mouse_input(int(int16_t(motion>>8)),int(int16_t(motion>>24)),
                            unsigned(motion&7),unsigned((motion>>3)&7),int(int16_t(motion>>40)));
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
                flush_motion();
#ifdef BMO_USB_DUAL
                if(scan==0x58) {doom_invoke(3,3,19,0);bmo_usb_disconnect();mouse_input(0,0,0);transport_lost=true;dirty=true;continue;}
#endif
#ifdef BMO_DMA_CENSUS
#ifdef BMO_RTX_LAB_PANEL
                if(scan==0x3e) {
                    rtx_panel_open=!rtx_panel_open;
                    if(rtx_panel_open && dma_panel_open) {
                        dma_panel->SetProperty("display","none");
                        dma_panel_open=false;
                        log("DMA_PANEL=OFF\n");
                    }
                    rtx_panel->SetProperty("display",rtx_panel_open?"block":"none");
                    log(rtx_panel_open?"RTX_LAB=ON\n":"RTX_LAB=OFF\n");
                    dirty=true;
                    continue;
                }
#endif
                if(scan==0x3c) {
#ifdef BMO_RTX_LAB_PANEL
                    if(rtx_panel_open) {
                        rtx_panel->SetProperty("display","none");
                        rtx_panel_open=false;
                        log("RTX_LAB=OFF\n");
                    }
#endif
                    dma_panel_open=!dma_panel_open;
                    if(dma_panel_open)dma_panel->SetInnerRML(dma_pages[dma_page]);
                    dma_panel->SetProperty("display",dma_panel_open?"block":"none");
                    log(dma_panel_open?"DMA_PANEL=ON\n":"DMA_PANEL=OFF\n");
                    dirty=true;
                    continue;
                }
                if(scan==0x3d && dma_panel_open && dma_page_count>1) {
                    dma_page=(dma_page+1)%dma_page_count;
                    dma_panel->SetInnerRML(dma_pages[dma_page]);
#ifdef BMO_STORAGE_STATE
                    if(dma_page+1==dma_page_count)log("STORAGE_PANEL=ON\n");
#endif
                    dirty=true;
                    continue;
                }
#endif
#ifdef BMO_DESKTOP_UI
                auto route=bmo_director_key(scan);
                if(route&1){dirty|=bool(route&2);focus_window|=bool(route&4);locks_dirty|=bool(route&8);continue;}
                if(scan==0x3b){bmo_director_open();dirty=true;}
#ifdef BMO_MSVC_PANEL
                if(scan==0x3d){bmo_director_open_msvc();dirty=true;}
#endif
#endif
                if(scan==0x1c
#ifdef BMO_DESKTOP_UI
                   && (bmo_director_state()>>8)==1
#endif
                  ) {button->Click();dirty=true;}
#ifndef BMO_DESKTOP_UI
                if(scan==0x01) {closing=true;break;}
#endif
            }
        }
        if(closing)break;
        flush_motion();
#ifdef BMO_USB_DUAL
        const unsigned locks=bmo_director_locks();
        if(!transport_lost && queued_leds!=locks && doom_invoke(3,3,22,0x200|locks)!=256)
            queued_leds=locks;
#endif
        if(dirty) frame();
        else {
#ifdef BMO_DESKTOP_UI
            const bool redraw_locks=locks_dirty;
#else
            const bool redraw_locks=false;
#endif
            const bool move_cursor=drawn_x!=pointer_x || drawn_y!=pointer_y || drawn_color!=cursor_color();
            if(redraw_locks || move_cursor) {
#ifdef BMO_DESKTOP_UI
            const auto old_position=unsigned(drawn_x)|(unsigned(drawn_y)<<16);
#endif
            for(int y=0;y<17 && drawn_y+y<desktop_height;++y)
                for(int x=0;x<12 && drawn_x+x<desktop_width;++x)
                    bmo_ui_pixels[(drawn_y+y)*desktop_width+drawn_x+x]=under_pointer[y][x];
#ifdef BMO_DESKTOP_UI
            if(redraw_locks) {
                sync_locks();
                renderer.pixels=bmo_ui_pixels;renderer.pixel_count=frame_pixels;
                renderer.frame(context,0,status_rows);
                renderer.pixels=nullptr;renderer.pixel_count=0;
            }
#endif
            draw_pointer();
#ifdef BMO_DESKTOP_UI
            const auto new_position=unsigned(drawn_x)|(unsigned(drawn_y)<<16);
            if((redraw_locks && doom_invoke(1,10,(uintptr_t)bmo_ui_pixels,0x80000000)!=0) ||
                (move_cursor && (doom_invoke(1,10,(uintptr_t)bmo_ui_pixels,old_position)!=0 ||
                 doom_invoke(1,10,(uintptr_t)bmo_ui_pixels,new_position)!=0)))
                present();
#else
            present();
#endif
            }
        }
#ifdef BMO_DESKTOP_UI
        if(focus_window && (bmo_director_state()>>8)==1 && button->Focus())
            bmo_ui_keyboard_focus=bmo_ui_keyboard_focus+1;
#endif
        register unsigned long service __asm__("rax")=1;
        unsigned long cap=2,op=1,duration=1;
        __asm__ volatile("syscall":"+a"(service),"+D"(cap),"+S"(op),"+d"(duration)::"rcx","r11","r8","r9","r10","memory");
    }
    doc->Close();Rml::Shutdown();
    check(renderer.geometries.empty() && renderer.textures.empty() && files.open_count==0,"shutdown resources");
    bmo_ui_state.phase=4;log("BMO UI CLOSED\n");
    for(;;)__asm__ volatile("pause");
}
