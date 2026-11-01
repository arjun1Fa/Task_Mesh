"""Generates a professional, publication-grade PDF dossier for TaskMesh Code-to-Math & Control Logic."""

import asyncio
import os
import shutil
from playwright.async_api import async_playwright

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>TaskMesh: Code-to-Math & Control Logic Dossier</title>
    <!-- KaTeX CSS & JS for Math Rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
    <style>
        @page {
            size: A4;
            margin: 20mm 16mm 20mm 16mm;
            @bottom-right {
                content: counter(page);
            }
        }
        
        :root {
            --primary: #0f172a;
            --primary-light: #1e293b;
            --accent: #0284c7;
            --accent-light: #e0f2fe;
            --success: #059669;
            --warning: #d97706;
            --danger: #dc2626;
            --border: #cbd5e1;
            --bg-alt: #f8fafc;
            --text-main: #0f172a;
            --text-muted: #475569;
            --code-bg: #f1f5f9;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: var(--text-main);
            line-height: 1.55;
            font-size: 10.5pt;
            margin: 0;
            padding: 0;
        }

        /* Cover Page */
        .cover-page {
            page-break-after: always;
            height: 95vh;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 20px 10px;
            box-sizing: border-box;
        }
        .cover-header {
            border-bottom: 4px solid var(--accent);
            padding-bottom: 25px;
        }
        .badge {
            display: inline-block;
            background: #0284c7;
            color: white;
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 5px 12px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .cover-title {
            font-size: 26pt;
            font-weight: 800;
            line-height: 1.2;
            color: var(--primary);
            margin: 0 0 10px 0;
        }
        .cover-subtitle {
            font-size: 13pt;
            font-weight: 400;
            color: var(--text-muted);
            margin: 0;
            line-height: 1.4;
        }
        .cover-meta-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            background: var(--bg-alt);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin: 40px 0;
        }
        .meta-item {
            font-size: 9.5pt;
        }
        .meta-label {
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 8pt;
            letter-spacing: 0.5px;
        }
        .meta-val {
            font-size: 10pt;
            font-weight: 600;
            color: var(--primary);
            margin-top: 3px;
        }
        .cover-abstract {
            background: #f0fdf4;
            border-left: 4px solid var(--success);
            padding: 15px 20px;
            border-radius: 0 6px 6px 0;
            font-size: 9.5pt;
            color: #166534;
            line-height: 1.5;
        }
        .cover-footer {
            border-top: 1px solid var(--border);
            padding-top: 15px;
            font-size: 8.5pt;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
        }

        /* Typography & Section Structure */
        h1 {
            color: var(--primary);
            font-size: 18pt;
            font-weight: 800;
            border-bottom: 2px solid var(--accent);
            padding-bottom: 6px;
            margin-top: 32px;
            margin-bottom: 14px;
            page-break-after: avoid;
        }
        h2 {
            color: var(--primary-light);
            font-size: 13.5pt;
            font-weight: 700;
            border-left: 4px solid var(--accent);
            padding-left: 10px;
            margin-top: 24px;
            margin-bottom: 10px;
            page-break-after: avoid;
        }
        h3 {
            color: #334155;
            font-size: 11pt;
            font-weight: 700;
            margin-top: 16px;
            margin-bottom: 6px;
            page-break-after: avoid;
        }
        p {
            margin: 0 0 10px 0;
            text-align: justify;
        }
        ul, ol {
            margin: 0 0 12px 0;
            padding-left: 22px;
        }
        li {
            margin-bottom: 4px;
        }

        /* Code & Monospace */
        code {
            font-family: "JetBrains Mono", "Fira Code", Consolas, Monaco, monospace;
            font-size: 9pt;
            background: var(--code-bg);
            color: #0369a1;
            padding: 2px 5px;
            border-radius: 3px;
            border: 1px solid #e2e8f0;
        }
        pre {
            background: #0f172a;
            color: #f8fafc;
            font-family: "JetBrains Mono", Consolas, monospace;
            font-size: 8.5pt;
            line-height: 1.45;
            padding: 12px 14px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 10px 0 14px 0;
            page-break-inside: avoid;
        }
        pre code {
            background: transparent;
            color: inherit;
            padding: 0;
            border: none;
        }

        /* Math Display Boxes */
        .math-box {
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-left: 4px solid #0284c7;
            padding: 10px 14px;
            margin: 10px 0 14px 0;
            border-radius: 0 6px 6px 0;
            page-break-inside: avoid;
        }
        .math-title {
            font-weight: 700;
            font-size: 9pt;
            color: #0369a1;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 14px 0;
            font-size: 8pt;
            page-break-inside: avoid;
        }
        th, td {
            border: 1px solid #cbd5e1;
            padding: 4px 7px;
            text-align: left;
            vertical-align: middle;
        }
        th {
            background: #f1f5f9;
            color: var(--primary);
            font-weight: 700;
        }
        tr:nth-child(even) {
            background: #f8fafc;
        }

        /* Diagrams & SVGs */
        .diagram-container {
            text-align: center;
            margin: 16px 0;
            page-break-inside: avoid;
        }
        .diagram-container svg {
            max-width: 100%;
            height: auto;
        }

        /* Callout Notes */
        .callout {
            border-radius: 6px;
            padding: 10px 14px;
            margin: 12px 0;
            font-size: 9pt;
            page-break-inside: avoid;
        }
        .callout-info {
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            color: #1e40af;
        }
        .callout-warning {
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            color: #92400e;
        }
        .callout-success {
            background: #f0fdf4;
            border-left: 4px solid #10b981;
            color: #065f46;
        }

        .page-break {
            page-break-before: always;
        }
    </style>
</head>
<body>

<!-- ========================================================================= -->
<!-- COVER PAGE                                                                -->
<!-- ========================================================================= -->
<div class="cover-page">
    <div class="cover-header">
        <span class="badge">Official Technical Whitepaper</span>
        <h1 class="cover-title">TASKMESH: CODE-TO-MATH & DISTRIBUTED CONTROL LOGIC DOSSIER</h1>
        <p class="cover-subtitle">A Rigorous Source-Code Audit, Algorithmic Deconstruction, Mathematical Pipeline, and Control Plane Analysis of the TaskMesh Distributed Orchestration Platform</p>
    </div>

    <div class="cover-meta-grid">
        <div class="meta-item">
            <div class="meta-label">Target System</div>
            <div class="meta-val">TaskMesh Distributed Task Orchestrator</div>
        </div>
        <div class="meta-item">
            <div class="meta-label">Git Branch & HEAD</div>
            <div class="meta-val">feature/wireless-inference (Commit a941217)</div>
        </div>
        <div class="meta-item">
            <div class="meta-label">Evaluation Class</div>
            <div class="meta-val">Distributed Systems & AI Inference Orchestration</div>
        </div>
        <div class="meta-item">
            <div class="meta-label">Audit Date</div>
            <div class="meta-val">November 1, 2026</div>
        </div>
        <div class="meta-item">
            <div class="meta-label">Security & Integrity Status</div>
            <div class="meta-val">Post-Audit Hardened & Verified (79/79 Tests Passing)</div>
        </div>
        <div class="meta-item">
            <div class="meta-label">Author / Role</div>
            <div class="meta-val">Principal Distributed Systems Architect & Lead Auditor</div>
        </div>
    </div>

    <div class="cover-abstract">
        <strong>Executive Abstract:</strong> This dossier provides an exhaustive code-level and mathematical audit of TaskMesh, a distributed, heterogeneous task orchestration system for ordinary LAN and Wi-Fi networks. It details the 7-stage scheduling pipeline—integrating hardware base scoring, EWMA dynamic adaptation, Deficit Round Robin (DRR) max-min fairness, Contract-Net 5-factor bidding, Multiplicative Weights Update (MWU/Hedge), Tabular Q-Learning (Contextual Bandits), and Network-Aware Wireless Cost Estimation. It traces orchestrator dispatch, lease fencing, fault recovery, dual-channel 48-byte binary framing (<code>TMCH</code>), worker concurrency offloading, and cryptographic HMAC-SHA256 replay protection. A complete numerical trace verifies exact execution values using production code constants.
    </div>

    <div class="cover-footer">
        <div>Confidential & Proprietary &bull; Academic & Evaluator Reference</div>
        <div>Page 1 of Dossier</div>
    </div>
