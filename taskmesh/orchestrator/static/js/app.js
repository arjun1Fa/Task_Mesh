const API_BASE = "";

// State
let clusterStats = {};
let nodesList = [];
let tasksList = [];
let activeTab = "overview";

// Toast helper
function showToast(msg, isError = false) {
  const container = document.getElementById("toast-container");
  const t = document.createElement("div");
  t.className = "toast";
  if (isError) t.style.borderColor = "var(--accent-rose)";
  t.innerText = msg;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    setTimeout(() => t.remove(), 300);
  }, 3500);
}

// Switch navigation tabs
function switchTab(tabName) {
  activeTab = tabName;
  document.querySelectorAll(".nav-tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-view").forEach(view => {
    view.style.display = view.id === `tab-${tabName}` ? "block" : "none";
  });

  if (tabName === "scheduler") {
    fetchSchedulerDetails();
  }
}

// Fetch Cluster Health
async function fetchClusterHealth() {
  try {
    const res = await fetch(`${API_BASE}/v1/cluster/health`);
    if (!res.ok) throw new Error("Health check failed");
    clusterStats = await res.json();

    document.getElementById("stat-online-nodes").innerText = `${clusterStats.online_nodes} / ${clusterStats.total_nodes}`;
    document.getElementById("stat-running-tasks").innerText = clusterStats.running_tasks;
    document.getElementById("stat-pending-tasks").innerText = clusterStats.pending_tasks;
    document.getElementById("stat-total-tasks").innerText = clusterStats.total_tasks;
    document.getElementById("stat-dlq-tasks").innerText = clusterStats.dlq_tasks;
    document.getElementById("stat-scheduler-mode").innerText = clusterStats.scheduler_mode.toUpperCase();

    const pill = document.getElementById("cluster-status-pill");
    const isHealthy = clusterStats.status === "healthy";
    pill.className = `cluster-pill ${isHealthy ? "" : "unhealthy"}`;
    pill.innerHTML = `<span class="pulse-dot"></span> Cluster: ${clusterStats.status.toUpperCase()}`;
  } catch (err) {
    console.error("Cluster health fetch error:", err);
  }
}

// Fetch Nodes
async function fetchNodes() {
  try {
    const res = await fetch(`${API_BASE}/v1/nodes`);
    if (!res.ok) return;
    nodesList = await res.json();
    renderNodes();
  } catch (err) {
    console.error("Nodes fetch error:", err);
  }
}

