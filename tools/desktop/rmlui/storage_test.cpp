#include "renderer.h"
#include <cstdio>
#include <stdexcept>
void require(bool ok,const char* message) {if(!ok) throw std::runtime_error(message);}
int main() {
    try {
        BmoUi::Renderer r;
        const Rml::byte mono[]={0,0,0,0,128,128,128,128};
        const Rml::byte color[]={255,0,0,255,0,128,0,128};
        auto a=r.GenerateTexture({mono,8},{2,1});
        auto b=r.GenerateTexture({color,8},{2,1});
        auto alpha=reinterpret_cast<BmoUi::Texture*>(a);
        auto rgba=reinterpret_cast<BmoUi::Texture*>(b);
        require(alpha->alpha_only && alpha->texels.size()==2 && alpha->texels[0]==0 && alpha->texels[1]==128,"mask storage changed coverage");
        require(!rgba->alpha_only && rgba->texels==std::vector<Rml::byte>(color,color+8),"color fallback lost data");
        require(r.texture_bytes==10 && r.texture_equivalent_bytes==16,"payload accounting");
        r.ReleaseTexture(a); r.ReleaseTexture(b);
        require(!r.texture_bytes && !r.texture_equivalent_bytes && r.textures.empty(),"texture lifetime");
        std::vector<Rml::TextureHandle> handles;
        for(int i=0;i<64;++i) handles.push_back(r.GenerateTexture({mono,4},{1,1}));
        bool rejected=false;
        try {r.GenerateTexture({mono,4},{1,1});} catch(const std::runtime_error&) {rejected=true;}
        require(rejected && r.textures.size()==64 && r.texture_bytes==64 && r.texture_equivalent_bytes==256,"handle budget weakened");
        for(auto h:handles) r.ReleaseTexture(h);
        require(!r.texture_bytes && !r.texture_equivalent_bytes && r.textures.empty(),"post-rejection cleanup");
        std::puts("PASS: lossless mask storage, colored RGBA fallback, budget and cleanup");
        return 0;
    } catch(const std::exception& e) {std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}
}
