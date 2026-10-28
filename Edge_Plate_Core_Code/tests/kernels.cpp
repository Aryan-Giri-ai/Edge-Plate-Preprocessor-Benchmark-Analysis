#include "kernels.hpp"
#include <array>
#include <iostream>
#include <stdexcept>

int main() {
    const std::array<std::uint8_t,15> rgb={0,0,0,255,255,255,255,0,0,0,255,0,0,0,255};
    std::array<std::uint8_t,5> g{};
    edge::gray_contrast(rgb.data(),g.data(),5,1,false);
    const std::array<std::uint8_t,5> expected={0,255,63,156,4};
    if(g!=expected) throw std::runtime_error("known RGB/contrast values failed");
    std::array<std::uint8_t,25> src{},dst{},column{};
    for(int axis=0;axis<2;++axis) {
        for(int y=0;y<5;++y) for(int x=0;x<5;++x) src[y*5+x]=static_cast<std::uint8_t>((axis?y:x)*20);
        edge::sobel(src.data(),dst.data(),5,5,false);
        edge::sobel(src.data(),column.data(),5,5,true);
        if(dst!=column) throw std::runtime_error("traversal mismatch");
        for(int y=0;y<5;++y) for(int x=0;x<5;++x) {
            const int value=(x==0||y==0||x==4||y==4)?0:160;
            if(dst[y*5+x]!=value) throw std::runtime_error("known ramp gradient/border failed");
        }
    }
    src.fill(99); dst.fill(255); edge::sobel(src.data(),dst.data(),5,5,false);
    for(auto x:dst) if(x) throw std::runtime_error("uniform field must be zero");
    for(int axis=0;axis<2;++axis) {
        for(int y=0;y<5;++y) for(int x=0;x<5;++x) src[y*5+x]=static_cast<std::uint8_t>((axis?y:x)*20);
        edge::vertical_sobel(src.data(),dst.data(),5,5,false,160);
        edge::vertical_sobel(src.data(),column.data(),5,5,true,160);
        if(dst!=column) throw std::runtime_error("vertical traversal mismatch");
        if(dst[12]!=(axis?0:255)) throw std::runtime_error("vertical orientation or threshold equality failed");
        edge::vertical_sobel(src.data(),dst.data(),5,5,false,161);
        if(dst[12]) throw std::runtime_error("weak vertical gradient was not suppressed");
    }
    std::array<std::uint8_t,49> binary{},scratch{};
    for(int y=1;y<6;++y) for(int x=1;x<6;++x) binary[y*7+x]=255;
    binary[24]=0; // 1-pixel interior hole must close.
    edge::close_binary(binary.data(),scratch.data(),7,7,false);
    for(int y=0;y<7;++y) for(int x=0;x<7;++x)
        if(binary[y*7+x]!=((x==0||y==0||x==6||y==6)?0:255))
            throw std::runtime_error("closing hole/border check failed");
    binary.fill(0); edge::close_binary(binary.data(),scratch.data(),7,7,true);
    for(auto v:binary) if(v) throw std::runtime_error("empty morphology check failed");
    std::cout<<"Source-profile vertical orientation, binary threshold boundary, closing hole and border checks passed\n";
    std::cout<<"Known grayscale, contrast, Gx/Gy ramps, border and uniform-field checks passed\n";
}
