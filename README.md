# gem5-benchmarking

If you want to build my project, you can refer to the other repositories in this organization. This repo is just meant to be a place to store my simulation results and scripts. Additionally, given I'm in the course, I can't share the course related gem5 files. So here, I've only posted work that is completely my own, and not part of the course in any way, in accordance with the course's academic integrity policy. I even made sure to work from a publically available branch of gem5 from the course.

Refer to my actual Rust code here: [github.com/bats-eightball/alfred](https://github.com/bats-eightball/alfred)

Below is a summary of my work. This project is definitely more of an application of gem5 to make software decisions than a use of benchmarking to make architectural decisions. I'm happy that I actually get to work on cool architectural things as part of the course though. 

Anyways, happy reading! - Surya Turaga

## Improving a Parallelized Rust Program with gem5

### Problem Statement

I am currently leading a team of 4 for a senior design project. Our goal is to build an autonomous system for gameplay assistance and training in Eight Ball Pool. Keeping track of the game status, it will recommend the most optimal shot to players, displaying it as a projected path on the physical board. The remainder of the project involves physical wireless robots being deployed on the board to move the balls, allowing for move undo and game reset.

My interest was in the computations subsystem of this project. I wanted to explore the question of how to efficiently analyze a game board to compute the most optimal shot, accounting for various factors such as distance, angle, unwanted position changes, etc. With a standard 4K 30fps camera providing a live feed, the goal was to compute the result fast enough such that the remaining time between frames could be allocated to high latency tasks such as image classification and data transmission.

I picked this problem to solve as it was fundamentally an optimization problem. Since the user could request a different target, every possible target needed one optimal recommendation ready while keeping track of which target is the most optimal. Following a principle of avoiding repeated computations, the simplest version of the solution involving parsing every possible combination of shots was trivial in implementation complexity, but completely unfeasible considering the state space of the game involving 7 balls and 6 pockets (which would increase when considering reflections). A challenge of speeding up this algorithm on constrained multiprocessors would mean exploration of mathematics for shot calculation, static graph traversal for pathfinding, and multithreading for higher parallelization of the program.

Once I was ready with a first draft of my code in Rust, I compiled it into a statically linked x86 executable and ran parametric testing on a 4 core O3 CPU through the gem5 simulator. To allow the processor to have multithreading capabilities, I made use of a full system simulation with the Linux 5.4 Kernel and Ubuntu 18.04 Disk Image. I swept through thread pool sizes of 1 - 32 and repeated tests with 10 seed values to collect the mean execution time, processor IPC, cache hit rate, etc of the program to process 100 camera frames. Below is an overview of the methods of optimizations I applied to my program, and the final results I obtained.

### Overview of Optimizations

First, I started with the unoptimized design and provided a numerical objective to my program. Although it is not complete and will likely need further adjustment from heuristics,

$$
Risk = R_{opp} + f(dist_0, \phi_0) + \sum_{i=1}^{n} [ f(dist_i, \phi_i) \cdot (1 + K_{depth} \cdot M_{reflect} \cdot N_{opp})^{i} ]
$$

Risk is calculated by penalizing hitting of opponent balls, analyzing the target to pocket path and entry angle, and by penalizing every subsequent multi level chain in terms of distance, angle, and the use of reflections.

I realized that constructing paths from the cue ball to pockets was unfeasible as there was no way of knowing which paths were the most promising until all paths were mapped out. I made the decision to start from the few pockets during traversal and construct paths backwards. This did not affect the initial search space, but allowed subsequent searches to compare their risk against existing baselines, allowing for early abandonment of unpromising paths. This reduced my execution time by approximately 30% as found by Python benchmarking tools.

```python
for pocket in pockets:    # outer loop: every pocket including reflected
    for ball in targets:  # inner loop: every ball including reflected
        if not legal_clear(pocket, ball):
            continue
        path = backtrack(ball, cue) # adds everything it can along the way
        if path is None:
            continue
        r = risk(pocket, path)
        if r < results[ball].risk:
            results[ball] = (pocket, path, r)    # keep lowest-risk shot
```

My next observation was that this method of backward traversal allowed for a strategy of backtracking known as the Ghost Ball method. This simplified risk calculation greatly. While it did not reduce my execution time greatly, it reduced my code size and allowed me to incorporate reflections in my design, treating reflected targets as being part of a separate path that incurred an additional penalty.

<img src="imgs/pathfinding.png" style="display: block; margin: 0 auto; width: 600px;">

<img src="imgs/ghostball.png" style="display: block; margin: 0 auto; width: 250px;">

<img src="imgs/reflection.png" style="display: block; margin: 0 auto; width: 250px;">

The added functionality of reflections almost tripled execution time due to the increased search space. Optimizations like adjusting the shot depth, checking angles, and early abandonment gave slight improvements.

My next major realization was that paths from target to cue ball were unchanged across pockets, so reuse of computed paths could be increased significantly by starting from the target instead of the pocket, and adding an optimal pocket at the program end. Each path traversal was also completely independent. This was of significant importance as it opened the doors to multithreading.

At this point, I moved the core logic of my program into Rust. It not only allowed me to run a multithreaded application with ease using the Rayon library, it also served as a good learning experience for the language itself. I found that just moving my codebase to Rust alone caused a massive speedup of over 2.50.

```python
table = build_position_table(cue, balls)
pool = ThreadPool(n_threads) # Total available threads
function solve(ball):
    chain = backtrack(ball, cue, table)
    if chain is None:
        return INVALID
    best = INVALID
    for pocket in pockets:
        if legal_clear(pocket, ball, table):
            r = risk(pocket, ball) + risk(chain)
            best = min(best, (pocket, chain, r))
    return best
pool.parallel_map(solve, targets) # one task per ball (real and reflected)
```

The use of the Rayon library allowed me to run tests on my program while adjusting the number of threads available to the program. I utilized Python’s benchmarking library for initial testing, and then used the O3 CPU in gem5 to run a compiled binary of my internal Rust program. This helped get a more fair view of program performance, independent of my own host laptop ram and caching techniques.

## Summarized Results

The below results show the total execution time to process 100 iterations for every thread pool count, found as a mean from 10 seed values per thread count. I chose to run 100 iterations as it was sufficient to account for the initial startup costs, which increased linearly with thread count.

<img src="imgs/results.png" style="display: block; margin: 0 auto; width: 600px;">

Analyzing the results, increasing the thread count initially improves the speedup. The program reaches an optimal speedup of 1.50 with a thread count of 8 on a 4 core O3 CPU. Increasing threads further begins to degrade performance, eventually bringing it to worse than a single threaded program, likely due to context switch overhead. After around 16 threads, the number of available threads likely crosses the peak thread request count. From this point, speedup starts to flatline as there is no improved benefit to adding new threads.

Considering all the speedups made compared to a single threaded Python program, the final speedup of my program was calculated to be $1.43 \cdot 2.50 \cdot 1.50 = 5.36$. This is a significant overall speedup.

This repository has most of my analysis, including my scripts and additional stats that I measured to help me make the above conclusions and decide on a thread pool count. I even put the spreadsheets I used for rough work. My Rust source code can also be found in the Github organization this repository is a part of.

## Final Thoughts

I liked questioning my own design every step of the way in this project, including the validation phase. I kept finding limitations in my own analysis methods, and tried new ways to get better results. This was a very open ended problem that needed a structured design to allow features such as adjustment of thread pool size.

Discounting the implied difficulty of learning Rust while developing this project, I found it quite challenging to get a full system simulation working. I realized that multithreading simulations needed a kernel and disk image due to the thread management requirements, and made use of website walkthroughs on how to write a full system Python file. To understand how to mount the Ubuntu disk image with the correct offset and add my binary executable, I carried out AI assisted debugging of my workflow and python file.

In the presence of the full project having ML workloads for tasks such as image classification, this part of the project realistically may not have been the rate limiting node even in a pure Python implementation. Regardless, working on this area of my senior design was a very enjoyable optimization problem that helped me understand the technicals of thread pool based parallel programs better.

An area I would like to continue working on this optimization project would be to actually simulate my workload on an RISC based processor, since that is the target architecture. This was not implemented, as the target hardware of the project is the A76 microprocessor of the Raspberry Pi 5. I chose not to simulate ARM as I have an x86 machine, and running a full system simulation of ARM meant letting go of the KVM CPU, which would make simulations take more time than I can afford at the moment.

Rather than using benchmarks to make architectural decisions through gem5, this project was more about learning to use gem5 architectures to make software decisions and optimize execution time. At the moment, I am excited to be working on a Waiting Instruction Buffer and a Victim Cache for the x86 O3 CPU. Once this is complete, I would like to touch back on this project and see if there is scope to use more of gem5’s capabilities for analysis of my senior design project.

