---
name: profile-optimise
description: Profile slow code and speed it up properly - baseline, sampling profile, fixes in order of share, outputs checked against the baseline, re-profile, record. Use whenever the user asks to optimise, speed up, profile, benchmark or find a bottleneck, asks why something is slow or memory-hungry, or mentions GPU offload, numba or JIT, batching, buffer reuse, caching, pipelining, TensorRT, data structures, algorithmic complexity or a better algorithm, even if they never say "profile". Use it before any performance change, including ones that look obvious.
---

# Profile, then optimise

Guessing the hotspot costs more than measuring it: in a real pass the suspected hotspot (GPU
rendering) was 3 % of the run and the real ones were repeated feature extraction (29 %) and a numpy
channel mean (12 %). Work from measurements, change one thing at a time, and prove each change kept
the results.

## 1. Fix the workload

- Use the real flow, end to end, on a slice that finishes every stage including the final report
  and its output files. Sampling needs 20 s or more of runtime; a smaller slice hides the real shape.
- Cost often scales with a count (candidates ranked, views rendered, photos tracked). Profile at the
  count that matters, and note it next to every number.
- Pin everything that moves: inputs, seeds, thread settings, caches, clocks, GPU state. Record the
  machine (cores, logical CPUs, GPU, library versions).
- Log one line per stage (name, count, total) to a named file. A job over about 10 minutes also gets
  a watcher on that file that reports failures.

## Cost model

Write each stage's cost as count times unit cost from the baseline (for example 8 ms a render plus
10 ms a descriptor, 18 ms a view) and predict any larger run from it before launching: 28,000 views
predicted 9 minutes and measured 8.9. A miss of more than about 20 % means the cost is not linear
(memory pressure, contention, a hidden stage) and the profile has not found it yet. Test the
exact path on a tiny slice first, so a late-stage bug does not appear at the end of a long run.

Speed has two multiplying levers: fewer things (priors, hints, coarse-to-fine, caching) and cheaper
things (GPU, batching, precision). Cutting the count usually gains more, and where it changes what is
searched it needs the owner's decision. Resource ceilings count as costs too: a run that peaks at
10.9 of 12.3 GB of GPU memory will fail when scaled up, not slow down.

## 2. Baseline

- Time the workload at least three times with warm caches. Discard the first run: engine builds,
  JIT compilation, CUDA context creation and file caches belong to start-up, not to the steady state.
- Keep the baseline outputs as the reference, and write the script that compares a run to them field
  by field. Without it no speed-up can be claimed.

## 3. Profile

- Sample wall-clock time with a sampling profiler (py-spy at 50 Hz, `--native` when time hides in
  C or CUDA libraries). cProfile counts thread-lock waiting as work and misreads thread pools
  (ONNX Runtime showed 50 s of phantom waiting); the sampler is the reference.
- Asynchronous GPU work lies to wall-clock timers: synchronise the stream before reading a timer,
  or use the framework profiler (torch profiler, Nsight Systems, ONNX Runtime profiling) for kernels.
  Watch GPU utilisation while the run goes: an idle GPU means the feed is starved, a saturated one
  means the kernels are the limit.
- Sample peak RAM and GPU memory every few seconds into a file; memory is often the wall at scale.
- Measure how the hot path scales: time it at n, 2n and 4n and read the exponent off the ratios.
  Two or four times the work taking four or sixteen times as long is a complexity problem, and
  no constant-factor fix will hold at the size that matters.
- Read the profile as a table: share of the run, inclusive and self time, call count times cost per
  call. A call count far above the work done (a photo's features computed once per candidate, 216
  times) is the usual find. Also look for serial hand-offs between devices, host-device copies,
  allocation churn, Python loops over arrays, quadratic searches and idle resources.

## 4. Choose the changes

Estimate the ceiling before starting: removing a part that takes share s of the run saves at most s.
Work in order of share, and prefer the earlier items in this list, which remove work instead of
doing it faster:

1. Do less: hoist what is invariant out of loops, compute once and reuse, cache, exit early.
2. Do it on the right device: keep data resident on the GPU between steps, avoid round trips, bind
   buffers to the inference runtime, use lower precision or an optimised engine (FP16, TensorRT)
   when the accuracy check allows it.
3. Overlap independent work: render while inferring, read while computing; size thread pools by a
   sweep, not by guess.
