#include <iostream>
#include <vector>
#include <cmath>
#include "matplotlibcpp.h"

namespace plt = matplotlibcpp;

int main() {
    std::cout << "Hello Monte Carlo" << std::endl;

    int n = 100;
    std::vector<double> x(n), y(n);
    
    for(int i = 0; i < n; ++i) {
        x[i] = i * 4.0 * M_PI / n;
        y[i] = std::sin(x[i]);
    }

    plt::figure();
    plt::plot(x, y, "r-");
    plt::title("Hello Monte Carlo - Sine Wave");
    plt::xlabel("x");
    plt::ylabel("sin(x)");
    plt::grid(true);
    
    plt::show();

    return 0;
}