</div>

<!-- ========================================================================= -->
<!-- SECTION 1: THE COMPLETE SCHEDULING MATH PIPELINE                          -->
<!-- ========================================================================= -->
<h1>1. The Complete Scheduling Math Pipeline</h1>
<p>
    The core scheduling pipeline executes in <code>taskmesh/scheduler/adaptive.py</code> inside <code>AdaptiveScheduler.select_node()</code> (lines 77&ndash;201), with post-execution feedback processed in <code>record_task_outcome()</code> (lines 203&ndash;248). The pipeline operates over 7 sequential phases:
</p>

<div class="diagram-container">
    <svg width="700" height="110" viewBox="0 0 700 110" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#0284c7;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#0369a1;stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect x="5" y="25" width="85" height="55" rx="5" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
        <text x="47" y="47" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle" fill="#0f172a">1. Eligibility</text>
        <text x="47" y="62" font-size="7.5" font-family="sans-serif" text-anchor="middle" fill="#475569">filter_eligible</text>
        
        <path d="M 90 52 L 105 52" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>
        
        <rect x="105" y="25" width="85" height="55" rx="5" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
        <text x="147" y="47" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle" fill="#0f172a">2. Base & EWMA</text>
        <text x="147" y="62" font-size="7.5" font-family="sans-serif" text-anchor="middle" fill="#475569">Hardware Score</text>

        <path d="M 190 52 L 205 52" stroke="#64748b" stroke-width="1.5"/>

        <rect x="205" y="25" width="85" height="55" rx="5" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
        <text x="247" y="47" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle" fill="#0f172a">3. DRR Gate</text>
        <text x="247" y="62" font-size="7.5" font-family="sans-serif" text-anchor="middle" fill="#475569">Deficit Check</text>

        <path d="M 290 52 L 305 52" stroke="#64748b" stroke-width="1.5"/>

        <rect x="305" y="25" width="85" height="55" rx="5" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
        <text x="347" y="47" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle" fill="#0f172a">4. Contract-Net</text>
        <text x="347" y="62" font-size="7.5" font-family="sans-serif" text-anchor="middle" fill="#475569">5-Factor Bidding</text>

        <path d="M 390 52 L 405 52" stroke="#64748b" stroke-width="1.5"/>

        <rect x="405" y="25" width="85" height="55" rx="5" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
        <text x="447" y="47" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle" fill="#0f172a">5. MWU Hedge</text>
        <text x="447" y="62" font-size="7.5" font-family="sans-serif" text-anchor="middle" fill="#475569">Factor Weights</text>

        <path d="M 490 52 L 505 52" stroke="#64748b" stroke-width="1.5"/>

        <rect x="505" y="25" width="85" height="55" rx="5" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
        <text x="547" y="47" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle" fill="#0f172a">6. Q-Learning</text>
        <text x="547" y="62" font-size="7.5" font-family="sans-serif" text-anchor="middle" fill="#475569">Slot Selection</text>

        <path d="M 590 52 L 605 52" stroke="#64748b" stroke-width="1.5"/>

        <rect x="605" y="25" width="90" height="55" rx="5" fill="url(#grad1)" stroke="#0284c7" stroke-width="1.5"/>
        <text x="650" y="47" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle" fill="#ffffff">7. Wireless Cost</text>
        <text x="650" y="62" font-size="7.5" font-family="sans-serif" text-anchor="middle" fill="#e0f2fe">Local Override</text>
    </svg>
</div>

<h2>1.1 Stage 1: Eligibility Filtering & Baseline Schedulers</h2>
<p>
    <strong>File & Function:</strong> <code>taskmesh/scheduler/base.py:filter_eligible_nodes()</code> (lines 10&ndash;44).<br>
    Before scoring or bidding, all nodes $\mathcal{N}$ are filtered against 6 hard operational requirements:
</p>

<div class="math-box">
    <div class="math-title">Eligibility Predicate Definition</div>
    $$\text{Eligible}(n, t) \iff \bigwedge_{i=1}^{6} P_i(n, t)$$
    <ol style="margin: 5px 0 0 15px; font-size: 9pt;">
        <li><strong>Status:</strong> $P_1 \iff n.\text{status} \in \{\text{ONLINE}, \text{DEGRADED}\}$. (Draining/offline nodes are rejected).</li>
        <li><strong>Offload Policy:</strong> $P_2 \iff (t.\text{offload\_policy} = \text{LOCAL\_ONLY} \implies n.\text{is\_local} = \text{True})$.</li>
        <li><strong>Workload Handler:</strong> $P_3 \iff (n.\text{supported\_handlers} \neq \emptyset \implies t.\text{task\_type} \in n.\text{supported\_handlers})$.</li>
        <li><strong>GPU Hardware:</strong> $P_4 \iff (t.\text{requires\_gpu} = \text{True} \implies n.\text{has\_gpu} = \text{True})$.</li>
        <li><strong>Memory Headroom:</strong> $P_5 \iff (t.\text{required\_memory\_mb} > 0 \implies n.\text{ram\_available\_mb} \ge t.\text{required\_memory\_mb})$.</li>
        <li><strong>Capability Tags:</strong> $P_6 \iff \forall \tau \in t.\text{required\_capabilities}, \; \tau \in n.\text{tags}$.</li>
    </ol>
</div>

<p>
    <strong>Cold-Start Behavior:</strong> If $\mathcal{N}_{\text{eligible}} = \emptyset$, <code>IneligibleNodeError</code> is raised. The orchestrator re-enqueues the task in <code>PriorityQueue</code> with a 1.0s backoff.
</p>

<p><strong>Baseline Implementations (<code>taskmesh/scheduler/baseline.py</code>):</strong></p>
<ul>
    <li><code>RoundRobinScheduler</code> (lines 14&ndash;38): Maintains thread-safe pointer $i \leftarrow (i + 1) \pmod{|\mathcal{N}_{\text{eligible}}|}$.</li>
    <li><code>LeastLoadedScheduler</code> (lines 41&ndash;80): Evaluates resource load index $\text{Load}(n) = 20.0 \cdot n.\text{active\_tasks} + n.\text{cpu\_percent} + n.\text{ram\_percent}$ (cold-start fallback: 50.0). Selects $\min \text{Load}(n)$, breaking ties within $\Delta = 0.1$ via round-robin.</li>
</ul>

<h2>1.2 Stage 2: Hardware Base Score & EWMA Dynamic Multiplier</h2>
<p>
    <strong>File & Functions:</strong> <code>taskmesh/scoring/base_score.py:compute_base_score()</code> (lines 6&ndash;19) and <code>EWMAUpdater.update_multiplier()</code> (lines 28&ndash;48).
</p>