4. Batch, when the model supports it: check the exported batch dimension first, an export fixed at
   batch 1 gives nothing.
5. CPU-bound numeric code: vectorise, then compile hot loops (numba `njit` with caching, warmed up
   before timing), and use the right data structure (spatial index instead of a quadratic scan).
6. Memory: allocate buffers once and reuse them, avoid copies, keep arrays contiguous and typed.
   Skip it when the profile shows no allocation cost.

A change that alters behaviour (which candidates are verified, a smaller search, lower precision with
different outputs) is a decision for the owner. Measure it, put the numbers in front of them, and do
not adopt it silently.

## Algorithms and data structures

Choose these before tuning constants: a better complexity class outlasts any micro-optimisation, and
changing the data structure often removes the hot loop altogether.

- Name the hot path's n and its access pattern (lookup, range query, nearest neighbour, top-k,
  insert, scan in order, repeated membership test), then pick the structure that makes that pattern
  cheap. Typical swaps: a repeated scan of a list becomes a hash set or dictionary; "points near
  this point" becomes a spatial index (k-d tree, grid hash) instead of a distance to every point;
  top-k of a large array becomes a partial selection (`argpartition`, a heap) instead of a full
  sort; a sort repeated inside a loop becomes one sort outside it; a running minimum or maximum over
  a sliding window becomes a monotonic queue.
- Turn many small operations into one large one: a Python loop of dot products becomes one matrix
  product (a similarity search of a query against a million descriptors is a single GPU matmul), a
  per-item loop over arrays becomes a vectorised expression, a pairwise comparison becomes a
  broadcast, and a repeated lookup becomes a precomputed table.
- Build an index once, query it many times. When the same database is searched repeatedly, spend the
  build cost up front and cache the index to disk with a key that changes when its inputs change.
  Approximate nearest-neighbour search (an inverted file or graph index) trades recall for speed
  once exact search is the limit; measure the recall it loses before adopting it.
- Layout and type are part of the structure: keep hot arrays contiguous, store fields as separate
  arrays (structure of arrays) when the loop reads one or two of them, use the narrowest dtype the
  accuracy allows (float16 descriptors on disk halved a cache at no measured loss), and stream or
  chunk data larger than memory instead of loading it whole.
- Cut the problem by its structure before searching it: process coarse before fine, prune with a
  cheap bound before an expensive test, exploit symmetry and sortedness, memoise repeated
  sub-problems, and stop at the first sufficient answer.
- Take the structure or algorithm from the standard library or an established package (scipy
  spatial trees, `heapq`, `bisect`, numpy selection and sorting, FAISS or similar for large vector
  search) instead of writing one. Hand-rolled structures ship untested edge cases that are then
  owned for good; write one only when nothing fits the shape and say why.
- Prove the swap on its own terms: the same outputs on the reference, and a scaling run showing the
  exponent improved. A structure that is faster at the test size and worse at the target size is a
  loss.

## 5. Apply and prove

- One change at a time. After each: run the workload, time it three times, compare the outputs with
  the reference.
- A pure refactor must match the reference exactly (diff every field; zero difference is the bar).
  A numerical change (FP16, a different kernel, a different order of summation) is compared against
  truth or a metric with a tolerance taken from the arithmetic, and reported as different, not as
  identical.
- Keep the change only if it gains and the outputs hold; otherwise revert it and write down why.
- After the pass, profile again. Shares move: a part that took 15 ms alone took 80 ms under CPU
  contention, and a parallel kernel can slow the library it competes with. Sweep thread and worker
  counts into a table and choose a value on the plateau, not at its edge.

## 6. Record

Write one results document: the workload and machine, the baseline timing, the profile as a share
table, each change in order with what it removed and the gain, the before and after table, the
statement that outputs are identical (or how they differ), what was measured and not adopted with the
reason, and what was not profiled. Update the project's status and decision records as its rules say.

## Traps

- Timing a cold first run, or timing GPU work without synchronising.
- Parallelising inside a library that already uses all cores: it competes with its own threads.
- Calling a GPU context from a thread that did not create it. One run segfaulted with no traceback.
- Profiling while the machine does other work, or comparing numbers from different load.
- Optimising a part the profile never showed, or reporting a speed-up without the output comparison.
- Trusting a synthetic micro-benchmark over the real flow: the real flow has the contention.
