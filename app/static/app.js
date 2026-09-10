const API_BASE = '/api/v1/identities';

// DOM Elements
const statTotalIdentities = document.getElementById('statTotalIdentities');
const statActiveCount = document.getElementById('statActiveCount');
const statOffboardedCount = document.getElementById('statOffboardedCount');
const statKillswitchCount = document.getElementById('statKillswitchCount');
const employeeTableBody = document.getElementById('employeeTableBody');
const searchInput = document.getElementById('searchInput');
const statusFilter = document.getElementById('statusFilter');
const refreshBtn = document.getElementById('refreshBtn');
const verifyAuditBtn = document.getElementById('verifyAuditBtn');
const onboardModalBtn = document.getElementById('onboardModalBtn');
const onboardModal = document.getElementById('onboardModal');
const onboardCloseBtn = document.getElementById('onboardCloseBtn');
const onboardForm = document.getElementById('onboardForm');
const killswitchModal = document.getElementById('killswitchModal');
const killswitchTargetId = document.getElementById('killswitchTargetId');
const killswitchReason = document.getElementById('killswitchReason');
const killswitchAuthCode = document.getElementById('killswitchAuthCode');
const detailsModal = document.getElementById('detailsModal');
const detailsBody = document.getElementById('detailsBody');
const auditStreamContainer = document.getElementById('auditStreamContainer');
const ledgerStatusText = document.getElementById('ledgerStatusText');

