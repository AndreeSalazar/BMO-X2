// Real RmlUi C++ engine adapter. No Windows API, disk I/O, wall clock or image writer.
// This source is platform-neutral; the linked C++/font runtime is not freestanding yet.
#include "engine.h"
#include "renderer.h"
#include "memory_files.h"
#include "owner.h"
#include <cmath>
#include <memory>
#include <cstring>

namespace {
using namespace BmoUi;
char error_text[2048]{};
bool busy=false;
void error(const char* text) {
    size_t i=0; if(text) for(;i<sizeof(error_text)-1 && text[i];++i) error_text[i]=text[i];
    error_text[i]=0;
}
struct Busy { Busy(){busy=true;} ~Busy(){busy=false;} };
class Clock final : public Rml::SystemInterface {
public:
    uint64_t ns=0;
    uint64_t warnings=0;
    double GetElapsedTime() override { return double(ns)/1e9; }
    bool LogMessage(Rml::Log::Type type,const Rml::String& text) override {
        if(type==Rml::Log::LT_ERROR || type==Rml::Log::LT_WARNING) {++warnings;error(text.c_str());}
        return true;
    }
};
class Action final : public Rml::EventListener {
public:
    BmoUiAction callback=nullptr; uint64_t calls=0,accepted=0;
    bool enter_down=false;
    void ProcessEvent(Rml::Event& event) override {
        if(event.GetType()=="blur") {enter_down=false;return;}
        if((event.GetType()=="keydown" || event.GetType()=="keyup") &&
            event.GetParameter<int>("key_identifier",0)==int(Rml::Input::KI_RETURN)) {
            const bool activate=event.GetType()=="keyup" && enter_down;
            enter_down=event.GetType()=="keydown";
            event.StopImmediatePropagation();
            if(activate) event.GetCurrentElement()->Click();
            return;
        }
        if(event.GetType()!="click") return;
        ++calls;
        const bool ok=callback && callback()==1;
        accepted+=ok;
        auto doc=event.GetCurrentElement()->GetOwnerDocument();
        doc->GetElementById("result")->SetInnerRML(ok?"ULTRA-J atendio el evento. Region cerrada.":"El runtime rechazo la accion.");
        doc->GetElementById("state")->SetInnerRML(ok?"Accion verificada":"Accion rechazada");
        doc->GetElementById("state")->SetClass("ready",ok);
    }
};
class Arrival final : public Rml::EventListener {
    void ProcessEvent(Rml::Event& event) override {
        if(event.GetType()=="animationend") {
            auto item=event.GetCurrentElement();
            item->GetOwnerDocument()->SetClass(item->GetId()=="intro"?"intro-ready":"arrived",true);
        }
    }
};
struct Session {
    Lease lease;
    Renderer renderer; Clock clock; MemoryFiles files; Action action; Arrival arrival;
    Rml::Context* context=nullptr;
    Rml::ElementDocument* document=nullptr;
    bool initialized=false,poisoned=false;
    bool shutdown() {
        if(!lease) return true;
        if(initialized) Rml::Shutdown();
        initialized=false;
        Rml::SetRenderInterface(nullptr); Rml::SetSystemInterface(nullptr); Rml::SetFileInterface(nullptr);
        return renderer.geometries.empty() && renderer.textures.empty() && files.open_count==0;
    }
    ~Session() {shutdown();}
};
std::unique_ptr<Session> session;
int failed(const std::exception& e) { error(e.what()); if(session) session->poisoned=true; return UiEngine; }
}

int bmo_ui_open(const BmoUiBlob* blobs,size_t count,BmoUiAction callback) {
    if(busy || session || rmlui_owned) return UiState;
    Busy guard; error("");
    try {
        auto next=std::make_unique<Session>();
        if(!callback || !next->files.assign(blobs,count)) {error("resource table rejected");return UiResources;}
        next->action.callback=callback;
        Rml::SetRenderInterface(&next->renderer); Rml::SetSystemInterface(&next->clock); Rml::SetFileInterface(&next->files);
        if(!Rml::Initialise()) {error("engine initialization");return UiEngine;}
        next->initialized=true;
        if(!Rml::LoadFontFace("LatoLatin-Regular.ttf") || !Rml::LoadFontFace("LatoLatin-Bold.ttf")) {error("font resource");return UiResources;}
        next->context=Rml::CreateContext("BMO-X2 memory",{W,H});
        if(!next->context) return UiEngine;
        next->document=next->context->LoadDocument("main.rml");
        if(!next->document || next->files.denied) {error("document resource");return UiResources;}
        auto button=next->document->GetElementById("activate");
        if(!button || !next->document->GetElementById("state") || !next->document->GetElementById("result")) return UiResources;
        for(const char* type:{"click","keydown","keyup","blur"}) button->AddEventListener(type,&next->action);
        next->document->Show();
        if(auto arrival=next->document->GetElementById("arrival")) arrival->AddEventListener("animationend",&next->arrival);
        if(auto intro=next->document->GetElementById("intro")) intro->AddEventListener("animationend",&next->arrival);
        // Resolve initial layout/animation before the caller presents its first frame.
        next->context->Update();
        if(next->files.denied) {error("deferred document resource");return UiResources;}
        if(next->clock.warnings) return UiResources;
        session=std::move(next); return UiOk;
    } catch(const std::exception& e) {return failed(e);}
}