<div class="math-box">
    <div class="math-title">Hardware Base Capability Score Formula</div>
    $$\text{CPU\_factor}(n) = \frac{n.\text{cpu\_cores} \cdot \left(\frac{n.\text{cpu\_frequency\_mhz}}{2500.0}\right)}{4.0}, \quad \text{RAM\_factor}(n) = \frac{n.\text{ram\_total\_mb}}{4096.0}$$
    $$\text{GPU\_factor}(n) = \begin{cases} 2.0, & \text{if } n.\text{has\_gpu} = \text{True} \\ 0.5, & \text{if } n.\text{has\_gpu} = \text{False} \end{cases}$$
    $$\text{BaseScore}(n) = \max\left(0.1, \; \text{round}\Big(0.4 \cdot \text{CPU\_factor}(n) + 0.3 \cdot \text{RAM\_factor}(n) + 0.3 \cdot \text{GPU\_factor}(n), \; 3\Big)\right)$$
</div>

<div class="math-box">
    <div class="math-title">EWMA Online Dynamic Multiplier Formula</div>
    $$\text{EffectiveScore}(n) = \text{round}\Big(\text{BaseScore}(n) \cdot n.\text{performance\_multiplier}, \; 3\Big)$$
    When a task finishes in $t_{\text{actual}}$ with $t_{\text{expected}} = \max(0.1, \; t.\text{timeout\_seconds} \cdot 0.2)$:
    $$\text{ratio} = \begin{cases} 2.0, & \text{if } t_{\text{actual}} \le 0.001\text{ s} \\ \frac{t_{\text{expected}}}{t_{\text{actual}}}, & \text{otherwise} \end{cases}, \quad \text{ratio}_{\text{clamped}} = \max\left(0.2, \; \min\left(5.0, \; \text{ratio}\right)\right)$$
    $$M_{t+1}(n) = \max\left(0.1, \; \min\left(10.0, \; \text{round}\Big(\alpha \cdot \text{ratio}_{\text{clamped}} + (1 - \alpha) \cdot M_t(n), \; 4\Big)\right)\right)$$
    <em>Constants:</em> Smoothing factor $\alpha = 0.20$ (configurable via <code>TASKMESH_EWMA_ALPHA</code>). Cold-start $M_0 = 1.0$.
</div>

<h2>1.3 Stage 3: Deficit Round Robin (DRR) Fairness Engine</h2>
<p>
    <strong>File & Methods:</strong> <code>taskmesh/fairness/drr.py:DRRFairnessManager</code> (lines 9&ndash;77); invoked in <code>adaptive.py:84&ndash;87</code>.
</p>
<p>
    DRR ensures max-min fairness across heterogeneous workers, preventing starvation of lower-spec nodes while allowing powerful nodes to service proportional share.
</p>

<div class="math-box">
    <div class="math-title">DRR Deficit & Quantum Formulas</div>
    <strong>1. Deficit Check:</strong> Candidate must meet cost $C = 1.0$: $\mathcal{N}_{\text{fair}} = \{n \in \mathcal{N}_{\text{eligible}} \mid D_n \ge C\}$.<br>
    <strong>2. Round Replenishment:</strong> If $\mathcal{N}_{\text{fair}} = \emptyset$ (round exhausted), all candidates receive an adaptive quantum:
    $$\bar{S} = \max\left(0.01, \; \frac{1}{|\mathcal{N}_{\text{eligible}}|} \sum_{n \in \mathcal{N}_{\text{eligible}}} \text{EffectiveScore}(n)\right)$$
    $$Q_n = Q_{\text{base}} \cdot \left(\frac{\text{EffectiveScore}(n)}{\bar{S}}\right) \quad (\text{with } Q_{\text{base}} = 1.0)$$
    $$D_n \leftarrow D_n + Q_n \quad \forall n \in \mathcal{N}_{\text{eligible}}$$
    <strong>3. Deficit Deduction:</strong> Upon selecting node $n^*$, deficit is decremented in line 177: $D_{n^*} \leftarrow \max(0.0, \; D_{n^*} - C)$.
</div>

<h2>1.4 Stage 4: Contract Net 5-Factor Bidding</h2>
<p>
    <strong>File & Function:</strong> <code>taskmesh/bidding/contract_net.py:calculate_node_bid()</code> (lines 7&ndash;67).<br>
    Every candidate in $\mathcal{N}_{\text{fair}}$ submits a 5-factor normalized suitability bid:
</p>

<div class="math-box">
    <div class="math-title">5-Factor Bidding Normalization Equations</div>
    $$\text{CPU Factor:} \quad f_{\text{cpu}} = \min\left(1.0, \; \frac{n.\text{cpu\_cores}}{16.0}\right)$$
    $$\text{GPU Factor:} \quad f_{\text{gpu}} = \begin{cases} 1.0, & \text{if } t.\text{requires\_gpu} \land n.\text{has\_gpu} \\ 0.0, & \text{if } t.\text{requires\_gpu} \land \neg n.\text{has\_gpu} \\ 0.5, & \text{if } \neg t.\text{requires\_gpu} \end{cases}$$
    $$\text{Load Headroom:} \quad f_{\text{load}} = \begin{cases} \max\left(0.0, \; 1.0 - \frac{n.\text{cpu\_percent} + n.\text{ram\_percent}}{200.0}\right), & \text{if telemetry} \\ 0.8, & \text{cold-start fallback} \end{cases}$$
    $$\text{Latency \& Bandwidth:} \quad f_{\text{lat}} = \begin{cases} 1.0, & \text{if local node} \\ \max\left(0.0, \min(1.0, 0.7 R + 0.3 B)\right), & \text{if remote telemetry} \\ 0.9, & \text{fallback} \end{cases}$$
    $$\text{where } R = \max\left(0.0, 1.0 - \frac{\text{RTT}_{\text{eff}}}{200.0}\right), \quad B = \min\left(1.0, \frac{n.\text{upload\_mbps\_ewma}}{100.0}\right)$$
    $$\text{Reliability Factor:} \quad f_{\text{rel}} = \begin{cases} \frac{n.\text{total\_completed}}{n.\text{total\_completed} + n.\text{total\_failed}}, & \text{if tasks completed} > 0 \\ 0.95, & \text{cold-start fallback} \end{cases}$$
    $$\mathbf{\text{Final Bid:}} \quad \text{FinalBid}(n) = \text{round}\left(\left(\sum_{k} w_k f_k\right) \cdot \text{EffectiveScore}(n), \; 4\right)$$
</div>

<p>Candidates are sorted in descending order of $\text{FinalBid}(n)$: $\mathcal{R} = [n_{(0)}, n_{(1)}, n_{(2)}, \dots]$.</p>

<h2>1.5 Stage 5: Multiplicative Weights Update (MWU / Hedge)</h2>
<p>
    <strong>File & Methods:</strong> <code>taskmesh/learning/mwu.py:MWUWeightLearner</code> (lines 7&ndash;42); invoked in <code>adaptive.py:223&ndash;234</code>.<br>
    MWU continuously updates factor weights $\mathbf{w} \in \mathbb{R}^5$ using online exponential hedging with learning rate $\eta = 0.10$:
</p>

<div class="math-box">
    <div class="math-title">MWU Loss & Exponential Update Formulas</div>
    $$L_{\text{time}} = \min\left(1.0, \; \frac{t_{\text{actual}}}{\max(1.0, \; t.\text{timeout\_seconds})}\right), \quad L_{\text{status}} = \begin{cases} 0.0, & \text{if Success} \\ 1.0, & \text{if Failure} \end{cases}$$
    $$\ell_{\text{cpu}} = 0.5 \cdot L_{\text{time}}, \quad \ell_{\text{gpu}} = \begin{cases} 0.8 \cdot L_{\text{status}}, & \text{if } t.\text{requires\_gpu} \\ 0.2, & \text{otherwise} \end{cases}, \quad \ell_{\text{load}} = L_{\text{time}}$$
    $$\ell_{\text{lat}} = \min\left(1.0, \; \frac{n.\text{network\_latency\_ms}}{100.0}\right) \quad (\text{fallback: } 10.0\text{ms} \implies 0.10), \quad \ell_{\text{rel}} = L_{\text{status}}$$
    $$\tilde{w}_k^{(t+1)} = w_k^{(t)} \cdot \exp\left(-\eta \cdot \ell_k\right), \quad w_k^{(t+1)} = \text{round}\left(\frac{\tilde{w}_k^{(t+1)}}{\sum_j \tilde{w}_j^{(t+1)}}, \; 4\right)$$
