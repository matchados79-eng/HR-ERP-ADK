/* Saudi HR ERP System - Main JavaScript Application with User Creation & Role Permissions */

let currentEmployeeId = null;
let currentTab = 'tab-info';
let currentUserRole = 'admin';
let allDepartments = [];
let allEmployees = [];

document.addEventListener('DOMContentLoaded', () => {
  checkAuthSession();
  runEosbCalc();
  runGosiCalc();
});

// Authentication & Role Handlers
function checkAuthSession() {
  const token = localStorage.getItem('jwt_token');
  const userJson = localStorage.getItem('jwt_user');

  if (!token) {
    showLoginModal();
    return;
  }

  if (userJson) {
    try {
      const u = JSON.parse(userJson);
      currentUserRole = u.role || 'viewer';
      document.getElementById('user-display-name').innerText = u.full_name || 'System User';
      document.getElementById('user-display-role').innerText = `Role: ${currentUserRole.toUpperCase()} • Active Session`;
    } catch (e) {}
  }

  applyRoleUIRestrictions();
  hideLoginModal();
  loadDashboardData();
  loadDepartments();
  loadEmployees();
  loadPayrollRuns();
  loadLeaves();
  loadSettings();
  loadUsersList();
}

function applyRoleUIRestrictions() {
  // If user is 'viewer' (Directory Only / Restricted)
  if (currentUserRole === 'viewer') {
    const addEmpBtn = document.getElementById('add-emp-btn');
    if (addEmpBtn) addEmpBtn.style.display = 'none';

    const payrollNav = document.getElementById('nav-payroll-item');
    if (payrollNav) payrollNav.style.display = 'none';

    const backupBtn = document.getElementById('gdrive-backup-btn');
    if (backupBtn) backupBtn.style.display = 'none';

    const settingsNav = document.getElementById('nav-settings-item');
    if (settingsNav) settingsNav.style.display = 'none';
  } else {
    const addEmpBtn = document.getElementById('add-emp-btn');
    if (addEmpBtn) addEmpBtn.style.display = 'inline-flex';

    const payrollNav = document.getElementById('nav-payroll-item');
    if (payrollNav) payrollNav.style.display = 'block';

    const backupBtn = document.getElementById('gdrive-backup-btn');
    if (backupBtn) backupBtn.style.display = 'inline-flex';

    const settingsNav = document.getElementById('nav-settings-item');
    if (settingsNav) settingsNav.style.display = 'block';
  }
}

function showLoginModal() {
  const m = document.getElementById('modal-login');
  if (m) m.classList.add('active');
}

function hideLoginModal() {
  const m = document.getElementById('modal-login');
  if (m) m.classList.remove('active');
}

async function submitLogin() {
  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;
  const errBox = document.getElementById('login-error-alert');

  if (errBox) errBox.style.display = 'none';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) {
      const err = await res.json();
      if (errBox) {
        errBox.innerText = err.detail || 'Login failed. Please check credentials.';
        errBox.style.display = 'block';
      }
      return;
    }

    const data = await res.json();
    localStorage.setItem('jwt_token', data.access_token);
    localStorage.setItem('jwt_user', JSON.stringify(data.user));

    checkAuthSession();
    alert(`Welcome, ${data.user.full_name}! Signed in successfully.`);

  } catch (err) {
    if (errBox) {
      errBox.innerText = `Network error: ${err}`;
      errBox.style.display = 'block';
    }
  }
}

function logoutUser() {
  localStorage.removeItem('jwt_token');
  localStorage.removeItem('jwt_user');
  showLoginModal();
}

