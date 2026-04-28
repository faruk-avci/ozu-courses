/*
 * PHYS 551: Advanced Monte Carlo Methods
 * Homework 1 - Source Code
 * Student: Omer Faruk Avci
 * Instructor: Prof. Taylan Akdogan
 * 
 * =========================================================================
 * 1. DEPENDENCIES
 * =========================================================================
 * This project utilizes 'matplotlib-cpp' for 2D visualization in Problem 3.
 * If 'matplotlibcpp.h' is not present in your directory, please download it
 * using one of the following terminal commands:
 * 
 * macOS (curl): curl -O https://raw.githubusercontent.com/lava/matplotlib-cpp/master/matplotlibcpp.h
 * Linux (wget): wget https://raw.githubusercontent.com/lava/matplotlib-cpp/master/matplotlibcpp.h
 * 
 * =========================================================================
 * 2. COMPILATION AND EXECUTION
 * =========================================================================
 * Due to the Python-C++ linkage, please use the following commands:
 * (Note: Adjust python3.10 to your specific version if needed)
 * 
 * macOS Compilation:
 *   g++ mc.cpp -std=c++11 $(python3-config --cflags) $(python3-config --ldflags) -o mc
 * 
 * Linux Compilation:
 *   g++ mc.cpp -std=c++11 -I/usr/include/python3.10 -lpython3.10 -o mc
 * 
 * To run the code:
 *   ./mc
 * 
 * =========================================================================
 * 3. USAGE & NESTED MODULARITY
 * =========================================================================
 * The code is structured to allow granular control over simulation tasks:
 * 
 * A. Main Level: Toggle run_problem_2() or run_problem_3() in main() 
 *    to skip an entire assignment section.
 * 
 * B. Function Level: Inside run_problem_2() and run_problem_3(), individual 
 *    sub-tasks (a, b, or c) can be commented out to execute only specific 
 *    analyses or visualizations.
 * =========================================================================
 */

#include <iostream>
#include <random>
#include <cmath> 
#include "matplotlibcpp.h"

std::random_device rd; // Random device for seeding
std::mt19937 gen(rd()); // Mersenne Twister random number generator
std::uniform_real_distribution<> square_dist(-1.0, 1.0); // Distribution for x and y coordinates 
std::uniform_real_distribution<> angle_dist(0.0, 2.0 * M_PI); // Distribution for random walk angles

/* 
 * -----------------------------------------------------------------
 * Problem 2: The Cost of Precision (Estimating Pi)
 * -----------------------------------------------------------------
 */

// Core Monte Carlo Function: "Darts in a Square"
// Estimates Pi by placing a circle of radius 1 inside a 2x2 square.
double estimate_pi(int N){
    
    int inside = 0; // Counter for points that fall inside the inscribed circle

    for(int i = 0; i < N; i++){
        double x = square_dist(gen); // x coordinate between -1 and 1
        double y = square_dist(gen); // y coordinate between -1 and 1

        // Check if the point falls inside the circle of radius r=1
        // Equation of circle: x^2 + y^2 <= r^2
        if(x*x + y*y <= 1.0){
            inside++;
        }
    }

    // Ratio of areas: (Area of Circle) / (Area of Square) = (pi * r^2) / (2r)^2 = pi / 4
    // Therefore, Pi is estimated as 4 * (Points Inside / Total Points N)
    return 4.0 * inside / N;
}


// -----------------------------------------------------------------
// Part (a): 
// Takes an array of N values, performs one simulation per N, and prints the result.
// -----------------------------------------------------------------
void run_problem_2_a(int N[], int size){
    for(int i = 0; i < size; i++){
        double pi_estimate = estimate_pi(N[i]);
        std::cout << "N: " << N[i] << " Estimated Pi: " << pi_estimate << std::endl;
    }
}


// -----------------------------------------------------------------
// Part (b):
// This function runs the simulation 'runs' times for each N and averages the estimates.
// -----------------------------------------------------------------
void run_problem_2_b(int N_values[], int size, int runs) {

    for (int i = 0; i < size; i++) {
        int N = N_values[i];
        double sum_pi = 0.0;

        std::cout << "========================" << std::endl;
        std::cout << "N = " << N << std::endl;

        for (int k = 0; k < runs; k++) {
            double pi_estimate = estimate_pi(N);

            std::cout << "Run " << k+1
                      << " | Pi Estimate: "
                      << pi_estimate << std::endl;

            sum_pi += pi_estimate; // Accumulate estimates for averaging
        }

        double average_pi = sum_pi / runs;

        std::cout << "Average Pi for N = "
                  << N << " : "
                  << average_pi << std::endl;
    }
}


// -----------------------------------------------------------------
// Part (c):
// Runs the simulation 10 times for each N, calculates the absolute error
// against the true value of Pi (M_PI), and finds the average error.
// -----------------------------------------------------------------
void run_problem_2_c(int N_values[], int size) {
    const int runs = 10; // As required by the homework prompt

    for (int i = 0; i < size; i++) {
        int N = N_values[i];
        double error_sum = 0.0;

        std::cout << "==============================" << std::endl;
        std::cout << "N = " << N << std::endl;

        for (int k = 0; k < runs; k++) {
            double pi_estimate = estimate_pi(N);
            
            // Calculate absolute error: |pi_estimate - pi_true|
            double error = std::abs(pi_estimate - M_PI);

            std::cout << "Run " << k+1
                      << " | Pi Estimate: " << pi_estimate
                      << " | Absolute Error: " << error
                      << std::endl;

            error_sum += error; // Accumulate errors
        }

        // Calculate the average absolute error for the current N
        double average_error = error_sum / runs;

        std::cout << "Average Absolute Error for N = "
                  << N << " : "
                  << average_error << std::endl;
    }
}