</div>

<h2>1.6 Stage 6: Tabular Q-Learning (Contextual Bandit Slot Selection)</h2>
<p>
    <strong>File & Methods:</strong> <code>taskmesh/learning/qlearning.py:QLearningScheduler</code> (lines 8&ndash;126); invoked in <code>adaptive.py:105&ndash;118, 237&ndash;248</code>.<br>
    Actions select candidate ranking slots: $a \in \{0 \text{ (Top Rank)}, 1 \text{ (2nd Rank)}, 2 \text{ (3rd Rank)}\}$.
</p>

<div class="math-box">
    <div class="math-title">27-State Bucket Discretization & Bellman Update</div>
    $$s = (b_{\text{score}}, \; b_{\text{load}}, \; b_{\text{prio}}) \in \{0, 1, 2\}^3 \implies 27 \text{ States}$$
    <ul>
        <li><strong>Score Bucket ($b_{\text{score}}$):</strong> $0$ if $\text{EffectiveScore} < 0.8$; $1$ if $0.8 \le \text{EffectiveScore} \le 1.5$; $2$ if $\text{EffectiveScore} > 1.5$.</li>
        <li><strong>Load Bucket ($b_{\text{load}}$):</strong> $0$ if $\text{AvgLoad} < 40\%$; $1$ if $40\% \le \text{AvgLoad} \le 75\%$; $2$ if $\text{AvgLoad} > 75\%$.</li>
        <li><strong>Priority Bucket ($b_{\text{prio}}$):</strong> $0$ if $\text{prio} \le 0$; $1$ if $1 \le \text{prio} \le 10$; $2$ if $\text{prio} > 10$.</li>
    </ul>
    <strong>Reward Function:</strong>
    $$R = \begin{cases} -1.5, & \text{if Failure} \\ 1.5, & \text{if Success and } t_{\text{actual}} < 0.5 \cdot t_{\text{timeout}} \\ 1.0, & \text{if Success and } t_{\text{actual}} \ge 0.5 \cdot t_{\text{timeout}} \end{cases}$$
    <strong>Verification of <code>next_state=None</code>:</strong> In <code>adaptive.py:247</code>, <code>next_state</code> is explicitly passed as <code>None</code>. In <code>qlearning.py:104&ndash;110</code>, this collapses the target to $\text{Target} = R + \gamma \cdot 0.0 = R$, producing pure <strong>Contextual Bandit Q-learning</strong>:
    $$Q(s, a) \leftarrow Q(s, a) + \alpha_{\text{RL}} \cdot \big(R - Q(s, a)\big)$$
    $$\epsilon \leftarrow \max\left(\epsilon_{\min}, \; \epsilon \cdot \lambda_{\text{decay}}\right) \quad (\alpha_{\text{RL}} = 0.1, \gamma = 0.9, \epsilon_0 = 0.15, \lambda_{\text{decay}} = 0.995, \epsilon_{\min} = 0.01)$$
</div>

<h2>1.7 Stage 7: Wireless Network Cost Estimator & Local Override</h2>
<p>
    <strong>File & Functions:</strong> <code>taskmesh/wireless/estimator.py:estimate_remote_execution_time()</code> (lines 134&ndash;161) and <code>compare_local_vs_remote()</code> (lines 184&ndash;230).<br>
    The estimator compares predicted remote execution latency against on-device local execution:
</p>

<div class="math-box">
    <div class="math-title">Latency Decomposition & Override Condition</div>
    $$T_{\text{remote}} = T_{\text{upload}} + T_{\text{rtt}} + T_{\text{queue}} + T_{\text{infer}} + T_{\text{download}}$$
    $$T_{\text{upload}} = \left(\frac{P \cdot 8}{\max(0.5, \; n.\text{upload\_mbps\_ewma}) \cdot 10^6}\right) \cdot 1000\text{ ms}, \quad T_{\text{rtt}} = n.\text{rtt\_ms\_ewma}$$
    $$T_{\text{queue}} = n.\text{active\_tasks} \cdot 25.0\text{ ms}, \quad T_{\text{infer}} = \frac{t_{\text{base}}}{\max(0.1, \; n.\text{performance\_multiplier})}$$
    $$\text{where } t_{\text{base}} = \begin{cases} 28.0\text{ ms}, & \text{if AI workload with GPU} \\ 135.0\text{ ms}, & \text{if AI workload without GPU} \\ 50.0\text{ ms}, & \text{generic task} \end{cases}$$
    $$T_{\text{download}} = \left(\frac{1024 \cdot 8}{\max(0.5, \; n.\text{download\_mbps\_ewma}) \cdot 10^6}\right) \cdot 1000\text{ ms}$$
    $$T_{\text{local}} = n_{\text{local}}.\text{active\_tasks} \cdot 25.0\text{ ms} + \frac{t_{\text{base}}(n_{\text{local}})}{\max(0.1, \; n_{\text{local}}.\text{performance\_multiplier})}$$
    $$\mathbf{\text{Override Condition:}} \quad \text{If } n_{\text{local}} \neq \text{None} \land T_{\text{local}} \le T_{\text{remote}} \implies \mathbf{\text{Execute Locally on } n_{\text{local}}}$$
</div>

<!-- ========================================================================= -->
<!-- SECTION 2: ORCHESTRATOR CONTROL LOGIC                                     -->
<!-- ========================================================================= -->
<div class="page-break"></div>
<h1>2. Orchestrator Control Logic</h1>
<p>
    The Orchestrator Control Plane (<code>taskmesh/orchestrator/runtime.py</code>) coordinates cluster state, persistence, lease management, and failure recovery.
</p>

<h2>2.1 Task Ingestion, Idempotency & Persistence</h2>
<ol>
    <li><strong>Client Ingress:</strong> REST <code>POST /v1/tasks</code> or CLI submits <code>TaskCreate</code> to <code>submit_task()</code> (lines 278&ndash;345).</li>
    <li><strong>Idempotency Validation:</strong> <code>IdempotencyStore.get(key)</code> checks memory cache. If present, returns existing task immediately without re-executing.</li>
    <li><strong>Binary Payload Staging:</strong> If binary bytes accompany submission, <code>BinaryPayloadStore.add_payload()</code> enforces <code>max_payload_size_bytes</code> (50 MB limit), computes SHA-256 digest, splits into 64 KB slices, and attaches <code>BinaryPayloadMeta</code>.</li>
    <li><strong>Durable SQLite Commit:</strong> <code>TaskRepository.save()</code> persists task to SQLite before enqueueing.</li>
    <li><strong>Priority Enqueue:</strong> If <code>scheduled_at > now</code>, staged in <code>_delayed_tasks</code>; else status set to <code>PENDING</code> and pushed to <code>PriorityQueue</code>.</li>
</ol>

<h2>2.2 The Dispatch Loop, Attempt IDs & Leases</h2>
<p>
    Inside <code>_dispatch_loop()</code> (lines 706&ndash;826):