function getAuthHeaders() {
  const token = localStorage.getItem('jwt_token') || '';
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

// User Accounts Management
async function loadUsersList() {
  if (currentUserRole === 'viewer') return;
  try {
    const res = await fetch('/api/users', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const users = await res.json();

    const tbody = document.getElementById('users-list-body');
    if (!tbody) return;

    tbody.innerHTML = users.map(u => `
      <tr>
        <td>#USR-${u.id}</td>
        <td><strong>${u.full_name}</strong></td>
        <td><code>${u.email}</code></td>
        <td><span class="badge ${u.role === 'admin' ? 'badge-saudi' : (u.role === 'hr_manager' ? 'badge-active' : 'badge-expat')}">${u.role.toUpperCase()}</span></td>
        <td>${u.created_at || 'N/A'}</td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Error loading users:', err);
  }
}

async function submitCreateUser() {
  const fullName = document.getElementById('new-user-fullname').value;
  const email = document.getElementById('new-user-email').value;
  const password = document.getElementById('new-user-password').value;
  const role = document.getElementById('new-user-role').value;

  try {
    const res = await fetch('/api/users', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ email, password, full_name: fullName, role })
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Error creating user: ${err.detail}`);
      return;
    }

    alert(`User account created successfully for ${fullName} (${role})!`);
    document.getElementById('create-user-form').reset();
    loadUsersList();

  } catch (err) {
    alert(`Failed to create user account: ${err}`);
  }
}

// Navigation Switching
function switchSection(sectionId) {
  document.querySelectorAll('.content-section').forEach(sec => sec.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));

  const targetSec = document.getElementById(`section-${sectionId}`);
  if (targetSec) targetSec.classList.add('active');

  event.currentTarget.classList.add('active');

  const titleMap = {
    'dashboard': ['HR Dashboard', 'Comprehensive overview of Saudi workforce, Saudization rates, and pending actions'],
    'employees': ['Employee Directory', 'Manage employee profiles, Iqama details, GOSI numbers, and document vaults'],
    'payroll': ['Payroll & WPS Engine', 'Process monthly salaries, generate SAMA WPS CSV files, and print PDF payslips'],
    'leaves': ['Leave Management', 'Track annual leave balances, sick leave requests, and approval workflows'],
    'compliance': ['Saudi Compliance Hub', 'Interactive EOSB (Articles 84/85), GOSI contributions, and Nitaqat tools'],
    'settings': ['System & Users Settings', 'Configure company legal details, CR number, and Google Drive Backups']
  };

  if (titleMap[sectionId]) {
    document.getElementById('page-heading').innerText = titleMap[sectionId][0];
    document.getElementById('page-subheading').innerText = titleMap[sectionId][1];
  }

  if (sectionId === 'dashboard') loadDashboardData();
  if (sectionId === 'employees') loadEmployees();
  if (sectionId === 'payroll') loadPayrollRuns();
  if (sectionId === 'leaves') loadLeaves();
  if (sectionId === 'settings') loadUsersList();
}

// Modal Helpers
function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('active');
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('active');
}

