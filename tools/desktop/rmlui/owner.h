#pragma once
namespace BmoUi {
// RmlUi has process-global interfaces. One owner, on the single UI thread.
inline bool rmlui_owned=false;
struct Lease {
    bool acquired=false;
    Lease() { if(!rmlui_owned) {rmlui_owned=true;acquired=true;} }
    Lease(const Lease&)=delete;
    Lease& operator=(const Lease&)=delete;
    ~Lease() { if(acquired) rmlui_owned=false; }
    explicit operator bool() const {return acquired;}
};
}