</p>
<ol>
    <li>Pulls highest-priority pending task via <code>self.queue.dequeue(timeout=0.5)</code>.</li>
    <li>Queries online nodes from <code>NodeRegistry</code> and calls <code>scheduler.select_node(task, nodes)</code>.</li>
    <li><strong>Attempt ID & Lease Allocation (<code>models.py:140&ndash;155</code>):</strong>
        <pre><code>def next_attempt(self, node_id: str, lease_duration_seconds: float) -> str:
    self.current_attempt += 1
    self.current_attempt_id = f"{self.id}-A{self.current_attempt}"  # e.g. task_123-A1
    self.assigned_node_id = node_id
    now = utc_now()
    expires = datetime.fromtimestamp(now.timestamp() + lease_duration_seconds, timezone.utc)
    self.active_lease = TaskLease(task_id=self.id, attempt_id=self.current_attempt_id,
                                 node_id=node_id, granted_at=now, expires_at=expires)
    self.status = TaskStatus.RUNNING
    return self.current_attempt_id</code></pre>
    </li>
    <li>Signs <code>TaskAssignmentPayload</code> with HMAC-SHA256 and transmits over WebSocket.</li>
    <li>If binary payload exists, loops through chunks and calls <code>_send_websocket_bytes(ws, create_binary_chunk_frame(...))</code>.</li>
</ol>

<h2>2.3 Result Validation & Stale Attempt Fencing</h2>
<p>
    When a worker completes a task and returns <code>TASK_COMPLETED</code> (lines 926&ndash;1000):
</p>
<pre><code># Stale Attempt Validation Fencing (line 940)
if task.current_attempt_id and task.current_attempt_id != attempt_id:
    logger.warning(f"Discarding stale completed result for task [{task_id}] attempt [{attempt_id}]")
    return</code></pre>
<p>
    If attempt <code>A1</code> timed out or failed over, and <code>A2</code> was dispatched to another node, late responses from <code>A1</code> are fenced off and discarded without corrupting cluster state.
</p>

<h2>2.4 Fault Recovery, Heartbeats & High Availability</h2>
<ul>
    <li><strong>Heartbeat Timeout (<code>_health_monitor_loop</code>, lines 1081&ndash;1106):</strong> Runs every 3.0s. If <code>now - node.last_heartbeat > 9.0s</code>, node is marked <code>OFFLINE</code>.</li>
    <li><strong>Failed Node Task Recovery (<code>_recover_tasks_for_failed_node</code>, lines 1107&ndash;1129):</strong> Finds all tasks in <code>RUNNING</code> status on failed node, attaches <code>latest_checkpoint</code> if present, resets to <code>PENDING</code>, and re-enqueues into <code>PriorityQueue</code>.</li>
    <li><strong>Lease Expiration Sweep (<code>_lease_checker_loop</code>, lines 1130&ndash;1147):</strong> Every 5.0s, reclaims tasks whose lease expired in SQLite, re-enqueuing them.</li>
    <li><strong>Exponential Backoff Retry (<code>taskmesh/retry/runner.py</code>):</strong>
        $$\text{delay} = \min\left(t_{\max}, \; t_{\text{base}} \cdot 2^{\text{attempt}-1}\right) \times \text{Uniform}(0.5, 1.0)$$
        If retries exceed <code>max_attempts</code> (3), task is moved to Dead-Letter Queue (<code>DLQManager</code>).
    </li>
    <li><strong>Primary/Standby Replication (lines 242&ndash;270):</strong> Standby polls <code>/v1/standby/snapshot</code> every 5.0s. If 3 consecutive probes fail, it promotes itself to Primary, adopts orphaned tasks, and launches dispatch loops.</li>
</ul>

<!-- ========================================================================= -->
<!-- SECTION 3: WORKER NODE & AGENT CONTROL LOGIC                              -->
<!-- ========================================================================= -->
<div class="page-break"></div>
<h1>3. Worker Node & Agent Control Logic</h1>

<h2>3.1 Hardware Registration & Dual Telemetry Loops</h2>
<p>
    In <code>taskmesh/node/agent.py</code>:
</p>
<ul>
    <li><strong>Hardware Profiling:</strong> <code>profile_hardware()</code> queries <code>psutil</code> for cores, clock speed, and RAM, and executes <code>torch.cuda.is_available()</code> to detect VRAM and GPU architecture.</li>
    <li><strong>Registration:</strong> Sends <code>REGISTER_NODE</code> with capabilities and join token; awaits signed <code>REGISTER_ACK</code>.</li>
    <li><strong>Heartbeat Loop (lines 199&ndash;212):</strong> Emits <code>HEARTBEAT</code> every 3.0s. Every 3rd heartbeat, sends <code>PING</code> to compute round-trip time (RTT).</li>
    <li><strong>Telemetry Loop (lines 213&ndash;226):</strong> Transmits CPU %, RAM %, and active worker count every 2.0s via <code>collect_telemetry()</code>.</li>
</ul>

<h2>3.2 Dual-Channel Transport & TMCH Binary Protocol</h2>
<p>
    TaskMesh multiplexes text and binary frames over a single WebSocket connection:
</p>
<ul>
    <li><strong>Control Plane Channel:</strong> Text frames encode JSON <code>ProtocolMessage</code> envelopes.</li>
    <li><strong>Data Plane Channel:</strong> Binary frames transport raw bytes prefixed with a 48-byte header.</li>
</ul>

<div class="math-box">
    <div class="math-title">48-Byte TMCH Binary Header Struct Specification</div>
    <strong>Struct Format:</strong> <code>>4s36sII</code> (Big-endian, struct size: $4 + 36 + 4 + 4 = 48\text{ bytes}$)
    <table style="margin: 8px 0 4px 0;">
        <tr><th>Offset</th><th>Field</th><th>Type</th><th>Description</th></tr>
        <tr><td>0 &ndash; 3</td><td><code>magic</code></td><td>char[4]</td><td>ASCII magic constant: <code>b"TMCH"</code></td></tr>
        <tr><td>4 &ndash; 39</td><td><code>task_id</code></td><td>char[36]</td><td>UUID task identifier (space-padded)</td></tr>
        <tr><td>40 &ndash; 43</td><td><code>chunk_index</code></td><td>uint32</td><td>Zero-based chunk sequence index</td></tr>
        <tr><td>44 &ndash; 47</td><td><code>total_chunks</code></td><td>uint32</td><td>Total chunk count for complete payload</td></tr>
        <tr><td>48 &ndash; END</td><td><code>chunk_data</code></td><td>bytes</td><td>Raw payload slice (default: 65,536 bytes / 64 KB)</td></tr>
    </table>
</div>

<p>
    <strong>Reassembly & Verification:</strong> <code>ChunkAssembler.add_chunk()</code> buffers slices. When all chunks arrive, it concatenates them and executes constant-time verification:
    <code>hmac.compare_digest(hashlib.sha256(data).hexdigest().lower(), expected_sha256)</code>.
    Upon verification, it triggers <code>self._payload_events[task_id].set()</code>, releasing the worker thread.
</p>

<h2>3.3 Concurrency & Execution Architecture</h2>
<p>
    In <code>taskmesh/node/worker_pool.py:65&ndash;87</code>:
</p>
<pre><code>async def _run():
    async with self._semaphore:  # Throttled by concurrency limit
        if inspect.iscoroutinefunction(handler):
            return await handler(assignment.payload, **kwargs)
        else:
            # Offload heavy synchronous AI / CPU inference to thread pool
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: handler(assignment.payload, **kwargs)
            )</code></pre>
<div class="callout callout-info">
    <strong>Thread Isolation Guarantee:</strong> Heavy computer vision and tensor inference (OpenCV image decoding, Ultralytics YOLO forward passes) are executed in a dedicated <code>ThreadPoolExecutor</code>. This guarantees the primary <code>asyncio</code> event loop is never blocked, preserving millisecond-level responsiveness for WebSocket heartbeats, ping frames, and abort signals.
</div>