// 1. DASHBOARD LOAD
async function loadDashboardData() {
  try {
    const res = await fetch('/api/dashboard/stats', { headers: getAuthHeaders() });
    const data = await res.json();

    document.getElementById('stat-total-emp').innerText = data.total_employees;
    document.getElementById('stat-saudization-pct').innerText = `${data.saudization.saudization_percentage}%`;
    document.getElementById('stat-monthly-payroll').innerText = `SAR ${data.total_monthly_payroll.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('stat-pending-leaves').innerText = data.pending_leaves_count;

    // Nitaqat Banner
    const nb = document.getElementById('nitaqat-banner');
    nb.style.backgroundColor = data.saudization.nitaqat_color;
    document.getElementById('nitaqat-band-name').innerText = `Nitaqat Band: ${data.saudization.nitaqat_band}`;
    document.getElementById('nitaqat-status-desc').innerText = data.saudization.status_description;
    document.getElementById('nitaqat-ratio-display').innerText = `${data.saudization.saudization_percentage}%`;

    // Alerts Table
    const alertsBody = document.getElementById('alerts-table-body');
    document.getElementById('alert-count-badge').innerText = `${data.expiring_alerts_count} Alerts`;

    if (data.alerts_summary.length === 0) {
      alertsBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--accent-emerald);">All Iqama and passport documents are up to date!</td></tr>`;
    } else {
      alertsBody.innerHTML = data.alerts_summary.map(a => `
        <tr>
          <td><strong>${a.employee_name}</strong></td>
          <td><span class="badge badge-pending">${a.doc_type}</span></td>
          <td>${a.expiry_date}</td>
          <td><span class="badge ${a.severity === 'CRITICAL' ? 'badge-critical' : 'badge-pending'}">${a.days_remaining} Days</span></td>
        </tr>
      `).join('');
    }

    // Dept Distribution Table
    const deptBody = document.getElementById('dept-dist-body');
    deptBody.innerHTML = data.department_distribution.map(d => `
      <tr>
        <td><strong>${d.name}</strong></td>
        <td><span class="badge badge-saudi">${d.emp_count} Employees</span></td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Error loading dashboard stats:', err);
  }
}

// 2. DEPARTMENTS & EMPLOYEES
async function loadDepartments() {
  try {
    const res = await fetch('/api/departments', { headers: getAuthHeaders() });
    allDepartments = await res.json();

    const addSelect = document.getElementById('add-emp-dept-select');
    const filterSelect = document.getElementById('emp-filter-dept');

    const optionsHtml = allDepartments.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join('');
    
    if (addSelect) addSelect.innerHTML = optionsHtml;
    if (filterSelect) filterSelect.innerHTML = `<option value="">All Departments</option>` + optionsHtml;

  } catch (err) {
    console.error('Error loading departments:', err);
  }
}

async function loadEmployees() {
  try {
    const search = document.getElementById('emp-search').value;
    const isSaudi = document.getElementById('emp-filter-saudi').value;
    const deptId = document.getElementById('emp-filter-dept').value;

    let url = `/api/employees?`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (isSaudi !== '') url += `is_saudi=${isSaudi}&`;
    if (deptId) url += `department_id=${deptId}&`;

    const res = await fetch(url, { headers: getAuthHeaders() });
    allEmployees = await res.json();

    const tbody = document.getElementById('employees-table-body');
    
    const leaveEmpSelect = document.getElementById('leave-emp-select');
    if (leaveEmpSelect) {
      leaveEmpSelect.innerHTML = allEmployees.map(e => `<option value="${e.id}">${e.emp_code} - ${e.first_name} ${e.last_name}</option>`).join('');
    }

    if (allEmployees.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center;">No matching employees found.</td></tr>`;
      return;
    }

    tbody.innerHTML = allEmployees.map(e => `
      <tr>
        <td><strong>${e.emp_code}</strong></td>
        <td>
          <div style="font-weight: 600;">${e.first_name} ${e.last_name}</div>
          <div style="font-size: 0.78rem; color: var(--text-muted);">${e.arabic_name || ''}</div>
        </td>
        <td><code>${e.national_id_iqama}</code></td>
        <td>${e.nationality}</td>
        <td>${e.department_name || 'Unassigned'}</td>
        <td>${e.designation}</td>
        <td>SAR ${e.basic_salary ? e.basic_salary.toLocaleString('en-US') : '***'}</td>
        <td>
          <span class="badge ${e.is_saudi ? 'badge-saudi' : 'badge-expat'}">
            ${e.is_saudi ? 'Saudi Citizen' : 'Expat'}
          </span>
        </td>
        <td>
          <button class="btn btn-outline" style="padding: 4px 10px; font-size: 0.8rem;" onclick="viewEmployeeDetail(${e.id})">
            View Details
          </button>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Error loading employees:', err);
  }
}

function openAddEmployeeModal() {
  document.getElementById('add-employee-form').reset();
  openModal('modal-add-employee');
}

async function submitAddEmployee() {
  const form = document.getElementById('add-employee-form');
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  data.is_saudi = parseInt(data.is_saudi);
  data.basic_salary = parseFloat(data.basic_salary || 0);
  data.housing_allowance = parseFloat(data.housing_allowance || 0);
  data.transport_allowance = parseFloat(data.transport_allowance || 0);

  try {
    const res = await fetch('/api/employees', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Error: ${err.detail}`);
      return;
    }

    closeModal('modal-add-employee');
    loadEmployees();
    loadDashboardData();
    alert('Employee profile created successfully!');
  } catch (err) {
    alert(`Failed to add employee: ${err}`);
  }
}

