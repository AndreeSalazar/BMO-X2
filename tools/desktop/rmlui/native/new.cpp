// The complete no-exceptions allocation family shares the bounded native heap.
#include <new>
#include <cstdlib>
#include <cstdint>
extern "C" [[noreturn]] void bmo_native_fail(const char*);
extern "C" [[noreturn]] void bmo_native_oom(size_t);
static void* allocate(size_t n,size_t alignment,bool required) {
    if(!n)n=1;
    void* p=nullptr;
    if(alignment<=16)p=std::malloc(n);
    else if(n<=SIZE_MAX-(alignment-1))p=std::aligned_alloc(alignment,(n+alignment-1)&~(alignment-1));
    if(!p && required)bmo_native_oom(n);
    return p;
}
void* operator new(size_t n) {return allocate(n,16,true);}
void* operator new[](size_t n) {return allocate(n,16,true);}
void* operator new(size_t n,const std::nothrow_t&) noexcept {return allocate(n,16,false);}
void* operator new[](size_t n,const std::nothrow_t&) noexcept {return allocate(n,16,false);}
void* operator new(size_t n,std::align_val_t a) {return allocate(n,size_t(a),true);}
void* operator new[](size_t n,std::align_val_t a) {return allocate(n,size_t(a),true);}
void* operator new(size_t n,std::align_val_t a,const std::nothrow_t&) noexcept {return allocate(n,size_t(a),false);}
void* operator new[](size_t n,std::align_val_t a,const std::nothrow_t&) noexcept {return allocate(n,size_t(a),false);}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete(void* p,size_t) noexcept {std::free(p);}
void operator delete[](void* p,size_t) noexcept {std::free(p);}
void operator delete(void* p,std::align_val_t) noexcept {std::free(p);}
void operator delete[](void* p,std::align_val_t) noexcept {std::free(p);}
void operator delete(void* p,size_t,std::align_val_t) noexcept {std::free(p);}
void operator delete[](void* p,size_t,std::align_val_t) noexcept {std::free(p);}
void operator delete(void* p,const std::nothrow_t&) noexcept {std::free(p);}
void operator delete[](void* p,const std::nothrow_t&) noexcept {std::free(p);}
void operator delete(void* p,std::align_val_t,const std::nothrow_t&) noexcept {std::free(p);}
void operator delete[](void* p,std::align_val_t,const std::nothrow_t&) noexcept {std::free(p);}