<p><strong>Missing GPU / Weight File Graceful Degradation (<code>handlers/ai_inference.py</code>):</strong></p>
<ol>
    <li>Attempts to load YOLO weights (e.g. <code>yolov8n.pt</code>). If Ultralytics is missing or weights cannot be loaded, catches exception and returns <code>None</code>.</li>
    <li>If binary image was decoded via OpenCV, produces synthetic structured detection (<code>{"class": "object", "confidence": 0.94, "bbox": [24.0, 32.0, 220.0, 310.0]}</code>).</li>
    <li>Attempts PyTorch Conv2D tensor execution. If CUDA is present and requested, runs on <code>cuda</code>; else falls back to <code>torch-cpu</code>.</li>
    <li>If PyTorch is not installed, falls back to NumPy matrix generation (<code>numpy-cpu</code>).</li>
</ol>

<!-- ========================================================================= -->
<!-- SECTION 4: SECURITY & INTEGRITY LOGIC                                     -->
<!-- ========================================================================= -->
<div class="page-break"></div>
<h1>4. Security & Integrity Logic</h1>
<p>
    The security subsystem (<code>taskmesh/security/hmac_auth.py</code>) provides end-to-end cryptographic integrity, message authentication, and replay protection for all control plane traffic.
</p>

<h2>4.1 Canonical Deterministic Serialization</h2>
<p>
    To prevent signature mismatch across different JSON encoders, messages are packed into a canonical pipe-delimited byte string:
</p>
<div class="math-box">
    <div class="math-title">Canonical Message Serialization String</div>
    $$\text{CanonicalBytes} = \text{version} \parallel \text{message\_id} \parallel \text{message\_type} \parallel \text{node\_id} \parallel \text{timestamp} \parallel \text{seq} \parallel \text{payload\_json}$$
    <em>Serialization Rule:</em> <code>json.dumps(msg.payload, sort_keys=True, separators=(",", ":"))</code>
</div>

<h2>4.2 HMAC-SHA256 Signing & Verification</h2>
$$\text{Signature} = \text{HMAC-SHA256}\Big(\text{SecretKey}, \; \text{CanonicalBytes}\Big)$$
<p>
    Signatures are verified using <code>hmac.compare_digest(msg.signature, expected)</code> to eliminate timing side-channel attacks.
</p>

<h2>4.3 Multi-Layered Replay Protection Pipeline</h2>
<p>
    When <code>secure_mode == True</code> (lines 60&ndash;94), 4 mandatory security checks are evaluated:
</p>
<ol>
    <li><strong>HMAC Signature Verification:</strong> Rejects untrusted or tampered packets (401/1008).</li>
    <li><strong>Timestamp Freshness Check:</strong>
        $$\Delta t = |t_{\text{current}} - t_{\text{msg}}| \le 60.0\text{ seconds}$$
        Packets older than 60 seconds are rejected with <code>"Message timestamp expired"</code>.
    </li>
    <li><strong>Message ID Deduplication:</strong> Verifies $\text{message\_id} \notin \mathcal{S}_{\text{seen\_ids}}$. Reused message IDs trigger immediate rejection.</li>
    <li><strong>Per-Node Monotonic Sequence Enforcement:</strong>
        $$\text{seq}_{\text{incoming}} > \text{last\_seq}(node\_id)$$
        If $\text{seq}_{\text{incoming}} \le \text{last\_seq}(node\_id)$, packet is rejected with <code>"Replay attack detected: non-monotonic sequence"</code>.
    </li>
</ol>

<!-- ========================================================================= -->
<!-- SECTION 5: STEP-BY-STEP NUMERICAL TRACE                                   -->
<!-- ========================================================================= -->
<div class="page-break"></div>
<h1>5. End-to-End Numerical Walkthrough Using Code Constants</h1>
<p>
    We trace one complete 300 KB (<code>307,200</code> bytes) image inference task arriving at the orchestrator with 3 active nodes.
</p>

<h2>5.1 Initial Parameters & Cluster Specifications</h2>
<ul>
    <li><strong>Task $t$:</strong> <code>task_type="image_inference"</code>, <code>priority=5</code>, <code>timeout_seconds=10.0</code>, <code>requires_gpu=False</code>, <code>offload_policy=WIRELESS_ALLOWED</code>, payload: 307,200 bytes.</li>
    <li><strong>Node A (Remote GPU Rig):</strong> 16 cores @ 3500 MHz, 32,768 MB RAM, GPU: Yes, Local: No. Telemetry: CPU 20%, RAM 25%, Tasks: 0, RTT: 10ms, Upload: 80 Mbps, Download: 100 Mbps, Completed: 45, Failed: 0, $M_0 = 1.0$.</li>
    <li><strong>Node B (Remote CPU Server):</strong> 32 cores @ 2800 MHz, 65,536 MB RAM, GPU: No, Local: No. Telemetry: CPU 30%, RAM 30%, Tasks: 1, RTT: 15ms, Upload: 60 Mbps, Download: 80 Mbps, Completed: 30, Failed: 2, $M_0 = 1.0$.</li>
    <li><strong>Node C (Local Laptop Host):</strong> 4 cores @ 2400 MHz, 8,192 MB RAM, GPU: No, Local: Yes. Telemetry: CPU 45%, RAM 60%, Tasks: 0, RTT: 0.5ms, Upload: 1000 Mbps, Download: 1000 Mbps, Completed: 10, Failed: 0, $M_0 = 1.0$.</li>
</ul>

<h2>5.2 Step-by-Step Mathematical Calculation</h2>

<h3>Step 1: Eligibility Filtering</h3>
<p>All nodes support <code>image_inference</code>, meet memory bounds, and <code>requires_gpu=False</code> $\implies \mathcal{N}_{\text{eligible}} = \{\text{Node A}, \text{Node B}, \text{Node C}\}$.</p>

<h3>Step 2: Base Capability Score Computation</h3>
<ul>
    <li><strong>Node A:</strong>
        $\text{CPU} = \frac{16 \cdot (3500/2500)}{4.0} = 5.60$, $\text{RAM} = \frac{32768}{4096} = 8.00$, $\text{GPU} = 2.00$<br>
        $\text{BaseScore}(A) = 0.4(5.60) + 0.3(8.00) + 0.3(2.00) = 2.24 + 2.40 + 0.60 = \mathbf{5.240}$
    </li>
    <li><strong>Node B:</strong>
        $\text{CPU} = \frac{32 \cdot (2800/2500)}{4.0} = 8.96$, $\text{RAM} = \frac{65536}{4096} = 16.00$, $\text{GPU} = 0.50$<br>
        $\text{BaseScore}(B) = 0.4(8.96) + 0.3(16.00) + 0.3(0.50) = 3.584 + 4.80 + 0.15 = \mathbf{8.534}$
    </li>
    <li><strong>Node C:</strong>
        $\text{CPU} = \frac{4 \cdot (2400/2500)}{4.0} = 0.96$, $\text{RAM} = \frac{8192}{4096} = 2.00$, $\text{GPU} = 0.50$<br>
        $\text{BaseScore}(C) = 0.4(0.96) + 0.3(2.00) + 0.3(0.50) = 0.384 + 0.60 + 0.15 = \mathbf{1.134}$
    </li>
</ul>

<h3>Step 3: Deficit Round Robin (DRR) Gate</h3>
<p>
    Initial deficits: $D_A = D_B = D_C = 0.0$. Scheduling cost $C = 1.0$. Because all deficits $< 1.0$, round replenishment fires:
    $$\bar{S} = \frac{5.240 + 8.534 + 1.134}{3} = \frac{14.908}{3} = 4.9693$$
    $$Q_A = 1.0 \cdot \frac{5.240}{4.9693} = \mathbf{1.055} \implies D_A = \mathbf{1.055} \ge 1.0 \implies \text{Eligible}$$
    $$Q_B = 1.0 \cdot \frac{8.534}{4.9693} = \mathbf{1.717} \implies D_B = \mathbf{1.717} \ge 1.0 \implies \text{Eligible}$$
    $$Q_C = 1.0 \cdot \frac{1.134}{4.9693} = \mathbf{0.228} \implies D_C = \mathbf{0.228} < 1.0 \implies \text{Not Eligible for this round}$$
    $$\mathcal{N}_{\text{fair}} = \{\text{Node A}, \text{Node B}\}$$