int bmo_ui_frame(uint64_t ns,uint32_t* pixels,size_t length) {
    if(busy || !session || session->poisoned) return UiState;
    if(!pixels || length!=size_t(W)*H || reinterpret_cast<uintptr_t>(pixels)%alignof(uint32_t)) return UiArgument;
    if(ns<session->clock.ns) return UiTime;
    Busy guard;
    try {
        session->clock.ns=ns;
        session->renderer.pixels=pixels; session->renderer.pixel_count=length;
        // Settle event-driven classes (including animationend) before drawing.
        session->context->Update();
        session->renderer.frame(session->context);
        session->renderer.pixels=nullptr; session->renderer.pixel_count=0;
        if(session->clock.warnings) {session->poisoned=true;return UiEngine;}
        return UiOk;
    } catch(const std::exception& e) {
        session->renderer.pixels=nullptr; session->renderer.pixel_count=0;
        return failed(e);
    }
}

int bmo_ui_input(uint32_t kind,int32_t x,int32_t y) {
    if(busy || !session || session->poisoned) return UiState;
    if(kind>4 || x<0 || x>=W || y<0 || y>=H) return UiArgument;
    Busy guard;
    try {
        if(kind==0) session->context->ProcessMouseMove(x,y,0);
        else if(kind==1) session->context->ProcessMouseButtonDown(0,0);
        else if(kind==2) session->context->ProcessMouseButtonUp(0,0);
        else if(kind==3) session->context->ProcessKeyDown(Rml::Input::KI_RETURN,0);
        else session->context->ProcessKeyUp(Rml::Input::KI_RETURN,0);
        return UiOk;
    } catch(const std::exception& e) {return failed(e);}
}

int bmo_ui_box(const char* id,float* xywh) {
    if(busy || !session || session->poisoned) return UiState;
    if(!xywh || !resource_name(id)) return UiArgument;
    Busy guard;
    try {
    auto item=session->document->GetElementById(id);
    if(!item) return UiArgument;
    auto position=item->GetAbsoluteOffset(); auto size=item->GetBox().GetSize();
    xywh[0]=position.x; xywh[1]=position.y; xywh[2]=size.x; xywh[3]=size.y;
    return UiOk;
    } catch(const std::exception& e) {return failed(e);}
}

int bmo_ui_motion(uint32_t enabled) {
    if(busy || !session || session->poisoned) return UiState;
    if(enabled>1) return UiArgument;
    Busy guard;
    try {session->document->SetClass("reduced-motion",enabled==0);return UiOk;}
    catch(const std::exception& e) {return failed(e);}
}

int bmo_ui_next_delay_ms(uint32_t* delay) {
    if(busy || !session || session->poisoned) return UiState;
    if(!delay) return UiArgument;
    double seconds=session->context->GetNextUpdateDelay();
    *delay=std::isfinite(seconds)?uint32_t(std::clamp(std::ceil(seconds*1000.0),0.0,4294967294.0)):UINT32_MAX;
    return UiOk;
}

int bmo_ui_stats(BmoUiStats* stats) {
    if(busy || !session) return UiState;
    if(!stats) return UiArgument;
    auto& s=*session;
    *stats={s.clock.ns,s.renderer.triangles,s.renderer.geometry_bytes,s.renderer.texture_bytes,
        s.renderer.peak_geometry,s.renderer.peak_texture,s.files.open_count,s.files.denied,s.action.calls,s.action.accepted};
    return UiOk;
}
int bmo_ui_close() {
    if(busy || !session) return UiState;
    Busy guard;
    try {bool clean=session->shutdown();session.reset();return clean?UiOk:UiEngine;}
    catch(const std::exception& e) {return failed(e);}
}
const char* bmo_ui_error() { return error_text; }
