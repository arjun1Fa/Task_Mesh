# TaskMesh Adaptive Scheduling Pipeline

TaskMesh routes tasks across heterogeneous machines using an adaptive multi-stage scheduling pipeline.

## Pipeline Layers

```text
                  Incoming Task
                        │
                        ▼
           [ 1. Eligibility Filter ]
     (Checks GPU, RAM, tags, online status)
                        │
                        ▼
          [ 2. Base & EWMA Score ]
      (Hardware capacity × speed ratio)
                        │
                        ▼
     [ 3. Deficit Round Robin (DRR) ]
     (Adaptive quantum, starvation prevention)
                        │
                        ▼
      [ 4. Contract-Net Bidding ]
       (Suitability auction over 5 factors)
                        │
                        ▼
   [ 5. MWU Online Weight Adaptation ]
         (Hedge factor loss updates)
                        │
                        ▼
      [ 6. Tabular Q-Learning ]
  (Discretized state bucket -> candidate slot)
                        │
                        ▼
            [ 7. Fallback Policy ]
          (Deterministic fallback)
                        │
                        ▼
             Selected Compute Node
```

## 1. Candidate Eligibility
Excludes nodes that are offline, draining, lacking required GPU hardware, or missing registered handlers for the requested `task_type`.

## 2. Base Score & EWMA Multiplier
- **Base Score**: Computed from CPU cores, clock speed, RAM capacity, and GPU presence.
- **EWMA Multiplier**:
  $$\text{ratio} = \frac{\text{expected\_duration}}{\text{actual\_duration}}$$
  $$\text{multiplier}_{t+1} = \alpha \cdot \text{ratio} + (1 - \alpha) \cdot \text{multiplier}_t$$
  $$\text{effective\_score} = \text{base\_score} \times \text{multiplier}$$

## 3. Deficit Round Robin Fairness
Maintains a per-node deficit counter. Nodes accumulate quantum proportional to their effective score:
$$\text{quantum}_i = \text{base\_quantum} \times \frac{\text{effective\_score}_i}{\text{mean\_effective\_score}}$$
Weak nodes receive fairness correction when their deficit balance accumulates.

## 4. Contract-Net Bidding & MWU
Suitability bids combine 5 factors: CPU, GPU, load, latency, reliability:
$$\text{Bid}_i = \sum_{k=1}^5 w_k \cdot \text{Factor}_{i,k}$$
Weights are updated after task outcome using Multiplicative Weight Update:
$$w_k(t+1) = w_k(t) \cdot \exp(-\eta \cdot \text{loss}_k)$$

## 5. Tabular Q-Learning
State is discretized into 3 buckets: `(score_bucket, load_bucket, priority_bucket)`.
Actions are candidate ranking slots (0: top bid, 1: second bid, 2: third bid).
This bounded action space ensures stability regardless of dynamic node joins or leaves.
