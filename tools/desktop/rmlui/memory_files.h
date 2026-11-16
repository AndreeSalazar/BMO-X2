#pragma once
#include "engine.h"
#include <RmlUi/Core.h>
#include <array>
#include <cstring>
#include <cstdio>
namespace BmoUi {
inline bool resource_name(const char* value) {
    if(!value) return false;
    size_t n=0;
    for(;n<64 && value[n];++n) {
        char c=value[n];
        if(!((c>='a' && c<='z') || (c>='A' && c<='Z') || (c>='0' && c<='9') || c=='_' || c=='-' || c=='.')) return false;
    }
    return n>0 && n<64 && !std::strstr(value,"..");
}
class MemoryFiles final : public Rml::FileInterface {
    struct Cursor { const BmoUiBlob* blob=nullptr; size_t position=0; };
    std::array<BmoUiBlob,8> blobs{};
    std::array<Cursor,32> cursors{};
    size_t count=0;
    Cursor* get(Rml::FileHandle h) { return h && h<=cursors.size() && cursors[h-1].blob?&cursors[h-1]:nullptr; }
public:
    uint64_t open_count=0, denied=0;
    bool assign(const BmoUiBlob* input,size_t n) {
        if(!input || !n || n>blobs.size()) return false;
        size_t total=0;
        for(size_t i=0;i<n;++i) {
            if(!resource_name(input[i].name) || !input[i].data || !input[i].length || input[i].length>2*1024*1024) return false;
            total+=input[i].length;
            if(total>8*1024*1024) return false;
            for(size_t k=0;k<i;++k) if(std::strcmp(input[k].name,input[i].name)==0) return false;
            blobs[i]=input[i];
        }
        count=n; return true;
    }
    Rml::FileHandle Open(const Rml::String& name) override {
        if(resource_name(name.c_str())) {
            for(size_t i=0;i<count;++i) if(name==blobs[i].name) {
                for(size_t k=0;k<cursors.size();++k) if(!cursors[k].blob) {
                    cursors[k]={&blobs[i],0}; ++open_count; return k+1;
                }
            }
        }
        ++denied; return 0;
    }
    void Close(Rml::FileHandle h) override { if(auto c=get(h)) { *c={}; --open_count; } }
    size_t Read(void* output,size_t size,Rml::FileHandle h) override {
        auto c=get(h); if(!c || (!output && size)) return 0;
        size_t n=std::min(size,c->blob->length-c->position);
        if(n) std::memcpy(output,c->blob->data+c->position,n);
        c->position+=n; return n;
    }
    bool Seek(Rml::FileHandle h,long offset,int origin) override {
        auto c=get(h); if(!c) return false;
        int64_t base;
        if(origin==SEEK_SET) base=0;
        else if(origin==SEEK_CUR) base=int64_t(c->position);
        else if(origin==SEEK_END) base=int64_t(c->blob->length);
        else return false;
        // Resource size is bounded; reject extreme offsets before addition.
        if(offset < -int64_t(c->blob->length) || offset > int64_t(c->blob->length)) return false;
        int64_t next=base+offset;
        if(next<0 || uint64_t(next)>c->blob->length) return false;
        c->position=size_t(next); return true;
    }
    size_t Tell(Rml::FileHandle h) override { auto c=get(h); return c?c->position:0; }
    size_t Length(Rml::FileHandle h) override { auto c=get(h); return c?c->blob->length:0; }
};
}