</p>

<h3>Step 4: Contract Net 5-Factor Bidding</h3>
<p>Uniform weights: $w_{\text{cpu}} = w_{\text{gpu}} = w_{\text{load}} = w_{\text{lat}} = w_{\text{rel}} = 0.20$.</p>
<ul>
    <li><strong>Node A:</strong>
        $f_{\text{cpu}} = 1.0$, $f_{\text{gpu}} = 0.5$, $f_{\text{load}} = 1.0 - \frac{20+25}{200} = 0.775$<br>
        $f_{\text{lat}} = 0.7(1 - 10/200) + 0.3(80/100) = 0.7(0.95) + 0.3(0.80) = 0.905$, $f_{\text{rel}} = \frac{45}{45} = 1.0$<br>
        $\text{RawBid}(A) = 0.2(1.0 + 0.5 + 0.775 + 0.905 + 1.0) = 0.8360 \implies \text{FinalBid}(A) = 0.8360 \cdot 5.240 = \mathbf{4.3806}$
    </li>
    <li><strong>Node B:</strong>
        $f_{\text{cpu}} = 1.0$, $f_{\text{gpu}} = 0.5$, $f_{\text{load}} = 1.0 - \frac{30+30}{200} = 0.700$<br>
        $f_{\text{lat}} = 0.7(1 - 15/200) + 0.3(60/100) = 0.7(0.925) + 0.3(0.60) = 0.8275$, $f_{\text{rel}} = \frac{30}{32} = 0.9375$<br>
        $\text{RawBid}(B) = 0.2(1.0 + 0.5 + 0.70 + 0.8275 + 0.9375) = 0.7930 \implies \text{FinalBid}(B) = 0.7930 \cdot 8.534 = \mathbf{6.7675}$
    </li>
</ul>
<p>Ranking order: $\mathcal{R} = [\text{Node B (Slot 0)}, \text{Node A (Slot 1)}]$.</p>

<h3>Step 5: Tabular Q-Learning</h3>
<p>
    Top candidate is Node B ($\text{Score} = 8.534 > 1.5 \implies b_{\text{score}} = 2$; $\text{Load} = 30\% < 40\% \implies b_{\text{load}} = 0$; $\text{Priority} = 5 \implies b_{\text{prio}} = 1$).<br>
    State vector: $s = \mathbf{(2, 0, 1)}$. Action $\mathbf{0}$ is selected (Slot 0: Node B). Candidate by RL: <strong>Node B</strong>.
</p>

<h3>Step 6: Wireless Cost Estimation & Local Override</h3>
<p>Payload size: 307,200 bytes.</p>
<ul>
    <li><strong>Remote Estimate for Node B:</strong>
        $$T_{\text{upload}} = \frac{307,200 \times 8}{60 \times 10^6} \times 1000 = 40.96\text{ ms}$$
        $$T_{\text{rtt}} = 15.00\text{ ms}, \quad T_{\text{queue}} = 1 \times 25.0 = 25.00\text{ ms}, \quad T_{\text{infer}} = \frac{135.0}{1.0} = 135.00\text{ ms}, \quad T_{\text{download}} = 0.10\text{ ms}$$
        $$T_{\text{remote}} = 40.96 + 15.00 + 25.00 + 135.00 + 0.10 = \mathbf{216.06\text{ ms}}$$
    </li>
    <li><strong>Local Estimate for Node C ($n_{\text{local}}$):</strong>
        $$T_{\text{local}} = (0 \times 25.0) + \frac{135.0}{1.0} = \mathbf{135.00\text{ ms}}$$
    </li>
</ul>
<div class="callout callout-success">
    <strong>Local Override Decision:</strong> Since $T_{\text{local}} = 135.00\text{ ms} \le T_{\text{remote}} = 216.06\text{ ms}$, local execution on Node C is <strong>81.06 ms faster</strong> than offloading over Wi-Fi. The orchestrator overrides candidate selection and executes locally on <strong>Node C</strong>!
</div>
<p>DRR Cost deduction: $D_C = \max(0.0, \; 0.228 - 1.0) = \mathbf{0.000}$.</p>

<h3>Step 7: Post-Execution Feedback Updates</h3>
<p>Node C completes execution in $t_{\text{actual}} = 0.130\text{ seconds}$ with <code>success = True</code>:</p>
<ol>
    <li><strong>EWMA Multiplier on Node C:</strong>
        $t_{\text{expected}} = \max(0.1, 10.0 \times 0.2) = 2.0\text{s} \implies \text{ratio} = 2.0 / 0.130 = 15.38 \implies \text{clamped to } 5.0$.<br>
        $M_{\text{new}}(C) = (0.2 \times 5.0) + (0.8 \times 1.0) = \mathbf{1.8000} \implies \text{New EffectiveScore}(C) = 1.134 \times 1.8 = \mathbf{2.041}$.
    </li>
    <li><strong>MWU Weights ($\eta = 0.1$):</strong>
        $L_{\text{time}} = 0.130 / 10.0 = 0.013 \implies \ell_{\text{cpu}} = 0.0065, \ell_{\text{gpu}} = 0.20, \ell_{\text{load}} = 0.013, \ell_{\text{lat}} = 0.005, \ell_{\text{rel}} = 0.0$.<br>
        New normalized weights: $w_{\text{cpu}} = \mathbf{0.2008}, w_{\text{gpu}} = \mathbf{0.1969}, w_{\text{load}} = \mathbf{0.2006}, w_{\text{lat}} = \mathbf{0.2008}, w_{\text{rel}} = \mathbf{0.2009}$.
    </li>
    <li><strong>Q-Learning Bellman Update:</strong>
        $R = 1.0 + 0.5 = 1.5$ (completed in $< 5.0$s). With $\text{Target} = 1.5$:<br>
        $Q((2, 0, 1), 0) \leftarrow 0.0 + 0.1(1.5 - 0.0) = \mathbf{0.1500}$. Epsilon decays: $\epsilon \leftarrow 0.15 \times 0.995 = \mathbf{0.14925}$.
    </li>
</ol>

<h2>5.3 Comparative Scenario: 600 KB Payload with GPU Acceleration</h2>
<p>
    To observe when <strong>remote offloading overtakes local execution</strong>, consider a 600 KB payload (<code>614,400</code> bytes) submitted under identical network conditions:
</p>
<ul>
    <li><strong>Remote Node A (Dedicated GPU):</strong>
        $$T_{\text{upload}} = \frac{614,400 \times 8}{80.0 \times 10^6} \times 1000 = 61.44\text{ ms}, \quad T_{\text{rtt}} = 10.0\text{ ms}, \quad T_{\text{queue}} = 0.0\text{ ms}$$
        $$T_{\text{infer}} = \frac{28.0}{1.0} = \mathbf{28.00\text{ ms}} \text{ (GPU YOLO pass)}, \quad T_{\text{download}} = 0.08\text{ ms}$$
        $$T_{\text{remote}} = 61.44 + 10.0 + 0.0 + 28.0 + 0.08 = \mathbf{99.52\text{ ms}}$$
    </li>
    <li><strong>Local Node C (Laptop CPU):</strong>
        $$T_{\text{local}} = 0.0 + \frac{135.0}{1.0} = \mathbf{135.00\text{ ms}}$$
    </li>