// Load Employees & Compute Metrics
async function loadEmployees() {
  try {
    const params = new URLSearchParams();
    if (statusFilter.value) params.append('status_filter', statusFilter.value);
    if (searchInput.value) params.append('search', searchInput.value);

    const res = await fetch(`${API_BASE}/employees?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load identities');
    const employees = await res.json();

    // Calculate metrics
    const total = employees.length;
    const active = employees.filter(e => e.status === 'ACTIVE').length;
    const offboarded = employees.filter(e => e.status === 'OFFBOARDED').length;
    const killswitched = employees.filter(e => e.status === 'KILLSWITCH_TERMINATED').length;

    statTotalIdentities.innerText = total;
    statActiveCount.innerText = active;
    statOffboardedCount.innerText = offboarded;
    statKillswitchCount.innerText = killswitched;

    if (employees.length === 0) {
      employeeTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted); padding: 24px;">No managed identities found.</td></tr>`;
      return;
    }

    employeeTableBody.innerHTML = employees.map(emp => {
      const statusClass = emp.status.toLowerCase();
      const isActive = emp.status === 'ACTIVE';

      return `
        <tr>
          <td>
            <strong>${emp.full_name}</strong>
            <div style="font-size: 11px; color: var(--text-muted);">${emp.email}</div>
          </td>
          <td>
            <span style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan);">${emp.role}</span>
            <div style="font-size: 11px; color: var(--text-secondary);">${emp.department}</div>
          </td>
          <td>${emp.github_username ? `<code>${emp.github_username}</code>` : '<span style="color:var(--text-muted)">—</span>'}</td>
          <td>${emp.slack_handle ? `<code>${emp.slack_handle}</code>` : '<span style="color:var(--text-muted)">—</span>'}</td>
          <td><code>${emp.aws_iam_user || '—'}</code></td>
          <td><span class="status-badge ${statusClass}">${emp.status.replace('_', ' ')}</span></td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" onclick="viewEmployee('${emp.id}')">View Grants</button>
              ${isActive ? `
                <button class="btn btn-danger btn-sm" onclick="openKillswitchModal('${emp.id}', '${emp.full_name}')">🚨 KillSwitch</button>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error fetching identities:', err);
    employeeTableBody.innerHTML = `<tr><td colspan="7" style="color: var(--accent-red); text-align:center; padding: 24px;">Error fetching identities.</td></tr>`;
  }
}

// Load Audit Chain
async function loadAuditChain() {
  try {
    const res = await fetch(`${API_BASE}/audit/chain`);
    if (!res.ok) throw new Error('Failed to load audit chain');
    const blocks = await res.json();

    if (blocks.length === 0) {
      auditStreamContainer.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 20px;">No audit records in ledger.</div>`;
      return;
    }

    auditStreamContainer.innerHTML = blocks.map(b => {
      const isDanger = b.action.includes('KILLSWITCH');
      const detailsObj = JSON.parse(b.details || '{}');

      return `
        <div class="audit-block-card ${isDanger ? 'danger' : ''}">
          <div class="audit-header">
            <span><strong>Block #${b.index}</strong> • <code style="color: ${isDanger ? 'var(--accent-red)' : 'var(--accent-cyan)'};">${b.action}</code></span>
            <span>${new Date(b.timestamp).toLocaleTimeString()}</span>
          </div>
          <div>Target: <strong>${b.target_email}</strong> (Initiated by: <em>${b.actor}</em>)</div>
          <div style="font-size: 11px; color: var(--text-secondary); background: rgba(0,0,0,0.2); padding: 6px; border-radius: 4px;">
            Payload: ${JSON.stringify(detailsObj)}
          </div>
          <div class="block-hash">
            <span>Prev: ${b.previous_hash.slice(0, 16)}...</span> | 
            <span style="color: var(--accent-green);">Hash: ${b.block_hash.slice(0, 24)}...</span>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error fetching audit chain:', err);
  }
}

// Verify Ledger Integrity
async function verifyLedger() {
  try {
    const res = await fetch(`${API_BASE}/audit/verify`);
    const data = await res.json();
    if (data.valid) {
      ledgerStatusText.innerText = `Verified (${data.total_blocks} Blocks)`;
      showToast(`✅ ${data.message}`, 'success');
    } else {
      ledgerStatusText.innerText = `TAMPER DETECTED!`;
      ledgerStatusText.style.color = 'var(--accent-red)';
      showToast(`❌ Tamper Alert: ${data.reason}`, 'error');
    }
  } catch (err) {
    showToast(`Verification failed: ${err.message}`, 'error');
  }
}

// View Employee Details Modal
window.viewEmployee = async function(id) {
  try {
    const res = await fetch(`${API_BASE}/employees/${id}`);
    const emp = await res.json();

    detailsBody.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 13px;">
        <div><strong>Full Name:</strong> ${emp.full_name}</div>
        <div><strong>Email:</strong> ${emp.email}</div>
        <div><strong>Department:</strong> ${emp.department}</div>
        <div><strong>Role:</strong> <code>${emp.role}</code></div>
        <div><strong>GitHub:</strong> ${emp.github_username || 'None'}</div>
        <div><strong>Slack:</strong> ${emp.slack_handle || 'None'}</div>
        <div><strong>AWS IAM User:</strong> <code>${emp.aws_iam_user}</code></div>
        <div><strong>Status:</strong> <span class="status-badge ${emp.status.toLowerCase()}">${emp.status}</span></div>
      </div>

      <h4 style="margin-top: 20px; margin-bottom: 8px;">Active SaaS Entitlements &amp; Access Grants</h4>
      <table class="data-table" style="background: rgba(0,0,0,0.25); border-radius: 8px;">
        <thead>
          <tr>
            <th>Platform</th>
            <th>Resource Target</th>
            <th>Permission</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${emp.access_grants.map(g => `
            <tr>
              <td><strong style="font-family: var(--font-mono);">${g.platform}</strong></td>
              <td><code>${g.resource_name}</code></td>
              <td>${g.access_level}</td>
              <td><span style="color: ${g.is_active ? 'var(--accent-green)' : 'var(--accent-red)'}; font-weight: 600;">${g.is_active ? 'ACTIVE' : 'REVOKED'}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    detailsModal.style.display = 'flex';
  } catch (err) {
    showToast('Failed to load profile', 'error');
  }
};

// Onboard Form Submission
onboardForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    full_name: document.getElementById('onboardFullName').value,
    email: document.getElementById('onboardEmail').value,
    department: document.getElementById('onboardDept').value,
    role: document.getElementById('onboardRole').value,
    github_username: document.getElementById('onboardGithub').value || null,
    slack_handle: document.getElementById('onboardSlack').value || null,
    initiator: 'HR Operations Lead'
  };

  try {
    const res = await fetch(`${API_BASE}/onboard`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Onboarding failed');
    }

    showToast(`Identity ${payload.full_name} provisioned across SaaS & IAM!`, 'success');
    onboardModal.style.display = 'none';
    onboardForm.reset();
    loadEmployees();
    loadAuditChain();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
});

// KillSwitch Trigger
window.openKillswitchModal = function(id, name) {
  killswitchTargetId.value = id;
  killswitchReason.value = 'Immediate Departure / Security Precaution';
  killswitchAuthCode.value = `SEC-KILL-${Math.floor(100 + Math.random() * 900)}`;
  killswitchModal.style.display = 'flex';
};

window.confirmKillswitch = async function() {
  const id = killswitchTargetId.value;
  const reason = killswitchReason.value;
  const authCode = killswitchAuthCode.value;

  try {
    const res = await fetch(`${API_BASE}/employees/${id}/killswitch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reason: reason,
        initiator: 'Lead SecOps Officer',
        authorization_code: authCode
      })
    });

    if (!res.ok) throw new Error('KillSwitch purge failed');
    showToast(`🚨 ALL ACCESS PURGED & TOKENS TERMINATED!`, 'error');
    killswitchModal.style.display = 'none';
    loadEmployees();
    loadAuditChain();
  } catch (err) {
    showToast(`Purge failed: ${err.message}`, 'error');
  }
};

// Modal Listeners
onboardModalBtn.addEventListener('click', () => onboardModal.style.display = 'flex');
onboardCloseBtn.addEventListener('click', () => onboardModal.style.display = 'none');
verifyAuditBtn.addEventListener('click', verifyLedger);
refreshBtn.addEventListener('click', () => {
  loadEmployees();
  loadAuditChain();
  showToast('Refreshed identity directory.', 'info');
});

searchInput.addEventListener('input', loadEmployees);
statusFilter.addEventListener('change', loadEmployees);

function showToast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.borderColor = type === 'error' ? 'var(--accent-red)' : (type === 'success' ? 'var(--accent-green)' : 'var(--border-color)');
  toast.innerText = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

document.addEventListener('DOMContentLoaded', () => {
  loadEmployees();
  loadAuditChain();
  verifyLedger();
});
