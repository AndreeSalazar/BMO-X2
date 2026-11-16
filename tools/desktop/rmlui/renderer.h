#pragma once
#include <RmlUi/Core.h>
#include "raster.h"
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <memory>
#include <unordered_set>
#include <vector>
namespace BmoUi {
#ifdef BMO_UI_NATIVE
[[noreturn]] void native_failure(const char*);
#endif
[[noreturn]] inline void fail(const char* message) {
#ifdef BMO_UI_NATIVE
    native_failure(message);
#else
    throw std::runtime_error(message);
#endif
}

constexpr int W = 1280, H = 800;
struct Geometry { std::vector<Rml::Vertex> v; std::vector<int> i; };
struct Texture { int w, h; bool alpha_only; std::vector<Rml::byte> texels; };
class Renderer : public Rml::RenderInterface {
public:
    uint32_t* pixels=nullptr;
    size_t pixel_count=0;
    size_t triangles = 0, peak_geometry = 0, peak_texture = 0, geometry_bytes = 0, texture_bytes = 0;
    size_t texture_equivalent_bytes=0, peak_texture_equivalent_bytes=0;
    std::unordered_set<Geometry*> geometries;
    std::unordered_set<Texture*> textures;
    ~Renderer() override {
        for(auto g:geometries) delete g;
        for(auto t:textures) delete t;
    }
    bool clip = false;
    bool transformed=false, unsupported_transform=false;
    bool unsupported_feature=false;
    Rml::Rectanglei region = Rml::Rectanglei::FromPositionSize({0, 0}, {W, H});
    Rml::CompiledGeometryHandle CompileGeometry(Rml::Span<const Rml::Vertex> v, Rml::Span<const int> i) override {
        if (v.size() > 1000000 || i.size() > 3000000 || i.size() % 3) fail("geometry bounds");
        if(geometries.size()>=4096 || geometry_bytes+v.size()*sizeof(Rml::Vertex)+i.size()*sizeof(int)>16*1024*1024) fail("geometry budget");
        auto owned = std::make_unique<Geometry>(Geometry{{v.begin(), v.end()}, {i.begin(), i.end()}});
        auto g=owned.get();
        for (int n : g->i) if (n < 0 || size_t(n) >= g->v.size()) fail("geometry index");
        geometries.insert(g);
        geometry_bytes += g->v.size() * sizeof(Rml::Vertex) + g->i.size() * sizeof(int);
        peak_geometry = std::max(peak_geometry, geometry_bytes); owned.release();
        return reinterpret_cast<Rml::CompiledGeometryHandle>(g);
    }
    void ReleaseGeometry(Rml::CompiledGeometryHandle handle) override {
        auto g = reinterpret_cast<Geometry*>(handle);
        if (!geometries.erase(g)) fail("unknown geometry");
        geometry_bytes -= g->v.size() * sizeof(Rml::Vertex) + g->i.size() * sizeof(int); delete g;
    }
    Rml::TextureHandle LoadTexture(Rml::Vector2i&, const Rml::String&) override {
        fail("external images unsupported in this profile");
    }
    Rml::TextureHandle GenerateTexture(Rml::Span<const Rml::byte> source, Rml::Vector2i dimensions) override {
        if (dimensions.x <= 0 || dimensions.y <= 0 || dimensions.x > 4096 || dimensions.y > 4096 ||
            source.size() != size_t(dimensions.x) * dimensions.y * 4) fail("texture bounds");
        if(textures.size()>=64 || texture_equivalent_bytes+source.size()>16*1024*1024) fail("texture budget");
        bool alpha=true;
        for(size_t i=0;i<source.size();i+=4) {
            if(source[i]!=source[i+3] || source[i+1]!=source[i+3] || source[i+2]!=source[i+3]) {alpha=false;break;}
        }
        auto owned=std::make_unique<Texture>(Texture{dimensions.x, dimensions.y, alpha, {}});
        if(alpha) {
            owned->texels.resize(source.size()/4);
            for(size_t i=0;i<owned->texels.size();++i) owned->texels[i]=source[i*4+3];
        } else owned->texels.assign(source.begin(),source.end());
        auto t=owned.get(); textures.insert(t);
        texture_bytes += t->texels.size(); peak_texture = std::max(peak_texture, texture_bytes);
        texture_equivalent_bytes+=source.size(); peak_texture_equivalent_bytes=std::max(peak_texture_equivalent_bytes,texture_equivalent_bytes);
        owned.release();
        return reinterpret_cast<Rml::TextureHandle>(t);
    }
    void ReleaseTexture(Rml::TextureHandle handle) override {
        auto t = reinterpret_cast<Texture*>(handle);
        if (!textures.erase(t)) fail("unknown texture");
        texture_bytes -= t->texels.size(); texture_equivalent_bytes-=size_t(t->w)*t->h*4; delete t;
    }
    void SetTransform(const Rml::Matrix4f* value) override { transformed=value!=nullptr; unsupported_transform|=transformed; }
    void EnableClipMask(bool enabled) override { unsupported_feature|=enabled; }
    void RenderToClipMask(Rml::ClipMaskOperation,Rml::CompiledGeometryHandle,Rml::Vector2f) override { unsupported_feature=true; }
    Rml::LayerHandle PushLayer() override { unsupported_feature=true; return 1; }
    void CompositeLayers(Rml::LayerHandle,Rml::LayerHandle,Rml::BlendMode,Rml::Span<const Rml::CompiledFilterHandle>) override { unsupported_feature=true; }
    Rml::CompiledFilterHandle CompileFilter(const Rml::String&,const Rml::Dictionary&) override {unsupported_feature=true;return 0;}
    Rml::CompiledShaderHandle CompileShader(const Rml::String&,const Rml::Dictionary&) override {unsupported_feature=true;return 0;}
    void EnableScissorRegion(bool enable) override { clip = enable; }
    void SetScissorRegion(Rml::Rectanglei value) override { region = value; }
    void RenderGeometry(Rml::CompiledGeometryHandle handle, Rml::Vector2f translation, Rml::TextureHandle texture) override {
        if(transformed) return;
        auto g=reinterpret_cast<Geometry*>(handle); auto t=reinterpret_cast<Texture*>(texture);
        if(!geometries.count(g) || (t && !textures.count(t))) fail("render handle");
        BmoUiRect bounds{0,0,W,H};
        if(clip) bounds={uint32_t(std::clamp(region.Left(),0,W)),uint32_t(std::clamp(region.Top(),0,H)),
                         uint32_t(std::clamp(region.Right(),0,W)),uint32_t(std::clamp(region.Bottom(),0,H))};
        for(size_t n=0;n<g->i.size();n+=3) {
            BmoUiVertex vertices[3];
            for(size_t k=0;k<3;++k) {
                const auto& v=g->v[g->i[n+k]];
                vertices[k]={v.position.x+translation.x,v.position.y+translation.y,
                    float(v.colour.red),float(v.colour.green),float(v.colour.blue),float(v.colour.alpha),v.tex_coord.x,v.tex_coord.y};
            }
            auto raster=t && t->alpha_only?bmo_ui_triangle_mask:bmo_ui_triangle;
            if(raster(pixels,pixel_count,W,H,vertices,t?t->texels.data():nullptr,
                t?t->texels.size():0,t?uint32_t(t->w):0,t?uint32_t(t->h):0,bounds)!=0) fail("Rust raster rejected geometry");
            ++triangles;
        }
    }
    void frame(Rml::Context* context) {
        unsupported_transform=false;
        std::fill(pixels,pixels+pixel_count,0x0b1019); context->Update(); context->Render();
        if(unsupported_transform) fail("transforms outside CPU profile");
        if(unsupported_feature) fail("layers, masks, filters or shaders outside CPU profile");
    }
};
}
