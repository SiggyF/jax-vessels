# Benchmark Report

## Standard Benchmark: KCS Hull (Scale)

This benchmark measures the performance of the full simulation pipeline, including meshing (`snappyHexMesh`), optimization (`renumberMesh`), and solving (`interFoam`).

### Hardware Configuration
*   **Machine**: Apple Silicon (M-series)
*   **Cores**: 6 Logical (Docker allocated)
*   **Memory**: 16 GB (System)

### Results (`kcs_hull`)

| Metric | Value |
| :--- | :--- |
| **Grid Size** | **238,402 cells** |
| **Solver Time (Total)** | **109 s** |
| **Time per Step (Avg)** | **~0.02 s/step** |
| **Parallel Efficiency** | High (~520% CPU usage observed) |

### Optimization
*   **RenumberMesh**: Enabled.
*   **Decomposition**: Scotch (6 partitions).

### How to Run
To run this benchmark yourself:

```bash
# Verify Docker is running
docker info

# Run Benchmark (run 1 time)
uv run benchmarks/run_benchmark.py --case kcs_hull --runs 1
```

### Analysis
The simulation confirms that the current containerized setup efficiently utilizes available cores. The integration of `renumberMesh` ensures optimal matrix ordering for the linear solver.