void run_problem_2(){
    // Define the sample sizes as requested in the assignment: 10^1 to 10^7
    int N[] =  {10, 100, 1000, 10000, 100000, 1000000, 10000000};
    int size = sizeof(N) / sizeof(N[0]); // Dynamically calculate array size
    
    // Run Problem 2a
    std::cout << "\nRunning Problem 2a: Single Simulation for Each N" << std::endl;
    run_problem_2_a(N, size);
    
    // Run Problem 2b 
    std::cout << "\nRunning Problem 2b: 10 Simulations for Each N and Averaging" << std::endl;
    int runs = 10;
    run_problem_2_b(N, size, runs);
    
    // Run Problem 2c
    std::cout << "\nRunning Problem 2c: Error Analysis" << std::endl;
    run_problem_2_c(N, size);
}


/* 
 * -----------------------------------------------------------------
 * Problem 3: The “Drunkard’s Walk” (2D Random Walk)
 * -----------------------------------------------------------------
 */


// Core Random Walk Function: Simulates a single random walk of 'steps' steps and 
// returns the squared distance from the origin.
double single_random_walk(int steps) {

    double x = 0.0;
    double y = 0.0;

    for (int i = 0; i < steps; i++) {
        double angle = angle_dist(gen);
        x += std::cos(angle);
        y += std::sin(angle);
    }

    return x*x + y*y;  // return R^2
}

// Simulates 'walks' number of random walks, each with 'steps' steps,
// and returns the root mean square distance from the origin.
double simulate_M_walks(int steps, int walks) {

    double r2_sum = 0.0; 

    for (int i = 0; i < walks; i++) {
        r2_sum += single_random_walk(steps);
    }

    double mean_r2 = r2_sum / walks;
    double rms_distance = std::sqrt(mean_r2);

    return rms_distance;
}


// Even though single_random_walk function is defined, since the problem 3.a asks for plotting a single random walk,
// I will implement the plotting logic directly in run_problem_3_a function.
void run_problem_3_a(int steps) {
    double x = 0.0;
    double y = 0.0;
    
    std::vector<double> x_coords, y_coords;
    x_coords.push_back(x);
    y_coords.push_back(y);

    for (int i = 0; i < steps; i++) {
        double angle = angle_dist(gen);
        x += std::cos(angle);
        y += std::sin(angle);
        x_coords.push_back(x);
        y_coords.push_back(y);
    }

    matplotlibcpp::figure();
    matplotlibcpp::plot(x_coords, y_coords, {{"color", "blue"}, {"linestyle", "-"}, {"label", "Path"}});
    matplotlibcpp::plot({x_coords[0]}, {y_coords[0]}, {{"color", "green"}, {"marker", "o"}, {"label", "Start"}, {"markersize", "8"}});
    matplotlibcpp::plot({x_coords.back()}, {y_coords.back()}, {{"color", "red"}, {"marker", "^"}, {"label", "End"}, {"markersize", "8"}});
    matplotlibcpp::xlabel("x");
    matplotlibcpp::ylabel("y");
    matplotlibcpp::title("2D Random Walk (Drunkard's Walk)");
    matplotlibcpp::legend();
    matplotlibcpp::grid(true);
    matplotlibcpp::show();

    double r = std::sqrt(x*x + y*y);
    std::cout << "Final position: (" << x << ", " << y << ")" << std::endl;
    std::cout << "Distance from origin: " << r << std::endl;
}


// This function simulates 'walks' number of random walks, each with 'steps' steps, and computes the root mean square distance from the origin.
void run_problem_3_b_c(int steps, int walks) {
    double rms_distance = simulate_M_walks(steps, walks);
    std::cout << "RMS Distance from Origin after " << steps 
              << " steps and " << walks 
              << " walks: " << rms_distance << std::endl;
}

void run_problem_3() {

    int steps = 1000;
    int walks = 1000;
    std::cout << "\nRunning Problem 3a: Single Random Walk Simulation with 1000 Steps" << std::endl;
    run_problem_3_a(steps); // Simulate and plot a single random walk with 1000 steps
    std::cout << "\nRunning Problem 3b/c: Simulate 1000 Random Walks and Compute RMS Distance" << std::endl;
    run_problem_3_b_c(steps, walks); // Simulate 1000 random walks and compute RMS distance

}


int main() {

    std::cout << "==========================" << std::endl;
    std::cout << "Running Problem 2: Estimating Pi" << std::endl;
    std::cout << "==========================" << std::endl;
    run_problem_2();

    std::cout << "==========================" << std::endl;
    std::cout << "Running Problem 3: The Drunkard's Walk" << std::endl;
    std::cout << "==========================" << std::endl;
    run_problem_3();

    return 0;
}