// 3. EMPLOYEE PROFILE & FILE VAULT
async function viewEmployeeDetail(empId) {
  currentEmployeeId = empId;
  openModal('modal-emp-detail');
  switchTab('tab-info');

  try {
    const res = await fetch(`/api/employees/${empId}`, { headers: getAuthHeaders() });
    const data = await res.json();

    const emp = data.employee;
    document.getElementById('emp-detail-title').innerText = `Employee Profile: ${emp.first_name} ${emp.last_name}`;
    document.getElementById('detail-emp-name').innerText = `${emp.first_name} ${emp.last_name} (${emp.arabic_name || ''})`;
    document.getElementById('detail-emp-sub').innerText = `${emp.designation} • ${emp.department_name || 'General'} • Code: ${emp.emp_code}`;
    
    document.getElementById('detail-emp-nat-badge').className = `badge ${emp.is_saudi ? 'badge-saudi' : 'badge-expat'}`;
    document.getElementById('detail-emp-nat-badge').innerText = emp.is_saudi ? 'Saudi Citizen' : `Expat (${emp.nationality})`;

    document.getElementById('detail-emp-status-badge').className = `badge badge-active`;
    document.getElementById('detail-emp-status-badge').innerText = emp.status;

    // Avatar
    const avatarImg = document.getElementById('detail-avatar');
    if (emp.photo_filename) {
      avatarImg.src = `/uploads/${emp.photo_filename}`;
    } else {
      avatarImg.src = '/static/css/default-avatar.svg';
    }

    // Grid Info
    const grid = document.getElementById('detail-info-grid');
    grid.innerHTML = `
      <div class="form-group"><label>National ID / Iqama:</label><input type="text" class="form-control" value="${emp.national_id_iqama}" readonly></div>
      <div class="form-group"><label>Email:</label><input type="text" class="form-control" value="${emp.email}" readonly></div>
      <div class="form-group"><label>Phone:</label><input type="text" class="form-control" value="${emp.phone || ''}" readonly></div>
      <div class="form-group"><label>Hire Date:</label><input type="text" class="form-control" value="${emp.hire_date}" readonly></div>
      <div class="form-group"><label>Basic Salary:</label><input type="text" class="form-control" value="${emp.basic_salary ? 'SAR ' + emp.basic_salary.toLocaleString() : 'Restricted (Viewer)'}" readonly></div>
      <div class="form-group"><label>Housing Allowance:</label><input type="text" class="form-control" value="${emp.housing_allowance ? 'SAR ' + emp.housing_allowance.toLocaleString() : 'Restricted (Viewer)'}" readonly></div>
      <div class="form-group"><label>Transport Allowance:</label><input type="text" class="form-control" value="${emp.transport_allowance ? 'SAR ' + emp.transport_allowance.toLocaleString() : 'Restricted (Viewer)'}" readonly></div>
      <div class="form-group"><label>Bank & IBAN:</label><input type="text" class="form-control" value="${emp.bank_name || ''} - ${emp.iban || ''}" readonly></div>
      <div class="form-group"><label>Iqama Expiry Date:</label><input type="text" class="form-control" value="${emp.iqama_expiry_date || 'N/A'}" readonly></div>
      <div class="form-group"><label>Passport Number & Expiry:</label><input type="text" class="form-control" value="${emp.passport_number || ''} (Expires: ${emp.passport_expiry_date || 'N/A'})" readonly></div>
    `;

    // GOSI Box
    const gosi = data.gosi_breakdown;
    document.getElementById('detail-gosi-box').innerHTML = `
      <div class="card" style="background: #F0FDF4; border-color: #A7F3D0;">
        <h4 style="color: #065F46; margin-bottom: 10px;">GOSI Contribution Profile</h4>
        <p>GOSI Register Number: <strong>${emp.gosi_number || 'N/A'}</strong></p>
        <p>Eligible Monthly Base Wage: <strong>SAR ${gosi.gosi_base.toLocaleString()}</strong></p>
        <hr style="margin: 10px 0; border: none; border-top: 1px solid #A7F3D0;">
        <p>Employee Monthly Deduction: <strong>SAR ${gosi.employee_deduction.toLocaleString()}</strong></p>
        <p>Employer Monthly Contribution: <strong>SAR ${gosi.employer_contribution.toLocaleString()}</strong></p>
      </div>
    `;

    // Docs Table
    const docsBody = document.getElementById('detail-docs-body');
    if (data.documents.length === 0) {
      docsBody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No document files uploaded yet.</td></tr>`;
    } else {
      docsBody.innerHTML = data.documents.map(d => `
        <tr>
          <td><span class="badge badge-saudi">${d.doc_type}</span></td>
          <td>${d.file_name}</td>
          <td>${d.upload_date}</td>
          <td>${d.expiry_date || 'N/A'}</td>
          <td>
            <a href="/api/documents/${d.id}/download" target="_blank" class="btn btn-outline" style="padding: 4px 8px; font-size: 0.78rem;">
              ⬇️ Download
            </a>
          </td>
        </tr>
      `).join('');
    }

    // Leaves Table
    const leavesBody = document.getElementById('detail-leaves-body');
    if (data.leaves.length === 0) {
      leavesBody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No leave history recorded.</td></tr>`;
    } else {
      leavesBody.innerHTML = data.leaves.map(l => `
        <tr>
          <td>${l.leave_type}</td>
          <td>${l.start_date}</td>
          <td>${l.end_date}</td>
          <td>${l.days} Days</td>
          <td><span class="badge ${l.status === 'Approved' ? 'badge-active' : 'badge-pending'}">${l.status}</span></td>
        </tr>
      `).join('');
    }

  } catch (err) {
    console.error('Error fetching employee details:', err);
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  event.currentTarget.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

// Upload Photo Handler
async function uploadEmployeePhoto() {
  const input = document.getElementById('photo-upload-input');
  if (!input.files || !input.files[0]) return;

  const file = input.files[0];
  const formData = new FormData();
  formData.append('file', file);

  const token = localStorage.getItem('jwt_token') || '';

  try {
    const res = await fetch(`/api/employees/${currentEmployeeId}/photo`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Photo upload failed: ${err.detail}`);
      return;
    }

    const data = await res.json();
    document.getElementById('detail-avatar').src = `${data.photo_url}?t=${Date.now()}`;
    alert('Employee profile photo updated successfully!');
    loadEmployees();

  } catch (err) {
    alert(`Photo upload error: ${err}`);
  }
}

// Upload Document Handler
async function submitUploadDocument() {
  const docType = document.getElementById('upload-doc-type').value;
  const expiryDate = document.getElementById('upload-doc-expiry').value;
  const fileInput = document.getElementById('upload-doc-file');

  if (!fileInput.files || !fileInput.files[0]) {
    alert('Please select a file to upload.');
    return;
  }

  const formData = new FormData();
  formData.append('doc_type', docType);
  if (expiryDate) formData.append('expiry_date', expiryDate);
  formData.append('file', fileInput.files[0]);

  const token = localStorage.getItem('jwt_token') || '';

  try {
    const res = await fetch(`/api/employees/${currentEmployeeId}/documents`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Document upload failed: ${err.detail}`);
      return;
    }

    alert('Document uploaded successfully to vault!');
    fileInput.value = '';
    viewEmployeeDetail(currentEmployeeId);

  } catch (err) {
    alert(`Document upload error: ${err}`);
  }
}

// 4. PAYROLL & WPS
async function loadPayrollRuns() {
  if (currentUserRole === 'viewer') return;
  try {
    const res = await fetch('/api/payroll/runs', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const runs = await res.json();

    const tbody = document.getElementById('payroll-runs-body');
    if (!tbody) return;

    if (runs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center;">No payroll runs executed yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = runs.map(r => `
      <tr>
        <td><strong>#PR-${r.id}</strong></td>
        <td>Pay Period ${r.payroll_month}/${r.payroll_year}</td>
        <td>SAR ${r.total_basic.toLocaleString()}</td>
        <td>SAR ${r.total_allowances.toLocaleString()}</td>
        <td>SAR ${r.total_deductions.toLocaleString()}</td>
        <td><strong style="color: var(--primary); font-size: 1rem;">SAR ${r.total_net_pay.toLocaleString()}</strong></td>
        <td><span class="badge badge-active">${r.status}</span></td>
        <td>
          <div style="display: flex; gap: 8px;">
            <a href="/api/payroll/runs/${r.id}/wps.csv" class="btn btn-success" style="padding: 4px 10px; font-size: 0.78rem;">
              🇸🇦 Download SAMA WPS CSV
            </a>
            <button class="btn btn-outline" style="padding: 4px 10px; font-size: 0.78rem;" onclick="viewPayrollDetails(${r.id})">
              View Payslips
            </button>
          </div>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Error loading payroll runs:', err);
  }
}

function openRunPayrollModal() {
  openModal('modal-run-payroll');
}

async function submitGeneratePayroll() {
  const month = parseInt(document.getElementById('payroll-month').value);
  const year = parseInt(document.getElementById('payroll-year').value);

  try {
    const res = await fetch('/api/payroll/generate', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ month, year })
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Payroll Error: ${err.detail}`);
      return;
    }

    closeModal('modal-run-payroll');
    loadPayrollRuns();
    loadDashboardData();
    alert('Monthly Payroll processed successfully! WPS CSV and PDF Payslips generated.');

  } catch (err) {
    alert(`Payroll processing failed: ${err}`);
  }
}

async function viewPayrollDetails(runId) {
  try {
    const res = await fetch(`/api/payroll/runs/${runId}/details`, { headers: getAuthHeaders() });
    const data = await res.json();

    let popupContent = `
      <div style="max-height: 400px; overflow-y: auto;">
        <table class="data-table">
          <thead>
            <tr>
              <th>Emp</th>
              <th>Basic</th>
              <th>Allowances</th>
              <th>GOSI Deduction</th>
              <th>Net Salary</th>
              <th>PDF Payslip</th>
            </tr>
          </thead>
          <tbody>
            ${data.details.map(d => `
              <tr>
                <td><strong>${d.first_name} ${d.last_name}</strong><br/><small>${d.emp_code}</small></td>
                <td>SAR ${d.basic_salary.toLocaleString()}</td>
                <td>SAR ${(d.housing_allowance + d.transport_allowance + d.other_allowances).toLocaleString()}</td>
                <td>SAR ${d.gosi_employee.toLocaleString()}</td>
                <td><strong>SAR ${d.net_salary.toLocaleString()}</strong></td>
                <td>
                  <a href="/api/payroll/details/${d.id}/payslip.pdf" target="_blank" class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;">
                    📄 PDF Payslip
                  </a>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    const m = document.createElement('div');
    m.className = 'modal-overlay active';
    m.innerHTML = `
      <div class="modal-box" style="max-width: 800px;">
        <div class="modal-header">
          <h3 class="modal-title">Payroll Details: Period ${data.run.payroll_month}/${data.run.payroll_year}</h3>
          <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
        </div>
        <div class="modal-body">${popupContent}</div>
      </div>
    `;
    document.body.appendChild(m);

  } catch (err) {
    alert(`Failed to load details: ${err}`);
  }
}

// 5. LEAVES
async function loadLeaves() {
  try {
    const res = await fetch('/api/leaves', { headers: getAuthHeaders() });
    const leaves = await res.json();

    const tbody = document.getElementById('leaves-table-body');
    if (leaves.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center;">No leave applications found.</td></tr>`;
      return;
    }

    tbody.innerHTML = leaves.map(l => `
      <tr>
        <td>#LV-${l.id}</td>
        <td><strong>${l.first_name} ${l.last_name}</strong> (${l.emp_code})</td>
        <td><span class="badge badge-saudi">${l.leave_type}</span></td>
        <td>${l.start_date}</td>
        <td>${l.end_date}</td>
        <td><strong>${l.days} Days</strong></td>
        <td>${l.reason || 'N/A'}</td>
        <td><span class="badge ${l.status === 'Approved' ? 'badge-active' : (l.status === 'Pending' ? 'badge-pending' : 'badge-critical')}">${l.status}</span></td>
        <td>
          ${(l.status === 'Pending' && currentUserRole !== 'viewer') ? `
            <button class="btn btn-success" style="padding: 2px 6px; font-size: 0.75rem;" onclick="updateLeaveStatus(${l.id}, 'Approved')">Approve</button>
            <button class="btn btn-danger" style="padding: 2px 6px; font-size: 0.75rem;" onclick="updateLeaveStatus(${l.id}, 'Rejected')">Reject</button>
          ` : l.status}
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Error loading leaves:', err);
  }
}

function openApplyLeaveModal() {
  openModal('modal-apply-leave');
}

async function submitApplyLeave() {
  const form = document.getElementById('apply-leave-form');
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  data.employee_id = parseInt(data.employee_id);
  data.days = parseInt(data.days);

  try {
    const res = await fetch('/api/leaves', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Leave application failed: ${err.detail}`);
      return;
    }

    closeModal('modal-apply-leave');
    loadLeaves();
    loadDashboardData();
    alert('Leave application submitted successfully!');

  } catch (err) {
    alert(`Error applying for leave: ${err}`);
  }
}

async function updateLeaveStatus(leaveId, status) {
  try {
    const res = await fetch(`/api/leaves/${leaveId}/status`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ status })
    });

    if (!res.ok) {
      alert('Failed to update status');
      return;
    }

    loadLeaves();
    loadDashboardData();
  } catch (err) {
    alert(`Error updating leave status: ${err}`);
  }
}

