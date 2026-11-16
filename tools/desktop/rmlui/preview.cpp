// HOST Windows proof. RmlUi builds layout/geometry; this adapter rasterizes on CPU.
#include <RmlUi/Core.h>
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
constexpr int W = 1280, H = 800;
struct Geometry { std::vector<Rml::Vertex> v; std::vector<int> i; };
struct Texture { int w, h; std::vector<Rml::byte> rgba; };
class Renderer final : public Rml::RenderInterface {
public:
    std::vector<uint32_t> pixels;
    size_t triangles = 0, peak_geometry = 0, peak_texture = 0, geometry_bytes = 0, texture_bytes = 0;
    std::unordered_set<Geometry*> geometries;
    std::unordered_set<Texture*> textures;
    bool clip = false;
    Rml::Rectanglei region = Rml::Rectanglei::FromPositionSize({0, 0}, {W, H});
    Rml::CompiledGeometryHandle CompileGeometry(Rml::Span<const Rml::Vertex> v, Rml::Span<const int> i) override {
        if (v.size() > 1000000 || i.size() > 3000000 || i.size() % 3) throw std::runtime_error("geometry bounds");
        auto g = new Geometry{{v.begin(), v.end()}, {i.begin(), i.end()}};
        for (int n : g->i) if (n < 0 || size_t(n) >= g->v.size()) { delete g; throw std::runtime_error("geometry index"); }
        geometry_bytes += g->v.size() * sizeof(Rml::Vertex) + g->i.size() * sizeof(int);
        peak_geometry = std::max(peak_geometry, geometry_bytes); geometries.insert(g);
        return reinterpret_cast<Rml::CompiledGeometryHandle>(g);
    }
    void ReleaseGeometry(Rml::CompiledGeometryHandle handle) override {
        auto g = reinterpret_cast<Geometry*>(handle);
        if (!geometries.erase(g)) throw std::runtime_error("unknown geometry");
        geometry_bytes -= g->v.size() * sizeof(Rml::Vertex) + g->i.size() * sizeof(int); delete g;
    }
    Rml::TextureHandle LoadTexture(Rml::Vector2i&, const Rml::String&) override {
        throw std::runtime_error("external images unsupported in this profile");
    }
    Rml::TextureHandle GenerateTexture(Rml::Span<const Rml::byte> source, Rml::Vector2i dimensions) override {
        if (dimensions.x <= 0 || dimensions.y <= 0 || dimensions.x > 4096 || dimensions.y > 4096 ||
            source.size() != size_t(dimensions.x) * dimensions.y * 4) throw std::runtime_error("texture bounds");
        auto t = new Texture{dimensions.x, dimensions.y, {source.begin(), source.end()}};
        texture_bytes += t->rgba.size(); peak_texture = std::max(peak_texture, texture_bytes); textures.insert(t);
        return reinterpret_cast<Rml::TextureHandle>(t);
    }
    void ReleaseTexture(Rml::TextureHandle handle) override {
        auto t = reinterpret_cast<Texture*>(handle);
        if (!textures.erase(t)) throw std::runtime_error("unknown texture");
        texture_bytes -= t->rgba.size(); delete t;
    }
    void EnableScissorRegion(bool enable) override { clip = enable; }
    void SetScissorRegion(Rml::Rectanglei value) override { region = value; }
    static float edge(Rml::Vector2f a, Rml::Vector2f b, Rml::Vector2f p) {
        return (p.x-a.x)*(b.y-a.y) - (p.y-a.y)*(b.x-a.x);
    }
    static bool owned(float value, Rml::Vector2f a, Rml::Vector2f b) {
        return value > 0 || (value == 0 && (a.y < b.y || (a.y == b.y && a.x > b.x)));
    }
    void RenderGeometry(Rml::CompiledGeometryHandle handle, Rml::Vector2f translation, Rml::TextureHandle texture) override {
        auto g = reinterpret_cast<Geometry*>(handle); auto t = reinterpret_cast<Texture*>(texture);
        if (!geometries.count(g) || (t && !textures.count(t))) throw std::runtime_error("render handle");
        for (size_t n=0; n<g->i.size(); n+=3) {
            auto a=g->v[g->i[n]], b=g->v[g->i[n+1]], c=g->v[g->i[n+2]];
            a.position+=translation; b.position+=translation; c.position+=translation;
            float area=edge(a.position,b.position,c.position);
            if (!std::isfinite(area) || area == 0) continue;
            if (area < 0) { std::swap(b,c); area=-area; }
            int x0=std::max(0,int(std::floor(std::min({a.position.x,b.position.x,c.position.x}))));
            int x1=std::min(W,int(std::ceil(std::max({a.position.x,b.position.x,c.position.x}))));
            int y0=std::max(0,int(std::floor(std::min({a.position.y,b.position.y,c.position.y}))));
            int y1=std::min(H,int(std::ceil(std::max({a.position.y,b.position.y,c.position.y}))));
            if (clip) { x0=std::max(x0,region.Left()); x1=std::min(x1,region.Right()); y0=std::max(y0,region.Top()); y1=std::min(y1,region.Bottom()); }
            ++triangles;
            for (int y=y0;y<y1;++y) for(int x=x0;x<x1;++x) {
                Rml::Vector2f p(float(x)+.5f,float(y)+.5f);
                float u=edge(b.position,c.position,p),v=edge(c.position,a.position,p),w=edge(a.position,b.position,p);
                if (!owned(u,b.position,c.position) || !owned(v,c.position,a.position) || !owned(w,a.position,b.position)) continue;
                u/=area; v/=area; w/=area;
                float r=u*a.colour.red+v*b.colour.red+w*c.colour.red;
                float gr=u*a.colour.green+v*b.colour.green+w*c.colour.green;
                float bl=u*a.colour.blue+v*b.colour.blue+w*c.colour.blue;
                float alpha=u*a.colour.alpha+v*b.colour.alpha+w*c.colour.alpha;
                if (t) {
                    int tx=std::clamp(int((u*a.tex_coord.x+v*b.tex_coord.x+w*c.tex_coord.x)*t->w),0,t->w-1);
                    int ty=std::clamp(int((u*a.tex_coord.y+v*b.tex_coord.y+w*c.tex_coord.y)*t->h),0,t->h-1);
                    auto s=&t->rgba[(ty*t->w+tx)*4]; r*=s[0]/255.f; gr*=s[1]/255.f; bl*=s[2]/255.f; alpha*=s[3]/255.f;
                }
                uint32_t dst=pixels[y*W+x]; float inv=1.f-alpha/255.f;
                auto channel=[](float a){return uint32_t(std::clamp(int(a+.5f),0,255));};
                pixels[y*W+x]=channel(r+float(dst>>16&255)*inv)<<16 | channel(gr+float(dst>>8&255)*inv)<<8 | channel(bl+float(dst&255)*inv);
            }
        }
    }
    void frame(Rml::Context* context) { std::fill(pixels.begin(),pixels.end(),0x0b1019); context->Update(); context->Render(); }
    void save(const std::string& path) {
        BITMAPFILEHEADER file{}; BITMAPINFOHEADER info{};
        file.bfType=0x4d42; file.bfOffBits=sizeof(file)+sizeof(info); file.bfSize=file.bfOffBits+W*H*4;
        info.biSize=sizeof(info); info.biWidth=W; info.biHeight=-H; info.biPlanes=1; info.biBitCount=32; info.biCompression=BI_RGB;
        std::ofstream out(path,std::ios::binary); out.write(reinterpret_cast<char*>(&file),sizeof(file)); out.write(reinterpret_cast<char*>(&info),sizeof(info));
        out.write(reinterpret_cast<char*>(pixels.data()),pixels.size()*4); if(!out) throw std::runtime_error("image write");
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
    bool initialized=false;
    Renderer renderer; System system; Listener listener(action);
    try {
        renderer.pixels.resize(W * H);
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
        stats<<"{\"evidence\":\"HOST\",\"engine\":\"RmlUi 6.3\",\"renderer\":\"CPU\",\"callback_passed\":"<<(passed?"true":"false")
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