</ul>
<div class="callout callout-info">
    <strong>Remote GPU Offload Selection:</strong> In this scenario, $T_{\text{remote}} = 99.52\text{ ms} < T_{\text{local}} = 135.00\text{ ms}$. The 28ms GPU inference acceleration more than compensates for the 61ms Wi-Fi transfer, saving <strong>35.48 ms</strong>. The system dispatches the 600 KB payload over 10 <code>TMCH</code> binary frames to <strong>Remote Node A</strong>!
</div>

<!-- ========================================================================= -->
<!-- APPENDIX: SOURCE CODE REFERENCE MAPPING                                   -->
<!-- ========================================================================= -->
<div class="page-break"></div>
<h1>Appendix: Source Code Reference Mapping</h1>
<table>
    <tr><th>Pipeline Subsystem</th><th>Source File Path</th><th>Class / Function Name</th><th>Line Ref.</th></tr>
    <tr><td>Eligibility Filter</td><td><code>taskmesh/scheduler/base.py</code></td><td><code>filter_eligible_nodes()</code></td><td>10 &ndash; 44</td></tr>
    <tr><td>Round Robin Baseline</td><td><code>taskmesh/scheduler/baseline.py</code></td><td><code>RoundRobinScheduler.select_node()</code></td><td>21 &ndash; 38</td></tr>
    <tr><td>Least Loaded Baseline</td><td><code>taskmesh/scheduler/baseline.py</code></td><td><code>LeastLoadedScheduler.select_node()</code></td><td>48 &ndash; 80</td></tr>
    <tr><td>Hardware Base Score</td><td><code>taskmesh/scoring/base_score.py</code></td><td><code>compute_base_score()</code></td><td>6 &ndash; 19</td></tr>
    <tr><td>EWMA Performance Multiplier</td><td><code>taskmesh/scoring/base_score.py</code></td><td><code>EWMAUpdater.update_multiplier()</code></td><td>28 &ndash; 48</td></tr>
    <tr><td>DRR Fairness Deficits</td><td><code>taskmesh/fairness/drr.py</code></td><td><code>DRRFairnessManager.get_eligible_with_deficit()</code></td><td>45 &ndash; 60</td></tr>
    <tr><td>Contract-Net 5-Factor Bidding</td><td><code>taskmesh/bidding/contract_net.py</code></td><td><code>calculate_node_bid()</code></td><td>7 &ndash; 67</td></tr>
    <tr><td>MWU Weight Adaptation</td><td><code>taskmesh/learning/mwu.py</code></td><td><code>MWUWeightLearner.update()</code></td><td>25 &ndash; 42</td></tr>
    <tr><td>Tabular Q-Learning</td><td><code>taskmesh/learning/qlearning.py</code></td><td><code>QLearningScheduler.discretize_state(), update()</code></td><td>35 &ndash; 115</td></tr>
    <tr><td>Wireless Cost Estimator</td><td><code>taskmesh/wireless/estimator.py</code></td><td><code>NetworkEstimator.estimate_remote_execution_time()</code></td><td>134 &ndash; 161</td></tr>
    <tr><td>Orchestrator Dispatch Loop</td><td><code>taskmesh/orchestrator/runtime.py</code></td><td><code>OrchestratorRuntime._dispatch_loop()</code></td><td>706 &ndash; 826</td></tr>
    <tr><td>Fencing Lease & Attempt ID</td><td><code>taskmesh/core/models.py</code></td><td><code>Task.next_attempt()</code></td><td>140 &ndash; 155</td></tr>
    <tr><td>Result Validation Fencing</td><td><code>taskmesh/orchestrator/runtime.py</code></td><td><code>OrchestratorRuntime._process_task_completed()</code></td><td>926 &ndash; 965</td></tr>
    <tr><td>Fault Recovery & HA</td><td><code>taskmesh/orchestrator/runtime.py</code></td><td><code>_health_monitor_loop(), _recover_tasks()</code></td><td>1081 &ndash; 1147</td></tr>
    <tr><td>Exponential Retry Runner</td><td><code>taskmesh/retry/runner.py</code></td><td><code>evaluate_retry(), compute_backoff()</code></td><td>17 &ndash; 52</td></tr>
    <tr><td>TMCH 48-Byte Header Protocol</td><td><code>taskmesh/transport/binary_protocol.py</code></td><td><code>create_binary_chunk_frame(), parse...()</code></td><td>28 &ndash; 56</td></tr>
    <tr><td>Payload Store & Assembly</td><td><code>taskmesh/transport/payload_store.py</code></td><td><code>ChunkAssembler.add_chunk()</code></td><td>100 &ndash; 151</td></tr>
    <tr><td>Worker Thread Pool Offload</td><td><code>taskmesh/node/worker_pool.py</code></td><td><code>WorkerPool.execute_assignment()</code></td><td>39 &ndash; 87</td></tr>
    <tr><td>AI Inference Handler Fallbacks</td><td><code>taskmesh/handlers/ai_inference.py</code></td><td><code>image_inference_handler()</code></td><td>23 &ndash; 115</td></tr>
    <tr><td>HMAC & Replay Protection</td><td><code>taskmesh/security/hmac_auth.py</code></td><td><code>SecurityManager.validate_incoming()</code></td><td>60 &ndash; 94</td></tr>
</table>

<div style="margin-top: 30px; text-align: center; font-size: 8.5pt; color: #64748b;">
    &mdash; END OF TECHNICAL DOSSIER &mdash;<br>
    Compiled directly from the TaskMesh Source Tree.
</div>

<script>
    document.addEventListener("DOMContentLoaded", function() {
        renderMathInElement(document.body, {
            delimiters: [
                {left: "$$", right: "$$", display: true},
                {left: "$", right: "$", display: false}
            ],
            throwOnError: false
        });
    });
</script>
</body>
</html>
"""

async def generate_pdf():
    print("Launching Chromium (channel=msedge) via Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge")
        page = await browser.new_page()
        
        print("Rendering HTML dossier content with KaTeX math...")
        await page.set_content(HTML_CONTENT, wait_until="networkidle")
        await page.wait_for_timeout(2000)  # Ensure KaTeX scripts finish rendering formulas
        
        output_pdf_path = os.path.abspath("docs/TASKMESH_CODE_TO_MATH_DOSSIER.pdf")
        os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
        
        print(f"Exporting publication-grade PDF to {output_pdf_path}...")
        await page.pdf(
            path=output_pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "15mm", "bottom": "18mm", "left": "15mm", "right": "15mm"},
            display_header_footer=True,
            header_template='<div style="font-size: 8px; width: 100%; text-align: right; color: #94a3b8; padding-right: 15mm; font-family: sans-serif;">TaskMesh Architecture Dossier &bull; Code-to-Math & Control Logic</div>',
            footer_template='<div style="font-size: 8px; width: 100%; text-align: center; color: #64748b; font-family: sans-serif;">Page <span class="pageNumber"></span> of <span class="totalPages"></span> &nbsp;|&nbsp; TaskMesh Distributed Computing Platform</div>',
        )
        await browser.close()
        print("PDF generated successfully!")

        # Also copy to artifacts directory for direct user convenience
        artifact_dir = os.path.abspath("C:/Users/ASUS/.gemini/antigravity/brain/29993f87-25bb-47fa-b376-64dff7f6033e")
        if os.path.exists(artifact_dir):
            dest_artifact = os.path.join(artifact_dir, "TASKMESH_CODE_TO_MATH_DOSSIER.pdf")
            shutil.copy2(output_pdf_path, dest_artifact)
            print(f"Copied PDF to artifact directory: {dest_artifact}")

if __name__ == "__main__":
    asyncio.run(generate_pdf())