function renderNodes() {
  const container = document.getElementById("nodes-container");
  const countBadge = document.getElementById("nodes-count");
  if (countBadge) countBadge.innerText = `${nodesList.length} Nodes`;

  if (nodesList.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: var(--text-dim);">
        <p>No nodes registered yet.</p>
        <p style="font-size: 0.8rem; margin-top: 0.5rem;">Start a worker node using: <code class="mono">python -m taskmesh.node.main --node-id node-alpha --url ws://127.0.0.1:8000/v1/ws/nodes</code></p>
      </div>`;
    return;
  }

  container.innerHTML = nodesList.map(node => {
    const isOnline = node.status === "online";
    const caps = node.capabilities || {};
    const tags = caps.tags || [];
    const cores = caps.cpu_cores || "N/A";
    const memGb = caps.memory_total_bytes ? (caps.memory_total_bytes / (1024**3)).toFixed(1) + " GB" : "N/A";
    const hasGpu = caps.has_gpu ? "Yes" : "No";

    return `
      <div class="node-card ${isOnline ? 'online' : 'offline'}">
        <div class="node-header">
          <div class="node-name">🖥️ ${node.id}</div>
          <span class="status-badge ${isOnline ? 'status-completed' : 'status-failed'}">
            ${node.status}
          </span>
        </div>
        
        <div class="node-tags">
          ${tags.map(t => `<span class="tag-badge">#${t}</span>`).join("") || '<span class="tag-badge">default</span>'}
        </div>

        <div class="node-metrics">
          <div class="metric-item">
            <span>CPU Cores</span>
            <span>${cores}</span>
          </div>
          <div class="metric-item">
            <span>RAM</span>
            <span>${memGb}</span>
          </div>
          <div class="metric-item">
            <span>GPU Accel</span>
            <span>${hasGpu}</span>
          </div>
          <div class="metric-item">
            <span>Load / Score</span>
            <span>${(node.load_score || 0).toFixed(2)}</span>
          </div>
        </div>

        <div style="margin-top: 0.85rem; display: flex; justify-content: flex-end;">
          <button class="btn btn-outline btn-sm" onclick="drainNode('${node.id}')" ${!isOnline ? 'disabled' : ''}>
            Drain Node
          </button>
        </div>
      </div>
    `;
  }).join("");
}

// Drain node action
async function drainNode(nodeId) {
  if (!confirm(`Are you sure you want to drain node ${nodeId}? No new tasks will be assigned to it.`)) return;
  try {
    const res = await fetch(`${API_BASE}/v1/nodes/${nodeId}/drain`, { method: "POST" });
    if (res.ok) {
      showToast(`Node ${nodeId} set to draining`);
      fetchNodes();
    } else {
      showToast(`Failed to drain node: ${res.statusText}`, true);
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, true);
  }
}

// Fetch Tasks
async function fetchTasks() {
  try {
    const res = await fetch(`${API_BASE}/v1/tasks?limit=50`);
    if (!res.ok) return;
    tasksList = await res.json();
    renderTasks();
  } catch (err) {
    console.error("Tasks fetch error:", err);
  }
}

function renderTasks() {
  const tbody = document.getElementById("tasks-table-body");
  const countBadge = document.getElementById("tasks-count");
  if (countBadge) countBadge.innerText = `${tasksList.length} Tasks`;

  if (tasksList.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--text-dim); padding: 2.5rem;">
          No tasks found. Submit a task using the form above!
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = tasksList.map(task => {
    let statusClass = "status-pending";
    if (task.status === "completed") statusClass = "status-completed";
    else if (task.status === "running") statusClass = "status-running";
    else if (task.status === "failed") statusClass = "status-failed";
    else if (task.status === "cancelled") statusClass = "status-cancelled";

    const assignedNode = task.assigned_node_id ? `<span class="tag-badge">${task.assigned_node_id}</span>` : `<span style="color: var(--text-dim);">-</span>`;
    let createdAt = "-";
    if (task.created_at) {
      const dt = typeof task.created_at === "number" ? new Date(task.created_at * 1000) : new Date(task.created_at);
      createdAt = dt.toLocaleTimeString();
    }
    const resultPreview = task.result ? JSON.stringify(task.result) : (task.error_message ? `<span style="color: var(--accent-rose);">${task.error_message}</span>` : "-");

    return `
      <tr>
        <td class="mono" style="color: var(--accent-cyan); font-weight: 600;">${task.id.slice(0, 8)}...</td>
        <td><span class="tag-badge">${task.task_type}</span></td>
        <td><span class="status-badge ${statusClass}">${task.status}</span></td>
        <td>${assignedNode}</td>
        <td>${task.priority}</td>
        <td style="max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title='${resultPreview}'>${resultPreview}</td>
        <td>
          <div style="display: flex; gap: 0.35rem;">
            ${task.status === "running" || task.status === "pending" ? `
              <button class="btn btn-outline btn-sm" onclick="cancelTask('${task.id}')">Cancel</button>
            ` : ""}
            ${task.status === "failed" ? `
              <button class="btn btn-primary btn-sm" onclick="retryTask('${task.id}')">Retry</button>
            ` : ""}
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

// Cancel Task
async function cancelTask(taskId) {
  try {
    const res = await fetch(`${API_BASE}/v1/tasks/${taskId}/cancel`, { method: "POST" });
    if (res.ok) {
      showToast(`Task ${taskId.slice(0, 8)} cancelled`);
      fetchTasks();
      fetchClusterHealth();
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, true);
  }
}

// Retry Task
async function retryTask(taskId) {
  try {
    const res = await fetch(`${API_BASE}/v1/tasks/${taskId}/retry`, { method: "POST" });
    if (res.ok) {
      showToast(`Task ${taskId.slice(0, 8)} requeued`);
      fetchTasks();
      fetchClusterHealth();
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, true);
  }
}

// Submit Task Form
async function handleTaskSubmit(e) {
  e.preventDefault();
  const type = document.getElementById("task-type").value.trim();
  const priority = parseInt(document.getElementById("task-priority").value, 10) || 0;
  const policy = document.getElementById("task-policy").value;
  const requiresGpu = document.getElementById("task-gpu").checked;
  const payloadRaw = document.getElementById("task-payload").value.trim();

  let payload = {};
  if (payloadRaw) {
    try {
      payload = JSON.parse(payloadRaw);
    } catch (err) {
      alert("Invalid JSON in payload: " + err.message);
      return;
    }
  }

  try {
    const res = await fetch(`${API_BASE}/v1/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_type: type,
        priority: priority,
        offload_policy: policy,
        requires_gpu: requiresGpu,
        payload: payload
      })
    });

    if (res.ok) {
      const created = await res.json();
      showToast(`Task submitted! ID: ${created.id.slice(0, 8)}...`);
      fetchTasks();
      fetchClusterHealth();
    } else {
      const err = await res.text();
      showToast(`Submission failed: ${err}`, true);
    }
  } catch (err) {
    showToast(`Submission error: ${err.message}`, true);
  }
}

// Submit Image Inference Form
async function handleImageSubmit(e) {
  e.preventDefault();
  const fileInput = document.getElementById("inference-file");
  if (!fileInput.files.length) {
    alert("Please choose an image file first");
    return;
  }

  const model = document.getElementById("inference-model").value;
  const priority = parseInt(document.getElementById("inference-priority").value, 10) || 5;
  const policy = document.getElementById("inference-policy").value;
  const requiresGpu = document.getElementById("inference-gpu").checked;

  const file = fileInput.files[0];
  const url = `${API_BASE}/v1/tasks/binary?task_type=image_inference&model=${encodeURIComponent(model)}&priority=${priority}&offload_policy=${policy}&requires_gpu=${requiresGpu}`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": file.type || "image/jpeg" },
      body: file
    });

    if (res.ok) {
      const task = await res.json();
      showToast(`Image inference task submitted! ID: ${task.id.slice(0, 8)}...`);
      fileInput.value = "";
      fetchTasks();
      fetchClusterHealth();
    } else {
      const err = await res.text();
      showToast(`Error: ${err}`, true);
    }
  } catch (err) {
    showToast(`Upload error: ${err.message}`, true);
  }
}

// Scheduler view
async function fetchSchedulerDetails() {
  try {
    const [statusRes, decisionsRes] = await Promise.all([
      fetch(`${API_BASE}/v1/scheduler/status`),
      fetch(`${API_BASE}/v1/scheduler/decisions?limit=25`)
    ]);

    if (statusRes.ok) {
      const statusData = await statusRes.json();
      document.getElementById("scheduler-json").textContent = JSON.stringify(statusData, null, 2);
    }

    if (decisionsRes.ok) {
      const decisionsData = await decisionsRes.json();
      const container = document.getElementById("scheduler-decisions-body");
      if (decisionsData.length === 0) {
        container.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 1.5rem;">No scheduling decisions recorded yet.</td></tr>`;
      } else {
        container.innerHTML = decisionsData.map(d => `
          <tr>
            <td class="mono" style="color: var(--accent-cyan);">${(d.task_id || '').slice(0, 8)}</td>
            <td><span class="tag-badge">${d.selected_node_id || 'N/A'}</span></td>
            <td>${d.reason || d.strategy || 'Adaptive Score'}</td>
            <td>${(d.score || 0).toFixed(3)}</td>
            <td style="color: var(--text-dim); font-size: 0.75rem;">${new Date((d.timestamp || 0) * 1000).toLocaleTimeString()}</td>
          </tr>
        `).join("");
      }
    }
  } catch (err) {
    console.error("Scheduler fetch error:", err);
  }
}

// Init
window.addEventListener("DOMContentLoaded", () => {
  // Navigation tabs
  document.querySelectorAll(".nav-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  // Forms
  document.getElementById("task-form").addEventListener("submit", handleTaskSubmit);
  document.getElementById("image-task-form").addEventListener("submit", handleImageSubmit);

  // Initial polls
  fetchClusterHealth();
  fetchNodes();
  fetchTasks();

  // Background refresh every 3 seconds
  setInterval(() => {
    fetchClusterHealth();
    fetchNodes();
    fetchTasks();
    if (activeTab === "scheduler") {
      fetchSchedulerDetails();
    }
  }, 3000);
});
