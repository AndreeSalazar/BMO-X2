// HOST Windows proof. RmlUi builds layout/geometry; this adapter rasterizes on CPU.
#include <RmlUi/Core.h>
#include "renderer.h"
#include "owner.h"
#include <windows.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

namespace {
using namespace BmoUi;
class PreviewRenderer final : public Renderer {
public:
    void save(const std::string& path) {
        BITMAPFILEHEADER file{}; BITMAPINFOHEADER info{};
        file.bfType=0x4d42; file.bfOffBits=sizeof(file)+sizeof(info); file.bfSize=file.bfOffBits+W*H*4;
        info.biSize=sizeof(info); info.biWidth=W; info.biHeight=-H; info.biPlanes=1; info.biBitCount=32; info.biCompression=BI_RGB;
        std::ofstream out(path,std::ios::binary); out.write(reinterpret_cast<char*>(&file),sizeof(file)); out.write(reinterpret_cast<char*>(&info),sizeof(info));
        out.write(reinterpret_cast<char*>(pixels),pixel_count*4); if(!out) throw std::runtime_error("image write");
    }
};
class System final : public Rml::SystemInterface {
    std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();
public:
    double GetElapsedTime() override { return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count(); }
    bool LogMessage(Rml::Log::Type, const Rml::String& message) override { OutputDebugStringA(message.c_str()); return true; }
};
using Action = int(__cdecl*)();
class Listener final : public Rml::EventListener {
public:
    Action action; int calls=0; bool passed=false;
    explicit Listener(Action value):action(value){}
    void ProcessEvent(Rml::Event& event) override {
        if(event.GetType() != "click") return;
        ++calls; passed=action && action()==1;
        auto doc=event.GetCurrentElement()->GetOwnerDocument();
        doc->GetElementById("result")->SetInnerRML(passed?"ULTRA-J atendio el evento. Region cerrada.":"El runtime rechazo la accion.");
        doc->GetElementById("state")->SetInnerRML(passed?"Accion verificada":"Accion rechazada");
        doc->GetElementById("state")->SetClass("ready",passed);
    }
};
}

extern "C" __declspec(dllexport) int bmo_rmlui_preview(const char* assets, const char* output, Action action) noexcept {
    BmoUi::Lease lease; if(!lease) return 1;
    bool initialized=false;
    PreviewRenderer renderer; std::vector<uint32_t> framebuffer; System system; Listener listener(action);
    try {
        framebuffer.resize(W * H); renderer.pixels=framebuffer.data(); renderer.pixel_count=framebuffer.size();
        Rml::SetRenderInterface(&renderer); Rml::SetSystemInterface(&system);
        if(!Rml::Initialise()) {
            Rml::SetRenderInterface(nullptr); Rml::SetSystemInterface(nullptr);
            return 2;
        }
        initialized=true;
        const std::string root=assets, target=output;
        if(!Rml::LoadFontFace(root+"/LatoLatin-Regular.ttf") || !Rml::LoadFontFace(root+"/LatoLatin-Bold.ttf")) throw std::runtime_error("font load");
        auto context=Rml::CreateContext("BMO-X2 HOST",{W,H});
        if(!context) throw std::runtime_error("context");
        auto doc=context->LoadDocument(root+"/main.rml");
        if(!doc) throw std::runtime_error("document");
        auto button=doc->GetElementById("activate"); if(!button) throw std::runtime_error("button");
        button->AddEventListener("click",&listener); doc->Show();
        auto begin=std::chrono::steady_clock::now(); renderer.frame(context); renderer.save(target+"/before.bmp");
        auto first=std::chrono::steady_clock::now();
        button->Click(); renderer.frame(context); renderer.save(target+"/after.bmp");
        auto last=std::chrono::steady_clock::now();
        bool passed=listener.passed && listener.calls==1;
        button->RemoveEventListener("click",&listener); doc->Close(); Rml::RemoveContext("BMO-X2 HOST");
        Rml::Shutdown(); initialized=false;
        std::ofstream stats(target+"/native.json");
        stats<<"{\"evidence\":\"HOST\",\"engine\":\"RmlUi 6.3\",\"renderer\":\"Rust no_std CPU\",\"callback_passed\":"<<(passed?"true":"false")
             <<",\"click_events\":"<<listener.calls<<",\"triangles_two_frames\":"<<renderer.triangles<<",\"framebuffer_bytes\":"<<W*H*4
             <<",\"peak_adapter_geometry_bytes\":"<<renderer.peak_geometry<<",\"peak_adapter_texture_bytes\":"<<renderer.peak_texture
             <<",\"first_frame_and_bmp_ms\":"<<std::chrono::duration<double,std::milli>(first-begin).count()
             <<",\"action_frame_and_bmp_ms\":"<<std::chrono::duration<double,std::milli>(last-first).count()
             <<",\"adapter_geometry_bytes_after_shutdown\":"<<renderer.geometry_bytes<<",\"adapter_texture_bytes_after_shutdown\":"<<renderer.texture_bytes<<"}\n";
        Rml::SetRenderInterface(nullptr); Rml::SetSystemInterface(nullptr);
        return passed && stats && renderer.geometries.empty() && renderer.textures.empty()?0:3;
    } catch(const std::exception& error) {
        if(initialized) Rml::Shutdown();
        Rml::SetRenderInterface(nullptr); Rml::SetSystemInterface(nullptr);
        std::ofstream(std::string(output)+"/error.txt") << error.what();
        return 4;
    } catch(...) {
        if(initialized) Rml::Shutdown();
        Rml::SetRenderInterface(nullptr); Rml::SetSystemInterface(nullptr);
        return 4;
    }
}