// 6. SAUDI CALCULATORS
async function runEosbCalc() {
  const basic = parseFloat(document.getElementById('eosb-basic').value || 0);
  const start = document.getElementById('eosb-start').value;
  const end = document.getElementById('eosb-end').value;
  const reason = document.getElementById('eosb-reason').value;

  if (!basic || !start || !end) return;

  try {
    const res = await fetch('/api/calculators/eosb', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        basic_salary: basic,
        gross_salary: basic * 1.25,
        start_date: start,
        end_date: end,
        reason: reason
      })
    });

    const data = await res.json();
    document.getElementById('eosb-net-val').innerText = `SAR ${data.net_eosb.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('eosb-notes-desc').innerHTML = `
      Duration: <strong>${data.years_of_service} Years</strong> (${data.days_worked} days worked)<br/>
      Raw Benefit (Art 84): SAR ${data.raw_benefit.toLocaleString()}<br/>
      Resignation Multiplier: <strong>${data.multiplier_percentage}%</strong> (${data.article})<br/>
      <em>${data.notes}</em>
    `;

  } catch (err) {
    console.error('EOSB Calculation Error:', err);
  }
}

async function runGosiCalc() {
  const isSaudi = parseInt(document.getElementById('gosi-is-saudi').value) === 1;
  const basic = parseFloat(document.getElementById('gosi-basic').value || 0);
  const housing = parseFloat(document.getElementById('gosi-housing').value || 0);

  try {
    const res = await fetch('/api/calculators/gosi', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        is_saudi: isSaudi,
        basic_salary: basic,
        housing_allowance: housing
      })
    });

    const data = await res.json();
    document.getElementById('gosi-emp-share').innerText = `SAR ${data.employee_deduction.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('gosi-empr-share').innerText = `SAR ${data.employer_contribution.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('gosi-total-share').innerText = `SAR ${data.total_gosi.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

  } catch (err) {
    console.error('GOSI Calculation Error:', err);
  }
}

