#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <utility>

namespace edge {
// Chen et al. (2024), Sec. 4.4.1-4.4.2: Sobel, threshold, closing.
// US6553131B1, Fig. 1 block 16: vertical edges. The patent does not name Sobel.
// Gx selection, threshold 80, 3x3 closing and border rules are frozen here.
inline void vertical_sobel(const std::uint8_t* gray, std::uint8_t* out,
                           std::size_t w, std::size_t h, bool column, int threshold) {
    std::memset(out,0,w);
    std::memset(out+(h-1)*w,0,w);
    for(std::size_t y=1;y+1<h;++y) out[y*w]=out[y*w+w-1]=0;
    auto pixel=[&](std::size_t x,std::size_t y) {
        const auto p=y*w+x;
        const int gx=-gray[p-w-1]+gray[p-w+1]-2*gray[p-1]+2*gray[p+1]-gray[p+w-1]+gray[p+w+1];
        const int strength=std::abs(gx);
        out[p]=static_cast<std::uint8_t>(strength<threshold?0:255);
    };
    if(column) {
        for(std::size_t x=1;x+1<w;++x) for(std::size_t y=1;y+1<h;++y) pixel(x,y);
    } else for(std::size_t y=1;y+1<h;++y) for(std::size_t x=1;x+1<w;++x) pixel(x,y);
}

// Binary closing = dilation followed by erosion with a full 3x3 square.
// Outside pixels are zero in each pass. Sobel and final image borders are zero.
// scratch is the first WH bytes of this slot's now-consumed RGB array.
inline void close_binary(std::uint8_t* out, std::uint8_t* scratch,
                         std::size_t w, std::size_t h, bool column) {
    auto visit=[&](auto fn) {
        if(column) {
            for(std::size_t x=0;x<w;++x) for(std::size_t y=0;y<h;++y) fn(x,y);
        } else for(std::size_t y=0;y<h;++y) for(std::size_t x=0;x<w;++x) fn(x,y);
    };
    visit([&](std::size_t x,std::size_t y) {
        std::uint8_t value=0;
        for(int dy=-1;dy<=1;++dy) for(int dx=-1;dx<=1;++dx) {
            const auto xx=static_cast<std::ptrdiff_t>(x)+dx;
            const auto yy=static_cast<std::ptrdiff_t>(y)+dy;
            if(xx>=0 && yy>=0 && xx<static_cast<std::ptrdiff_t>(w) && yy<static_cast<std::ptrdiff_t>(h))
                value=std::max(value,out[static_cast<std::size_t>(yy)*w+static_cast<std::size_t>(xx)]);
        }
        scratch[y*w+x]=value;
    });
    visit([&](std::size_t x,std::size_t y) {
        if(x==0 || y==0 || x+1==w || y+1==h) {out[y*w+x]=0;return;}
        std::uint8_t value=255;
        for(int dy=-1;dy<=1;++dy) for(int dx=-1;dx<=1;++dx)
            value=std::min(value,scratch[static_cast<std::size_t>(static_cast<std::ptrdiff_t>(y)+dy)*w+
                                           static_cast<std::size_t>(static_cast<std::ptrdiff_t>(x)+dx)]);
        out[y*w+x]=value;
    });
}

// RGB order. Exact integer policy is specified in docs/METHODOLOGY.md.
inline void gray_contrast(const std::uint8_t* rgb, std::uint8_t* gray,
                          std::size_t w, std::size_t h, bool column) {
    auto pixel = [&](std::size_t p) {
        const int y = (299 * rgb[3*p] + 587 * rgb[3*p+1] + 114 * rgb[3*p+2] + 500) / 1000;
        gray[p] = static_cast<std::uint8_t>(std::clamp((5*y + 2)/4 - 32, 0, 255));
    };
    if (column) {
        for (std::size_t x=0; x<w; ++x)
            for (std::size_t y=0; y<h; ++y) pixel(y*w+x);
    } else {
        for (std::size_t p=0; p<w*h; ++p) pixel(p);
    }
}

inline void sobel(const std::uint8_t* gray, std::uint8_t* out,
                  std::size_t w, std::size_t h, bool column) {
    // Separate input/output arrays; all border pixels have defined zero output.
    std::memset(out, 0, w);
    std::memset(out+(h-1)*w, 0, w);
    for (std::size_t y=1; y+1<h; ++y) out[y*w] = out[y*w+w-1] = 0;
    auto pixel = [&](std::size_t x, std::size_t y) {
        const auto p = y*w+x;
        const int a=gray[p-w-1], b=gray[p-w], c=gray[p-w+1];
        const int d=gray[p-1], f=gray[p+1];
        const int g=gray[p+w-1], j=gray[p+w], k=gray[p+w+1];
        const int gx = -a+c-2*d+2*f-g+k;
        const int gy = -a-2*b-c+g+2*j+k;
        out[p] = static_cast<std::uint8_t>(std::min(255, std::abs(gx)+std::abs(gy)));
    };
    if (column) {
        for (std::size_t x=1; x+1<w; ++x)
            for (std::size_t y=1; y+1<h; ++y) pixel(x,y);
    } else {
        for (std::size_t y=1; y+1<h; ++y)
            for (std::size_t x=1; x+1<w; ++x) pixel(x,y);
    }
}

inline std::pair<std::uint64_t,std::uint64_t> fingerprint(const std::uint8_t* p, std::size_t n) {
    std::uint64_t sum=0, weighted=0;
    for (std::size_t i=0; i<n; ++i) {
        sum += p[i];
        weighted += static_cast<std::uint64_t>(p[i]) * (i+1);
    }
    return {sum, weighted};
}
}