// 7. SETTINGS
async function loadSettings() {
  if (currentUserRole === 'viewer') return;
  try {
    const res = await fetch('/api/settings', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const settings = await res.json();

    if (settings.company_name) document.getElementById('set-company-name').value = settings.company_name;
    if (settings.company_arabic_name) document.getElementById('set-company-arabic-name').value = settings.company_arabic_name;
    if (settings.cr_number) document.getElementById('set-cr-number').value = settings.cr_number;
    if (settings.mol_establishment_id) document.getElementById('set-mol-id').value = settings.mol_establishment_id;
    if (settings.gosi_reg_number) document.getElementById('set-gosi-number').value = settings.gosi_reg_number;
    if (settings.wps_bank_code) document.getElementById('set-wps-bank-code').value = settings.wps_bank_code;

  } catch (err) {
    console.error('Error loading settings:', err);
  }
}

async function saveSettings() {
  const payload = {
    company_name: document.getElementById('set-company-name').value,
    company_arabic_name: document.getElementById('set-company-arabic-name').value,
    cr_number: document.getElementById('set-cr-number').value,
    mol_establishment_id: document.getElementById('set-mol-id').value,
    gosi_reg_number: document.getElementById('set-gosi-number').value,
    wps_bank_code: document.getElementById('set-wps-bank-code').value
  };

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) alert('Settings saved successfully!');
  } catch (err) {
    alert(`Failed to save settings: ${err}`);
  }
}

// 8. GOOGLE DRIVE AUTOMATED BACKUP
async function triggerGoogleDriveBackup() {
  const banner = document.getElementById('backup-status-banner');
  if (banner) {
    banner.style.display = 'block';
    banner.innerHTML = '⏳ <strong>Generating system backup archive...</strong> Please wait...';
  }

  try {
    const res = await fetch('/api/backup/google-drive', {
      method: 'POST',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Backup failed: ${err.detail}`);
      if (banner) banner.style.display = 'none';
      return;
    }

    const data = await res.json();
    if (banner) {
      banner.style.display = 'block';
      banner.innerHTML = `
        ✅ <strong>Backup Completed Successfully!</strong> Archive created: <code>${data.backup_filename}</code><br/>
        <a href="${data.backup_download_url}" target="_blank" class="btn btn-outline" style="margin-top: 6px; padding: 4px 10px; font-size: 0.8rem;">
          ⬇️ Download Backup Archive
        </a>
      `;
    }
    alert(`Full system backup archive created successfully!\nFile: ${data.backup_filename}`);

  } catch (err) {
    alert(`Backup error: ${err}`);
    if (banner) banner.style.display = 'none';
  }
}
