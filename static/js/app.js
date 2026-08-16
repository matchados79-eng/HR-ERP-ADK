/* Saudi HR & SME Finance ERP System - Core Application Logic */

let currentEmployeeId = null;
let currentTab = 'tab-info';
let currentUserRole = 'admin';
let allDepartments = [];
let allEmployees = [];
let allUsers = [];
let allSupplierPayments = [];

document.addEventListener('DOMContentLoaded', () => {
  checkAuthSession();
  runEosbCalc();
  runGosiCalc();
});

// Toast Notification System
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = '✅';
  if (type === 'error') icon = '❌';
  if (type === 'info') icon = 'ℹ️';

  toast.innerHTML = `<span>${icon}</span><span style="flex: 1;">${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(50px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

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
      const nameElem = document.getElementById('user-display-name');
      if (nameElem) nameElem.innerText = u.full_name || 'System User';
      const roleElem = document.getElementById('user-display-role');
      if (roleElem) roleElem.innerText = `Role: ${currentUserRole.toUpperCase()} • Active Session`;
    } catch (e) {}
  }

  applyRoleUIRestrictions();
  hideLoginModal();
  loadDashboardData();
  loadDepartments();
  loadEmployees();
  loadPayrollRuns();
  loadLeaves();
  loadSuppliersDirectory();
  loadSupplierPayments();
  loadFinanceAnalytics();
  loadSettings();
  loadUsersList();
}

function applyRoleUIRestrictions() {
  const isViewer = currentUserRole === 'viewer';
  
  const addEmpBtn = document.getElementById('add-emp-btn');
  if (addEmpBtn) addEmpBtn.style.display = isViewer ? 'none' : 'inline-flex';

  const payrollNav = document.getElementById('nav-payroll-item');
  if (payrollNav) payrollNav.style.display = isViewer ? 'none' : 'block';

  const backupBtn = document.getElementById('gdrive-backup-btn');
  if (backupBtn) backupBtn.style.display = isViewer ? 'none' : 'inline-flex';

  const financeNav = document.getElementById('nav-finance-item');
  if (financeNav) financeNav.style.display = isViewer ? 'none' : 'block';

  const settingsNav = document.getElementById('nav-settings-item');
  if (settingsNav) settingsNav.style.display = isViewer ? 'none' : 'block';
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
    showToast(`Welcome back, ${data.user.full_name}! Signed in successfully.`);

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
  showToast('You have been logged out.', 'info');
}

function getAuthHeaders() {
  const token = localStorage.getItem('jwt_token') || '';
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

// Section Switching with robust element selection
function switchSection(sectionId) {
  document.querySelectorAll('.content-section').forEach(sec => sec.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));

  const targetSec = document.getElementById(`section-${sectionId}`);
  if (targetSec) targetSec.classList.add('active');

  const activeLink = document.querySelector(`.nav-link[data-section="${sectionId}"]`);
  if (activeLink) activeLink.classList.add('active');

  const titleMap = {
    'dashboard': ['HR Dashboard', 'Comprehensive overview of Saudi workforce, Saudization rates, and pending actions'],
    'employees': ['Employee Directory', 'Manage employee profiles, Iqama details, GOSI numbers, and document vaults'],
    'departments': ['Department Management', 'Manage organizational departments, manager assignments, and annual budgets'],
    'payroll': ['Payroll & WPS Engine', 'Process monthly salaries, generate SAMA WPS CSV files, and print PDF payslips'],
    'leaves': ['Leave Management', 'Track annual leave balances, sick leave requests, and approval workflows'],
    'compliance': ['Saudi Compliance Hub', 'Interactive EOSB (Articles 84/85/87), GOSI contributions, and Nitaqat tools'],
    'suppliers': ['Supplier Payment Tracking', 'Track vendor invoices, supply dates, due dates, partial payments, and PDF statements'],
    'finance': ['Finance & Aging Analytics', 'Accounts Payable aging schedules, vendor liabilities, and cash outflow forecasting'],
    'settings': ['System & Users Settings', 'Configure company legal details, CR number, user accounts, and backups']
  };

  if (titleMap[sectionId]) {
    document.getElementById('page-heading').innerText = titleMap[sectionId][0];
    document.getElementById('page-subheading').innerText = titleMap[sectionId][1];
  }

  if (sectionId === 'dashboard') loadDashboardData();
  if (sectionId === 'employees') loadEmployees();
  if (sectionId === 'departments') loadDepartments();
  if (sectionId === 'payroll') loadPayrollRuns();
  if (sectionId === 'leaves') loadLeaves();
  if (sectionId === 'suppliers') loadSupplierPayments();
  if (sectionId === 'finance') loadFinanceAnalytics();
  if (sectionId === 'settings') {
    loadSettings();
    loadUsersList();
  }
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
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('stat-total-emp').innerText = data.total_employees;
    document.getElementById('stat-saudization-pct').innerText = `${data.saudization.saudization_percentage}%`;
    document.getElementById('stat-monthly-payroll').innerText = `SAR ${data.total_monthly_payroll.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('stat-pending-payables').innerText = `SAR ${data.pending_supplier_payables.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

    // Nitaqat Banner
    const nb = document.getElementById('nitaqat-banner');
    if (nb) {
      nb.style.backgroundColor = data.saudization.nitaqat_color;
      document.getElementById('nitaqat-band-name').innerText = `Nitaqat Band: ${data.saudization.nitaqat_band}`;
      document.getElementById('nitaqat-status-desc').innerText = data.saudization.status_description;
      document.getElementById('nitaqat-ratio-display').innerText = `${data.saudization.saudization_percentage}%`;
    }

    // Alerts Table
    const alertsBody = document.getElementById('alerts-table-body');
    const badge = document.getElementById('alert-count-badge');
    if (badge) badge.innerText = `${data.expiring_alerts_count} Alerts`;

    if (alertsBody) {
      if (data.alerts_summary.length === 0) {
        alertsBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--success); font-weight: 600;">All Iqama and passport documents are fully up to date!</td></tr>`;
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
    }

    // Dept Distribution Table
    const deptBody = document.getElementById('dept-dist-body');
    if (deptBody) {
      deptBody.innerHTML = data.department_distribution.map(d => `
        <tr>
          <td><strong>${d.name}</strong></td>
          <td><span class="badge badge-saudi">${d.emp_count} Staff</span></td>
        </tr>
      `).join('');
    }

  } catch (err) {
    console.error('Error loading dashboard stats:', err);
  }
}

// 2. DEPARTMENTS CRUD
async function loadDepartments() {
  try {
    const res = await fetch('/api/departments', { headers: getAuthHeaders() });
    if (!res.ok) return;
    allDepartments = await res.json();

    const tbody = document.getElementById('departments-table-body');
    if (tbody) {
      if (allDepartments.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center;">No departments registered yet.</td></tr>`;
      } else {
        tbody.innerHTML = allDepartments.map(d => `
          <tr>
            <td><code>${d.code}</code></td>
            <td><strong>${d.name}</strong></td>
            <td>${d.manager_name || 'Unassigned'}</td>
            <td>SAR ${(d.budget || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
            <td><span class="badge badge-saudi">${d.employee_count} Employees</span></td>
            <td>
              <div style="display: flex; gap: 6px;">
                ${currentUserRole !== 'viewer' ? `
                  <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openEditDepartmentModal(${d.id})">
                    ✏️ Edit
                  </button>
                ` : ''}
                ${currentUserRole === 'admin' ? `
                  <button class="btn btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="deleteDepartment(${d.id}, '${d.name.replace(/'/g, "\\'")}')">
                    🗑️ Delete
                  </button>
                ` : ''}
              </div>
            </td>
          </tr>
        `).join('');
      }
    }

    // Populate dropdowns
    const addSelect = document.getElementById('add-emp-dept-select');
    const editSelect = document.getElementById('edit-emp-dept-select');
    const filterSelect = document.getElementById('emp-filter-dept');

    const optionsHtml = allDepartments.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join('');
    
    if (addSelect) addSelect.innerHTML = optionsHtml;
    if (editSelect) editSelect.innerHTML = optionsHtml;
    if (filterSelect) filterSelect.innerHTML = `<option value="">All Departments</option>` + optionsHtml;

  } catch (err) {
    console.error('Error loading departments:', err);
  }
}

function openAddDepartmentModal() {
  document.getElementById('department-form').reset();
  document.getElementById('dept-id').value = '';
  document.getElementById('dept-modal-title').innerText = '+ Create New Department';
  openModal('modal-department');
}

function openEditDepartmentModal(deptId) {
  const d = allDepartments.find(x => x.id === deptId);
  if (!d) return;

  document.getElementById('dept-id').value = d.id;
  document.getElementById('dept-name').value = d.name;
  document.getElementById('dept-code').value = d.code;
  document.getElementById('dept-manager').value = d.manager_name || '';
  document.getElementById('dept-budget').value = d.budget || 0;
  document.getElementById('dept-modal-title').innerText = '✏️ Edit Department';
  openModal('modal-department');
}

async function submitDepartment() {
  const deptId = document.getElementById('dept-id').value;
  const payload = {
    name: document.getElementById('dept-name').value,
    code: document.getElementById('dept-code').value,
    manager_name: document.getElementById('dept-manager').value,
    budget: parseFloat(document.getElementById('dept-budget').value || 0)
  };

  try {
    const method = deptId ? 'PUT' : 'POST';
    const url = deptId ? `/api/departments/${deptId}` : '/api/departments';

    const res = await fetch(url, {
      method: method,
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Department operation failed', 'error');
      return;
    }

    closeModal('modal-department');
    loadDepartments();
    loadDashboardData();
    showToast(deptId ? 'Department updated successfully!' : 'Department created successfully!');
  } catch (err) {
    showToast(`Error saving department: ${err}`, 'error');
  }
}

async function deleteDepartment(deptId, name) {
  if (!confirm(`Are you sure you want to delete department '${name}'? Staff will be unassigned.`)) return;

  try {
    const res = await fetch(`/api/departments/${deptId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Failed to delete department', 'error');
      return;
    }

    loadDepartments();
    loadEmployees();
    loadDashboardData();
    showToast(`Department '${name}' deleted successfully.`);
  } catch (err) {
    showToast(`Delete error: ${err}`, 'error');
  }
}

// 3. EMPLOYEES CRUD
async function loadEmployees() {
  try {
    const searchElem = document.getElementById('emp-search');
    const search = searchElem ? searchElem.value : '';
    const saudiElem = document.getElementById('emp-filter-saudi');
    const isSaudi = saudiElem ? saudiElem.value : '';
    const deptElem = document.getElementById('emp-filter-dept');
    const deptId = deptElem ? deptElem.value : '';

    let url = `/api/employees?`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (isSaudi !== '') url += `is_saudi=${isSaudi}&`;
    if (deptId) url += `department_id=${deptId}&`;

    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) return;
    allEmployees = await res.json();

    const tbody = document.getElementById('employees-table-body');
    const leaveEmpSelect = document.getElementById('leave-emp-select');
    if (leaveEmpSelect) {
      leaveEmpSelect.innerHTML = allEmployees.map(e => `<option value="${e.id}">${e.emp_code} - ${e.first_name} ${e.last_name}</option>`).join('');
    }

    if (!tbody) return;

    if (allEmployees.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center;">No matching employee records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = allEmployees.map(e => `
      <tr>
        <td><strong>${e.emp_code}</strong></td>
        <td>
          <div style="font-weight: 700;">${e.first_name} ${e.last_name}</div>
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
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="viewEmployeeDetail(${e.id})">
              👁️ View
            </button>
            ${currentUserRole !== 'viewer' ? `
              <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openEditEmployeeModal(${e.id})">
                ✏️ Edit
              </button>
            ` : ''}
            ${currentUserRole === 'admin' ? `
              <button class="btn btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="deleteEmployee(${e.id}, '${e.first_name} ${e.last_name}')">
                🗑️ Delete
              </button>
            ` : ''}
          </div>
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
  data.department_id = data.department_id ? parseInt(data.department_id) : null;
  data.basic_salary = parseFloat(data.basic_salary || 0);
  data.housing_allowance = parseFloat(data.housing_allowance || 0);
  data.transport_allowance = parseFloat(data.transport_allowance || 0);
  data.other_allowances = parseFloat(data.other_allowances || 0);

  try {
    const res = await fetch('/api/employees', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Failed to create employee', 'error');
      return;
    }

    closeModal('modal-add-employee');
    loadEmployees();
    loadDashboardData();
    showToast('Employee profile created successfully!');
  } catch (err) {
    showToast(`Failed to add employee: ${err}`, 'error');
  }
}

function openEditEmployeeModal(empId) {
  const emp = allEmployees.find(x => x.id === empId);
  if (!emp) return;

  document.getElementById('edit-emp-id').value = emp.id;
  document.getElementById('edit-emp-code').value = emp.emp_code;
  document.getElementById('edit-emp-first-name').value = emp.first_name;
  document.getElementById('edit-emp-last-name').value = emp.last_name;
  document.getElementById('edit-emp-arabic-name').value = emp.arabic_name || '';
  document.getElementById('edit-emp-email').value = emp.email;
  document.getElementById('edit-emp-phone').value = emp.phone || '';
  document.getElementById('edit-emp-iqama').value = emp.national_id_iqama;
  document.getElementById('edit-emp-nationality').value = emp.nationality;
  document.getElementById('edit-emp-is-saudi').value = emp.is_saudi;
  if (document.getElementById('edit-emp-dept-select')) document.getElementById('edit-emp-dept-select').value = emp.department_id || '';
  document.getElementById('edit-emp-designation').value = emp.designation;
  document.getElementById('edit-emp-hire-date').value = emp.hire_date;
  document.getElementById('edit-emp-contract-type').value = emp.contract_type || 'Fixed';
  document.getElementById('edit-emp-status').value = emp.status || 'Active';
  document.getElementById('edit-emp-basic-salary').value = emp.basic_salary;
  document.getElementById('edit-emp-housing').value = emp.housing_allowance;
  document.getElementById('edit-emp-transport').value = emp.transport_allowance;
  document.getElementById('edit-emp-other-allow').value = emp.other_allowances;
  document.getElementById('edit-emp-bank-name').value = emp.bank_name || '';
  document.getElementById('edit-emp-iban').value = emp.iban || '';
  document.getElementById('edit-emp-iqama-exp').value = emp.iqama_expiry_date || '';
  document.getElementById('edit-emp-gosi-number').value = emp.gosi_number || '';

  openModal('modal-edit-employee');
}

async function submitEditEmployee() {
  const empId = document.getElementById('edit-emp-id').value;
  const payload = {
    emp_code: document.getElementById('edit-emp-code').value,
    first_name: document.getElementById('edit-emp-first-name').value,
    last_name: document.getElementById('edit-emp-last-name').value,
    arabic_name: document.getElementById('edit-emp-arabic-name').value,
    email: document.getElementById('edit-emp-email').value,
    phone: document.getElementById('edit-emp-phone').value,
    national_id_iqama: document.getElementById('edit-emp-iqama').value,
    nationality: document.getElementById('edit-emp-nationality').value,
    gender: 'Male',
    is_saudi: parseInt(document.getElementById('edit-emp-is-saudi').value),
    dob: null,
    department_id: document.getElementById('edit-emp-dept-select').value ? parseInt(document.getElementById('edit-emp-dept-select').value) : null,
    designation: document.getElementById('edit-emp-designation').value,
    hire_date: document.getElementById('edit-emp-hire-date').value,
    contract_type: document.getElementById('edit-emp-contract-type').value,
    contract_end_date: null,
    iqama_expiry_date: document.getElementById('edit-emp-iqama-exp').value || null,
    passport_number: null,
    passport_expiry_date: null,
    bank_name: document.getElementById('edit-emp-bank-name').value,
    iban: document.getElementById('edit-emp-iban').value,
    basic_salary: parseFloat(document.getElementById('edit-emp-basic-salary').value || 0),
    housing_allowance: parseFloat(document.getElementById('edit-emp-housing').value || 0),
    transport_allowance: parseFloat(document.getElementById('edit-emp-transport').value || 0),
    other_allowances: parseFloat(document.getElementById('edit-emp-other-allow').value || 0),
    gosi_number: document.getElementById('edit-emp-gosi-number').value,
    status: document.getElementById('edit-emp-status').value
  };

  try {
    const res = await fetch(`/api/employees/${empId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Update failed', 'error');
      return;
    }

    closeModal('modal-edit-employee');
    loadEmployees();
    loadDashboardData();
    showToast('Employee profile updated successfully!');
  } catch (err) {
    showToast(`Failed to update employee: ${err}`, 'error');
  }
}

async function deleteEmployee(empId, name) {
  if (!confirm(`Are you sure you want to remove employee ${name}? All linked records will be deleted.`)) return;

  try {
    const res = await fetch(`/api/employees/${empId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Delete failed', 'error');
      return;
    }

    loadEmployees();
    loadDashboardData();
    showToast(`Employee ${name} removed.`);
  } catch (err) {
    showToast(`Delete error: ${err}`, 'error');
  }
}

// 4. EMPLOYEE PROFILE & FILE VAULT
async function viewEmployeeDetail(empId) {
  currentEmployeeId = empId;
  openModal('modal-emp-detail');
  switchTab('tab-info');

  try {
    const res = await fetch(`/api/employees/${empId}`, { headers: getAuthHeaders() });
    if (!res.ok) return;
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
      <div class="form-group"><label>Basic Salary:</label><input type="text" class="form-control" value="${emp.basic_salary ? 'SAR ' + emp.basic_salary.toLocaleString() : 'Restricted'}" readonly></div>
      <div class="form-group"><label>Housing Allowance:</label><input type="text" class="form-control" value="${emp.housing_allowance ? 'SAR ' + emp.housing_allowance.toLocaleString() : 'Restricted'}" readonly></div>
      <div class="form-group"><label>Transport Allowance:</label><input type="text" class="form-control" value="${emp.transport_allowance ? 'SAR ' + emp.transport_allowance.toLocaleString() : 'Restricted'}" readonly></div>
      <div class="form-group"><label>Bank & IBAN:</label><input type="text" class="form-control" value="${emp.bank_name || ''} - ${emp.iban || ''}" readonly></div>
      <div class="form-group"><label>Iqama Expiry Date:</label><input type="text" class="form-control" value="${emp.iqama_expiry_date || 'N/A'}" readonly></div>
      <div class="form-group"><label>Contract Type:</label><input type="text" class="form-control" value="${emp.contract_type || 'Fixed'}" readonly></div>
    `;

    // GOSI Box
    const gosi = data.gosi_breakdown;
    document.getElementById('detail-gosi-box').innerHTML = `
      <div class="card" style="background: #F0FDF4; border-color: #A7F3D0; margin-bottom: 0;">
        <h4 style="color: #065F46; margin-bottom: 10px;">GOSI Contribution Profile</h4>
        <p style="font-size: 0.88rem;">GOSI Number: <strong>${emp.gosi_number || 'N/A'}</strong></p>
        <p style="font-size: 0.88rem;">Eligible Monthly Base Wage: <strong>SAR ${gosi.gosi_base.toLocaleString()}</strong></p>
        <hr style="margin: 10px 0; border: none; border-top: 1px solid #A7F3D0;">
        <div style="display: flex; justify-content: space-between; font-size: 0.88rem;">
          <span>Employee Deduction: <strong>SAR ${gosi.employee_deduction.toLocaleString()}</strong></span>
          <span>Employer Contribution: <strong>SAR ${gosi.employer_contribution.toLocaleString()}</strong></span>
        </div>
      </div>
    `;

    // Docs Table
    const docsBody = document.getElementById('detail-docs-body');
    if (data.documents.length === 0) {
      docsBody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No documents uploaded to vault yet.</td></tr>`;
    } else {
      docsBody.innerHTML = data.documents.map(d => `
        <tr>
          <td><span class="badge badge-saudi">${d.doc_type}</span></td>
          <td><strong>${d.file_name}</strong></td>
          <td>${d.upload_date}</td>
          <td>${d.expiry_date || 'N/A'}</td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="downloadDocumentFile(${d.id})">
                ⬇️ Download
              </button>
              ${currentUserRole !== 'viewer' ? `
                <button class="btn btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="deleteDocument(${d.id})">
                  🗑️
                </button>
              ` : ''}
            </div>
          </td>
        </tr>
      `).join('');
    }

    // Leaves Table
    const leavesBody = document.getElementById('detail-leaves-body');
    if (data.leaves.length === 0) {
      leavesBody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No leave applications found for this employee.</td></tr>`;
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

  const activeBtn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  if (activeBtn) activeBtn.classList.add('active');
  const activeContent = document.getElementById(tabId);
  if (activeContent) activeContent.classList.add('active');
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
      showToast(err.detail || 'Photo upload failed', 'error');
      return;
    }

    const data = await res.json();
    document.getElementById('detail-avatar').src = `${data.photo_url}?t=${Date.now()}`;
    showToast('Employee photo updated successfully!');
    loadEmployees();

  } catch (err) {
    showToast(`Photo upload error: ${err}`, 'error');
  }
}

// Upload Document Handler
async function submitUploadDocument() {
  const docType = document.getElementById('upload-doc-type').value;
  const expiryDate = document.getElementById('upload-doc-expiry').value;
  const fileInput = document.getElementById('upload-doc-file');

  if (!fileInput.files || !fileInput.files[0]) {
    showToast('Please select a file to upload.', 'error');
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
      showToast(err.detail || 'Document upload failed', 'error');
      return;
    }

    showToast('Document uploaded to vault!');
    fileInput.value = '';
    viewEmployeeDetail(currentEmployeeId);

  } catch (err) {
    showToast(`Document upload error: ${err}`, 'error');
  }
}

async function deleteDocument(docId) {
  if (!confirm('Are you sure you want to delete this document from the vault?')) return;

  try {
    const res = await fetch(`/api/documents/${docId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      showToast('Failed to delete document', 'error');
      return;
    }

    showToast('Document removed from vault.');
    viewEmployeeDetail(currentEmployeeId);
  } catch (err) {
    showToast(`Delete error: ${err}`, 'error');
  }
}

// 5. PAYROLL & WPS
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
        <td>Period ${r.payroll_month}/${r.payroll_year}</td>
        <td>SAR ${r.total_basic.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
        <td>SAR ${r.total_allowances.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
        <td>SAR ${r.total_deductions.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
        <td><strong style="color: var(--primary); font-size: 1rem;">SAR ${r.total_net_pay.toLocaleString('en-US', {minimumFractionDigits: 2})}</strong></td>
        <td><span class="badge badge-active">${r.status}</span></td>
        <td>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <button class="btn btn-success" style="padding: 2px 8px; font-size: 0.75rem;" onclick="downloadWpsFile(${r.id})">
              🇸🇦 SAMA WPS CSV
            </button>
            <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="viewPayrollDetails(${r.id})">
              Payslips
            </button>
            ${currentUserRole === 'admin' ? `
              <button class="btn btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="deletePayrollRun(${r.id})">
                🗑️
              </button>
            ` : ''}
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
      showToast(err.detail || 'Payroll execution failed', 'error');
      return;
    }

    closeModal('modal-run-payroll');
    loadPayrollRuns();
    loadDashboardData();
    showToast('Monthly Payroll processed! WPS file and PDF payslips ready.');

  } catch (err) {
    showToast(`Payroll processing failed: ${err}`, 'error');
  }
}

async function deletePayrollRun(runId) {
  if (!confirm(`Are you sure you want to delete Payroll Run #${runId}?`)) return;

  try {
    const res = await fetch(`/api/payroll/runs/${runId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      showToast('Failed to delete payroll run', 'error');
      return;
    }

    loadPayrollRuns();
    loadDashboardData();
    showToast('Payroll run deleted successfully.');
  } catch (err) {
    showToast(`Delete error: ${err}`, 'error');
  }
}

async function viewPayrollDetails(runId) {
  try {
    const res = await fetch(`/api/payroll/runs/${runId}/details`, { headers: getAuthHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    let popupContent = `
      <div style="max-height: 420px; overflow-y: auto;">
        <table class="data-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Basic</th>
              <th>Allowances</th>
              <th>GOSI Deduction</th>
              <th>Net Salary</th>
              <th>Payslip PDF</th>
            </tr>
          </thead>
          <tbody>
            ${data.details.map(d => `
              <tr>
                <td><strong>${d.first_name} ${d.last_name}</strong><br/><small>${d.emp_code}</small></td>
                <td>SAR ${d.basic_salary.toLocaleString()}</td>
                <td>SAR ${(d.housing_allowance + d.transport_allowance + d.other_allowances).toLocaleString()}</td>
                <td>SAR ${d.gosi_employee.toLocaleString()}</td>
                <td><strong style="color: var(--primary);">SAR ${d.net_salary.toLocaleString()}</strong></td>
                <td>
                  <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openPayslipPdf(${d.id})">
                    📄 Payslip PDF
                  </button>
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
          <h3 class="modal-title">Payroll Period: ${data.run.payroll_month}/${data.run.payroll_year}</h3>
          <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
        </div>
        <div class="modal-body">${popupContent}</div>
      </div>
    `;
    document.body.appendChild(m);

  } catch (err) {
    showToast(`Failed to load payroll details: ${err}`, 'error');
  }
}

// 6. LEAVES
async function loadLeaves() {
  try {
    const res = await fetch('/api/leaves', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const leaves = await res.json();

    const tbody = document.getElementById('leaves-table-body');
    if (!tbody) return;

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
          <div style="display: flex; gap: 4px; flex-wrap: wrap;">
            ${(l.status === 'Pending' && currentUserRole !== 'viewer') ? `
              <button class="btn btn-success" style="padding: 2px 6px; font-size: 0.75rem;" onclick="updateLeaveStatus(${l.id}, 'Approved')">Approve</button>
              <button class="btn btn-danger" style="padding: 2px 6px; font-size: 0.75rem;" onclick="updateLeaveStatus(${l.id}, 'Rejected')">Reject</button>
            ` : ''}
            ${currentUserRole === 'admin' ? `
              <button class="btn btn-outline" style="padding: 2px 6px; font-size: 0.75rem;" onclick="deleteLeave(${l.id})">🗑️</button>
            ` : ''}
          </div>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Error loading leaves:', err);
  }
}

function openApplyLeaveModal() {
  document.getElementById('apply-leave-form').reset();
  openModal('modal-apply-leave');
}

function calculateLeaveDays() {
  const start = document.getElementById('leave-start-date').value;
  const end = document.getElementById('leave-end-date').value;
  if (!start || !end) return;

  const d1 = new Date(start);
  const d2 = new Date(end);
  const diffTime = d2 - d1;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
  if (diffDays > 0) {
    document.getElementById('leave-days-count').value = diffDays;
  }
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
      showToast(err.detail || 'Leave application failed', 'error');
      return;
    }

    closeModal('modal-apply-leave');
    loadLeaves();
    loadDashboardData();
    showToast('Leave application submitted successfully!');

  } catch (err) {
    showToast(`Error submitting leave: ${err}`, 'error');
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
      showToast('Failed to update leave status', 'error');
      return;
    }

    loadLeaves();
    loadDashboardData();
    showToast(`Leave status updated to ${status}.`);
  } catch (err) {
    showToast(`Error updating leave status: ${err}`, 'error');
  }
}

async function deleteLeave(leaveId) {
  if (!confirm('Are you sure you want to delete this leave record?')) return;

  try {
    const res = await fetch(`/api/leaves/${leaveId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      showToast('Failed to delete leave record', 'error');
      return;
    }

    loadLeaves();
    loadDashboardData();
    showToast('Leave record removed.');
  } catch (err) {
    showToast(`Delete error: ${err}`, 'error');
  }
}

// 7. SUPPLIER DIRECTORY & INVOICES MANAGEMENT
let allSuppliers = [];

function switchSupplierSubTab(tabId) {
  document.querySelectorAll('#section-suppliers .tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('#section-suppliers .tab-content').forEach(c => c.classList.remove('active'));

  const activeBtn = document.querySelector(`#section-suppliers .tab-btn[data-tab="${tabId}"]`);
  if (activeBtn) activeBtn.classList.add('active');
  const activeContent = document.getElementById(tabId);
  if (activeContent) activeContent.classList.add('active');

  if (tabId === 'sup-view-vendors') {
    loadSuppliersDirectory();
  } else if (tabId === 'sup-view-invoices') {
    loadSupplierPayments();
  }
}

async function loadSuppliersDirectory() {
  try {
    const res = await fetch('/api/suppliers', { headers: getAuthHeaders() });
    if (!res.ok) return;
    allSuppliers = await res.json();

    renderSuppliersDirectoryTable(allSuppliers);
  } catch (err) {
    console.error('Error loading suppliers directory:', err);
  }
}

function renderSuppliersDirectoryTable(suppliersList) {
  const tbody = document.getElementById('suppliers-directory-body');
  if (!tbody) return;

  if (suppliersList.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 25px;">No suppliers registered yet. Click <strong>+ Add Supplier / Vendor</strong> to get started.</td></tr>`;
    return;
  }

  tbody.innerHTML = suppliersList.map(sup => `
    <tr>
      <td>
        <strong style="color: var(--text-main); font-size: 0.95rem;">${sup.name}</strong>
        ${sup.bank_name ? `<br/><small style="color: var(--text-muted);">🏦 ${sup.bank_name}</small>` : ''}
      </td>
      <td>${sup.contact_person || '<span style="color:var(--text-muted);">-</span>'}</td>
      <td>
        ${sup.phone ? `<div>📞 ${sup.phone}</div>` : ''}
        ${sup.email ? `<div>✉️ ${sup.email}</div>` : ''}
        ${!sup.phone && !sup.email ? '<span style="color:var(--text-muted);">-</span>' : ''}
      </td>
      <td>
        ${sup.cr_number ? `<div><small>CR:</small> <code>${sup.cr_number}</code></div>` : ''}
        ${sup.vat_number ? `<div><small>VAT:</small> <code>${sup.vat_number}</code></div>` : ''}
        ${!sup.cr_number && !sup.vat_number ? '<span style="color:var(--text-muted);">-</span>' : ''}
      </td>
      <td><span class="badge badge-saudi">${sup.payment_terms || 'Net 30'}</span></td>
      <td><strong>${sup.invoices_count || 0}</strong></td>
      <td>SAR ${(sup.total_billed || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
      <td>
        <strong style="color: ${(sup.total_balance || 0) > 0 ? 'var(--danger)' : 'var(--success)'};">
          SAR ${(sup.total_balance || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}
        </strong>
      </td>
      <td>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          ${currentUserRole !== 'viewer' ? `
            <button class="btn btn-primary" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openRecordInvoiceForSupplier('${sup.name.replace(/'/g, "\\'")}')">
              + Invoice
            </button>
          ` : ''}
          <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openVendorLedgerModal('${sup.name.replace(/'/g, "\\'")}')">
            📊 Ledger
          </button>
          ${currentUserRole !== 'viewer' ? `
            <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openAddSupplierModal(${sup.id})">
              ✏️
            </button>
          ` : ''}
          ${currentUserRole === 'admin' ? `
            <button class="btn btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="deleteSupplier(${sup.id}, '${sup.name.replace(/'/g, "\\'")}')">
              🗑️
            </button>
          ` : ''}
        </div>
      </td>
    </tr>
  `).join('');
}

function filterSuppliersDirectory() {
  const query = (document.getElementById('vendor-directory-search')?.value || '').toLowerCase().trim();
  if (!query) {
    renderSuppliersDirectoryTable(allSuppliers);
    return;
  }

  const filtered = allSuppliers.filter(s => 
    (s.name && s.name.toLowerCase().includes(query)) ||
    (s.contact_person && s.contact_person.toLowerCase().includes(query)) ||
    (s.phone && s.phone.includes(query)) ||
    (s.cr_number && s.cr_number.includes(query)) ||
    (s.email && s.email.toLowerCase().includes(query))
  );

  renderSuppliersDirectoryTable(filtered);
}

function openAddSupplierModal(supId = null) {
  const form = document.getElementById('add-supplier-form');
  if (form) form.reset();

  document.getElementById('supplier-form-id').value = '';
  document.getElementById('modal-supplier-title').innerText = '🏢 Add New Supplier / Vendor';
  document.getElementById('btn-save-supplier').innerText = 'Save Supplier Profile';

  if (supId) {
    const sup = allSuppliers.find(x => x.id === supId);
    if (sup) {
      document.getElementById('supplier-form-id').value = sup.id;
      document.getElementById('modal-supplier-title').innerText = `✏️ Edit Supplier: ${sup.name}`;
      document.getElementById('btn-save-supplier').innerText = 'Update Supplier Profile';
      document.getElementById('sup-name').value = sup.name || '';
      document.getElementById('sup-contact').value = sup.contact_person || '';
      document.getElementById('sup-phone').value = sup.phone || '';
      document.getElementById('sup-email').value = sup.email || '';
      document.getElementById('sup-cr').value = sup.cr_number || '';
      document.getElementById('sup-vat').value = sup.vat_number || '';
      document.getElementById('sup-bank').value = sup.bank_name || '';
      document.getElementById('sup-terms').value = sup.payment_terms || 'Net 30';
      document.getElementById('sup-iban').value = sup.iban || '';
      document.getElementById('sup-address').value = sup.address || '';
    }
  }

  openModal('modal-add-supplier');
}

async function submitAddSupplier() {
  const supId = document.getElementById('supplier-form-id').value;
  const isEdit = Boolean(supId);

  const payload = {
    name: document.getElementById('sup-name').value.trim(),
    contact_person: document.getElementById('sup-contact').value.trim() || null,
    phone: document.getElementById('sup-phone').value.trim() || null,
    email: document.getElementById('sup-email').value.trim() || null,
    cr_number: document.getElementById('sup-cr').value.trim() || null,
    vat_number: document.getElementById('sup-vat').value.trim() || null,
    bank_name: document.getElementById('sup-bank').value.trim() || null,
    payment_terms: document.getElementById('sup-terms').value || 'Net 30',
    iban: document.getElementById('sup-iban').value.trim() || null,
    address: document.getElementById('sup-address').value.trim() || null
  };

  if (!payload.name) {
    showToast('Please enter a Supplier Company Name.', 'error');
    return;
  }

  try {
    const url = isEdit ? `/api/suppliers/${supId}` : '/api/suppliers';
    const method = isEdit ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Failed to save supplier profile', 'error');
      return;
    }

    closeModal('modal-add-supplier');
    loadSuppliersDirectory();
    loadSupplierPayments();
    showToast(isEdit ? 'Supplier updated successfully!' : 'Supplier created successfully!');
  } catch (err) {
    showToast(`Supplier save error: ${err}`, 'error');
  }
}

async function deleteSupplier(supId, name) {
  if (!confirm(`Are you sure you want to delete supplier "${name}"?`)) return;

  try {
    const res = await fetch(`/api/suppliers/${supId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Failed to delete supplier', 'error');
      return;
    }

    loadSuppliersDirectory();
    showToast(`Supplier "${name}" deleted.`);
  } catch (err) {
    showToast(`Delete error: ${err}`, 'error');
  }
}

function populateSupplierDropdown(selectedName = '') {
  const select = document.getElementById('record-supplier-select');
  const customInput = document.getElementById('record-supplier-custom-name');
  if (!select) return;

  select.innerHTML = '<option value="">-- Choose Registered Supplier --</option>' +
    allSuppliers.map(s => `<option value="${s.name}" ${s.name === selectedName ? 'selected' : ''}>${s.name}</option>`).join('') +
    '<option value="__NEW__">➕ Enter New Supplier / Vendor Name...</option>';

  if (selectedName && allSuppliers.some(s => s.name === selectedName)) {
    select.value = selectedName;
    if (customInput) {
      customInput.style.display = 'none';
      customInput.value = selectedName;
    }
  } else if (selectedName) {
    select.value = '__NEW__';
    if (customInput) {
      customInput.style.display = 'block';
      customInput.value = selectedName;
    }
  } else {
    if (customInput) {
      customInput.style.display = 'none';
      customInput.value = '';
    }
  }
}

function handleSupplierSelectChange(val) {
  const customInput = document.getElementById('record-supplier-custom-name');
  if (!customInput) return;

  if (val === '__NEW__') {
    customInput.style.display = 'block';
    customInput.value = '';
    customInput.focus();
  } else if (val) {
    customInput.style.display = 'none';
    customInput.value = val;
  } else {
    customInput.style.display = 'none';
    customInput.value = '';
  }
}

function openRecordInvoiceForSupplier(supplierName) {
  openRecordSupplierPaymentModal(supplierName);
}

function exportAccountsPayablePdf() {
  openExportApReportModal();
}

function openExportApReportModal() {
  populateReportSuppliersCheckboxes();
  
  const allRadio = document.querySelector('input[name="ap-report-scope"][value="all"]');
  if (allRadio) allRadio.checked = true;
  toggleSupplierSelectionScope('all');

  const statusEl = document.getElementById('ap-report-status');
  if (statusEl) statusEl.value = '';
  const startEl = document.getElementById('ap-report-start-date');
  if (startEl) startEl.value = '';
  const endEl = document.getElementById('ap-report-end-date');
  if (endEl) endEl.value = '';

  openModal('modal-export-ap-report');
}

function toggleSupplierSelectionScope(scope) {
  const container = document.getElementById('ap-report-suppliers-container');
  if (!container) return;
  container.style.display = scope === 'custom' ? 'block' : 'none';
}

function populateReportSuppliersCheckboxes() {
  const list = document.getElementById('ap-report-suppliers-list');
  if (!list) return;

  if (allSuppliers.length === 0) {
    list.innerHTML = `<div style="color: var(--text-muted); font-size: 0.8rem;">No suppliers registered yet.</div>`;
    return;
  }

  list.innerHTML = allSuppliers.map(s => {
    const bal = s.total_balance || 0;
    return `
      <label style="display: flex; align-items: center; justify-content: space-between; padding: 5px 8px; border-radius: 4px; background: white; border: 1px solid #E2E8F0; cursor: pointer; margin-bottom: 2px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <input type="checkbox" class="report-sup-checkbox" value="${s.name}" checked>
          <span style="font-weight: 600; font-size: 0.82rem; color: var(--text-main);">${s.name}</span>
        </div>
        <span style="font-size: 0.75rem; color: ${bal > 0 ? 'var(--danger)' : 'var(--success)'}; font-weight: 700;">
          SAR ${bal.toLocaleString('en-US', {minimumFractionDigits: 2})}
        </span>
      </label>
    `;
  }).join('');
}

function selectAllReportSuppliers(selectAll) {
  document.querySelectorAll('.report-sup-checkbox').forEach(cb => {
    cb.checked = selectAll;
  });
}

function submitGenerateApReportPdf() {
  const scope = document.querySelector('input[name="ap-report-scope"]:checked')?.value || 'all';
  let selectedVendors = [];

  if (scope === 'custom') {
    const checked = Array.from(document.querySelectorAll('.report-sup-checkbox:checked')).map(cb => cb.value);
    if (checked.length === 0) {
      showToast('Please select at least one supplier to include in the report.', 'error');
      return;
    }
    selectedVendors = checked;
  }

  const status = document.getElementById('ap-report-status')?.value || '';
  const startDate = document.getElementById('ap-report-start-date')?.value || '';
  const endDate = document.getElementById('ap-report-end-date')?.value || '';

  const token = localStorage.getItem('jwt_token') || '';

  let url = `/api/suppliers/export/pdf?token=${encodeURIComponent(token)}&`;
  if (selectedVendors.length > 0) {
    url += `suppliers=${encodeURIComponent(selectedVendors.join(','))}&`;
  }
  if (status) url += `status=${encodeURIComponent(status)}&`;
  if (startDate) url += `start_date=${encodeURIComponent(startDate)}&`;
  if (endDate) url += `end_date=${encodeURIComponent(endDate)}&`;

  closeModal('modal-export-ap-report');
  window.open(url, '_blank');
  showToast('Accounts Payable PDF Report generated!');
}

// 7. SUPPLIER PAYMENTS & AP
async function loadSupplierPayments() {
  try {
    // Also refresh suppliers cache
    loadSuppliersDirectory();

    const search = document.getElementById('supplier-search') ? document.getElementById('supplier-search').value : '';
    const status = document.getElementById('supplier-filter-status') ? document.getElementById('supplier-filter-status').value : '';

    let url = '/api/suppliers/payments?';
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (status) url += `status=${encodeURIComponent(status)}&`;

    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) return;
    const payload = await res.json();

    const sum = payload.summary;
    allSupplierPayments = payload.payments;

    // Update KPI Cards
    if (document.getElementById('sp-kpi-total-billed')) {
      let totBilled = allSupplierPayments.reduce((a, b) => a + (b.amount || 0), 0);
      let totPaid = allSupplierPayments.reduce((a, b) => a + (b.paid_amount || 0), 0);
      let totRem = sum.total_outstanding_payable || 0;
      let totOver = sum.total_overdue_payable || 0;

      document.getElementById('sp-kpi-total-billed').innerText = `SAR ${totBilled.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('sp-kpi-total-paid').innerText = `SAR ${totPaid.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('sp-kpi-total-remaining').innerText = `SAR ${totRem.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('sp-kpi-total-overdue').innerText = `SAR ${totOver.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    }

    const tbody = document.getElementById('supplier-payments-body');
    if (!tbody) return;

    if (allSupplierPayments.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 25px;">No supplier payment records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = allSupplierPayments.map(sp => {
      const tot = sp.amount || 0.0;
      const pd = sp.paid_amount || 0.0;
      const rem = sp.remaining_amount !== undefined ? sp.remaining_amount : Math.max(0, tot - pd);

      const startD = sp.supply_start_date || sp.supply_date || '';
      const endD = sp.supply_end_date || sp.supply_date || '';
      const supplyPeriod = (startD && endD && startD !== endD) ? `${startD} <span style="color:var(--text-muted);">to</span> ${endD}` : (startD || 'N/A');

      return `
        <tr>
          <td>#INV-${sp.id}</td>
          <td>
            <a href="javascript:void(0)" style="font-weight: 700; color: var(--primary); text-decoration: underline;" onclick="openVendorLedgerModal('${sp.company_name.replace(/'/g, "\\'")}')">
              ${sp.company_name}
            </a>
          </td>
          <td><code>${sp.invoice_number || 'N/A'}</code></td>
          <td style="font-size: 0.82rem;">${supplyPeriod}</td>
          <td>${sp.due_date}</td>
          <td>SAR ${tot.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
          <td><span style="color: var(--primary); font-weight: 600;">SAR ${pd.toLocaleString('en-US', {minimumFractionDigits: 2})}</span></td>
          <td><strong style="color: ${rem > 0 ? 'var(--danger)' : 'var(--success)'};">SAR ${rem.toLocaleString('en-US', {minimumFractionDigits: 2})}</strong></td>
          <td>
            <span class="badge ${sp.status === 'Paid' ? 'badge-active' : (sp.status === 'Partially Paid' ? 'badge-pending' : 'badge-critical')}">
              ${sp.status}
            </span>
          </td>
          <td>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
              ${rem > 0 && currentUserRole !== 'viewer' ? `
                <button class="btn btn-success" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openDisburseSupplierPaymentModal(${sp.id}, '${sp.company_name.replace(/'/g, "\\'")}', ${rem})">
                  💳 Disburse
                </button>
              ` : ''}
              ${currentUserRole !== 'viewer' ? `
                <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="repeatInvoiceNextMonth(${sp.id})" title="Create recurring invoice for next month with same amount">
                  🔁 Next Month
                </button>
                <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openEditSupplierModal(${sp.id})">
                  ✏️ Edit
                </button>
              ` : ''}
              <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openSupplierStatementPdf(${sp.id})">
                📜 Statement
              </button>
              ${currentUserRole === 'admin' ? `
                <button class="btn btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="deleteSupplierPayment(${sp.id})">🗑️</button>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    console.error('Error loading supplier payments:', err);
  }
}

function openRecordSupplierPaymentModal(prefillSupplierName = '') {
  const form = document.getElementById('record-supplier-form');
  if (form) form.reset();
  
  populateSupplierDropdown(prefillSupplierName);

  const today = new Date().toISOString().split('T')[0];
  const d30 = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  
  const invDate = document.querySelector('#record-supplier-form input[name="invoice_date"]');
  const supStartDate = document.querySelector('#record-supplier-form input[name="supply_start_date"]');
  const supEndDate = document.querySelector('#record-supplier-form input[name="supply_end_date"]');
  const dueDate = document.querySelector('#record-supplier-form input[name="due_date"]');
  const invNum = document.querySelector('#record-supplier-form input[name="invoice_number"]');
  
  if (invDate) invDate.value = today;
  if (supStartDate) supStartDate.value = today;
  if (supEndDate) supEndDate.value = today;
  if (dueDate) dueDate.value = d30;
  if (invNum && !invNum.value) invNum.value = `INV-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;

  openModal('modal-record-supplier');
}

async function submitRecordSupplierPayment() {
  const form = document.getElementById('record-supplier-form');
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  data.amount = parseFloat(data.amount || 0);

  if (!data.company_name || !data.company_name.trim()) {
    showToast('Please enter a Company / Vendor name.', 'error');
    return;
  }

  if (isNaN(data.amount) || data.amount <= 0) {
    showToast('Please enter a valid positive invoice amount.', 'error');
    return;
  }

  try {
    const res = await fetch('/api/suppliers/payments', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const err = await res.json();
      let errMsg = 'Failed to record invoice';
      if (typeof err.detail === 'string') {
        errMsg = err.detail;
      } else if (Array.isArray(err.detail)) {
        errMsg = err.detail.map(e => e.msg || e.message).join(', ');
      }
      showToast(errMsg, 'error');
      return;
    }

    closeModal('modal-record-supplier');
    loadSupplierPayments();
    loadFinanceAnalytics();
    loadDashboardData();
    showToast('Supplier payment invoice recorded successfully!');

  } catch (err) {
    showToast(`Error saving invoice: ${err}`, 'error');
  }
}

function openEditSupplierModal(spId) {
  const sp = allSupplierPayments.find(x => x.id === spId);
  if (!sp) return;

  document.getElementById('edit-supplier-id').value = sp.id;
  document.getElementById('edit-supplier-company').value = sp.company_name;
  document.getElementById('edit-supplier-invoice-num').value = sp.invoice_number || '';
  document.getElementById('edit-supplier-invoice-date').value = sp.invoice_date;
  document.getElementById('edit-supplier-due-date').value = sp.due_date;
  document.getElementById('edit-supplier-supply-start').value = sp.supply_start_date || sp.supply_date || '';
  document.getElementById('edit-supplier-supply-end').value = sp.supply_end_date || sp.supply_date || '';
  document.getElementById('edit-supplier-details').value = sp.invoice_details || '';
  document.getElementById('edit-supplier-amount').value = sp.amount;
  document.getElementById('edit-supplier-status').value = sp.status;
  document.getElementById('edit-supplier-remarks').value = sp.remarks || '';

  openModal('modal-edit-supplier');
}

async function submitEditSupplierPayment() {
  const spId = document.getElementById('edit-supplier-id').value;
  const payload = {
    company_name: document.getElementById('edit-supplier-company').value,
    invoice_number: document.getElementById('edit-supplier-invoice-num').value,
    invoice_date: document.getElementById('edit-supplier-invoice-date').value,
    due_date: document.getElementById('edit-supplier-due-date').value,
    supply_start_date: document.getElementById('edit-supplier-supply-start').value,
    supply_end_date: document.getElementById('edit-supplier-supply-end').value,
    invoice_details: document.getElementById('edit-supplier-details').value,
    amount: parseFloat(document.getElementById('edit-supplier-amount').value || 0),
    status: document.getElementById('edit-supplier-status').value,
    remarks: document.getElementById('edit-supplier-remarks').value
  };

  try {
    const res = await fetch(`/api/suppliers/payments/${spId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Update failed', 'error');
      return;
    }

    showToast('Supplier invoice updated successfully!');
    closeModal('modal-edit-supplier');
    loadSupplierPayments();
    loadFinanceAnalytics();
    loadDashboardData();

  } catch (err) {
    showToast(`Update error: ${err}`, 'error');
  }
}

function addOneMonthToDate(dateStr) {
  if (!dateStr || !dateStr.includes('-')) return new Date().toISOString().split('T')[0];
  const parts = dateStr.split('-');
  let year = parseInt(parts[0], 10);
  let month = parseInt(parts[1], 10);
  let day = parseInt(parts[2], 10);

  month += 1;
  if (month > 12) {
    month = 1;
    year += 1;
  }
  const maxDay = new Date(year, month, 0).getDate();
  const validDay = Math.min(day, maxDay);

  const mm = String(month).padStart(2, '0');
  const dd = String(validDay).padStart(2, '0');
  return `${year}-${mm}-${dd}`;
}

async function repeatInvoiceNextMonth(spId) {
  const sp = allSupplierPayments.find(x => x.id === spId);
  const vendor = sp ? sp.company_name : 'supplier';
  const amt = sp ? `SAR ${Number(sp.amount).toLocaleString('en-US', {minimumFractionDigits: 2})}` : '';
  
  if (!confirm(`Create a recurring next-month invoice for "${vendor}" (${amt}) with dates automatically shifted to next month?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/suppliers/payments/${spId}/repeat-next-month`, {
      method: 'POST',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Failed to create recurring invoice', 'error');
      return;
    }

    const data = await res.json();
    loadSupplierPayments();
    loadFinanceAnalytics();
    loadDashboardData();
    showToast(`✅ Recurring invoice created! Due: ${data.due_date} (SAR ${Number(data.amount).toLocaleString('en-US', {minimumFractionDigits: 2})})`);
  } catch (err) {
    showToast(`Recurring invoice error: ${err}`, 'error');
  }
}

function duplicateInvoiceToNextMonth() {
  const spId = parseInt(document.getElementById('edit-supplier-id')?.value, 10);
  const sp = allSupplierPayments.find(x => x.id === spId);
  if (!sp) return;

  closeModal('modal-edit-supplier');
  openRecordSupplierPaymentModal(sp.company_name);

  const nextInvDate = addOneMonthToDate(sp.invoice_date);
  const nextDueDate = addOneMonthToDate(sp.due_date);
  const nextSupStart = addOneMonthToDate(sp.supply_start_date || sp.supply_date);
  const nextSupEnd = addOneMonthToDate(sp.supply_end_date || sp.supply_date);

  const invDateEl = document.querySelector('#record-supplier-form input[name="invoice_date"]');
  const dueDateEl = document.querySelector('#record-supplier-form input[name="due_date"]');
  const supStartEl = document.querySelector('#record-supplier-form input[name="supply_start_date"]');
  const supEndEl = document.querySelector('#record-supplier-form input[name="supply_end_date"]');
  const detailsEl = document.querySelector('#record-supplier-form input[name="invoice_details"]');
  const amtEl = document.querySelector('#record-supplier-form input[name="amount"]');
  const remarksEl = document.querySelector('#record-supplier-form textarea[name="remarks"]');

  if (invDateEl) invDateEl.value = nextInvDate;
  if (dueDateEl) dueDateEl.value = nextDueDate;
  if (supStartEl) supStartEl.value = nextSupStart;
  if (supEndEl) supEndEl.value = nextSupEnd;
  if (detailsEl) detailsEl.value = sp.invoice_details || '';
  if (amtEl) amtEl.value = sp.amount;
  if (remarksEl) remarksEl.value = `Recurring monthly invoice (cloned from #${sp.id})`;
}

function openDisburseSupplierPaymentModal(spId, companyName, remainingAmount) {
  document.getElementById('disburse-sp-id').value = spId;
  document.getElementById('disburse-modal-title').innerText = `Disburse Payment: ${companyName}`;
  document.getElementById('disburse-current-remaining').innerText = `SAR ${remainingAmount.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
  document.getElementById('disburse-amount').value = remainingAmount;
  document.getElementById('disburse-date').value = new Date().toISOString().split('T')[0];
  document.getElementById('disburse-reference').value = `TXN-${Math.floor(100000 + Math.random() * 900000)}`;
  document.getElementById('disburse-notes').value = 'Payment settlement';
  openModal('modal-disburse-supplier');
}

async function submitDisburseSupplierPayment() {
  const spId = document.getElementById('disburse-sp-id').value;
  const amount = parseFloat(document.getElementById('disburse-amount').value || 0);
  const payDate = document.getElementById('disburse-date').value;
  const method = document.getElementById('disburse-method').value;
  const ref = document.getElementById('disburse-reference').value;
  const notes = document.getElementById('disburse-notes').value;

  if (amount <= 0) {
    showToast('Please enter a valid disbursal amount.', 'error');
    return;
  }

  try {
    const res = await fetch(`/api/suppliers/payments/${spId}/disburse`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        payment_amount: amount,
        payment_date: payDate,
        payment_method: method,
        reference_number: ref,
        notes: notes
      })
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Disbursal failed', 'error');
      return;
    }

    const data = await res.json();
    showToast(`Payment of SAR ${amount.toLocaleString()} disbursed successfully!`);
    closeModal('modal-disburse-supplier');

    loadSupplierPayments();
    loadFinanceAnalytics();
    loadDashboardData();

  } catch (err) {
    showToast(`Disbursal error: ${err}`, 'error');
  }
}

async function openVendorLedgerModal(companyName) {
  openModal('modal-vendor-ledger');
  document.getElementById('vendor-ledger-title').innerText = `Vendor Account Statement: ${companyName}`;

  try {
    const res = await fetch(`/api/suppliers/vendors/${encodeURIComponent(companyName)}/ledger`, { headers: getAuthHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    const sum = data.summary;
    document.getElementById('vendor-ledger-summary-grid').innerHTML = `
      <div style="background: #EFF6FF; padding: 12px; border-radius: 8px; border: 1px solid #BFDBFE;">
        <div style="font-size: 0.75rem; color: #1E40AF; font-weight: 700;">TOTAL INVOICES</div>
        <div style="font-size: 1.3rem; font-weight: 800; color: #1E3A8A;">${sum.total_invoices_count} Invoices</div>
      </div>
      <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #CBD5E1;">
        <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700;">TOTAL BILLED</div>
        <div style="font-size: 1.3rem; font-weight: 800; color: var(--text-main);">SAR ${sum.total_billed.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
      </div>
      <div style="background: #ECFDF5; padding: 12px; border-radius: 8px; border: 1px solid #A7F3D0;">
        <div style="font-size: 0.75rem; color: #065F46; font-weight: 700;">TOTAL DISBURSED</div>
        <div style="font-size: 1.3rem; font-weight: 800; color: var(--primary);">SAR ${sum.total_paid.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
      </div>
      <div style="background: #FEF2F2; padding: 12px; border-radius: 8px; border: 1px solid #FCA5A5;">
        <div style="font-size: 0.75rem; color: #991B1B; font-weight: 700;">BALANCE DUE</div>
        <div style="font-size: 1.3rem; font-weight: 800; color: var(--danger);">SAR ${sum.total_balance.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
      </div>
    `;

    // Render Invoices
    const invBody = document.getElementById('vendor-ledger-invoices-body');
    invBody.innerHTML = data.invoices.map(i => `
      <tr>
        <td><code>${i.invoice_number || 'N/A'}</code></td>
        <td>${i.invoice_date}</td>
        <td>${i.due_date}</td>
        <td>${i.invoice_details || 'N/A'}</td>
        <td>SAR ${i.amount.toLocaleString()}</td>
        <td>SAR ${i.paid_amount.toLocaleString()}</td>
        <td><strong>SAR ${i.remaining_amount.toLocaleString()}</strong></td>
        <td><span class="badge ${i.status === 'Paid' ? 'badge-active' : 'badge-pending'}">${i.status}</span></td>
      </tr>
    `).join('');

    // Render Disbursal Logs
    const logsBody = document.getElementById('vendor-ledger-logs-body');
    if (data.payment_logs.length === 0) {
      logsBody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No disbursal transactions logged yet.</td></tr>`;
    } else {
      logsBody.innerHTML = data.payment_logs.map(l => `
        <tr>
          <td>${l.payment_date}</td>
          <td>${l.payment_method}</td>
          <td><code>${l.reference_number || 'N/A'}</code></td>
          <td><strong style="color: var(--primary);">SAR ${l.payment_amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</strong></td>
          <td>${l.notes || 'N/A'}</td>
        </tr>
      `).join('');
    }

  } catch (err) {
    showToast(`Failed to load vendor ledger: ${err}`, 'error');
  }
}

async function deleteSupplierPayment(id) {
  if (!confirm('Are you sure you want to delete this supplier payment record?')) return;

  try {
    const res = await fetch(`/api/suppliers/payments/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      showToast('Failed to delete invoice record', 'error');
      return;
    }

    loadSupplierPayments();
    loadFinanceAnalytics();
    loadDashboardData();
    showToast('Supplier payment record deleted.');

  } catch (err) {
    showToast(`Delete error: ${err}`, 'error');
  }
}

// 8. FINANCE & AGING ANALYTICS
async function loadFinanceAnalytics() {
  if (currentUserRole === 'viewer') return;

  try {
    const res = await fetch('/api/finance/analytics', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    const sum = data.summary;
    document.getElementById('fin-stat-total-payables').innerText = `SAR ${sum.total_outstanding_payable.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('fin-stat-overdue-payables').innerText = `SAR ${sum.total_overdue_payable.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('fin-stat-overdue-ratio').innerText = `${sum.overdue_ratio_percentage}%`;
    document.getElementById('fin-stat-30d-outflow').innerText = `SAR ${data.projected_30_day_outflow.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

    const agingBody = document.getElementById('finance-aging-table-body');
    if (agingBody) {
      const buckets = data.aging_buckets;
      const keys = ['current', 'days_1_30', 'days_31_60', 'days_61_90', 'days_90_plus'];

      agingBody.innerHTML = keys.map(k => {
        const b = buckets[k];
        const share = sum.total_outstanding_payable > 0 ? ((b.amount / sum.total_outstanding_payable) * 100).toFixed(1) : '0.0';
        return `
          <tr>
            <td>
              <span class="badge" style="background: ${b.color}; color: #FFF;">${b.label}</span>
            </td>
            <td><strong>${b.count} Invoices</strong></td>
            <td><strong style="color: ${b.color}; font-size: 0.95rem;">SAR ${b.amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</strong></td>
            <td>${share}%</td>
            <td>
              <div style="background: #E2E8F0; border-radius: 10px; height: 8px; width: 100%; overflow: hidden;">
                <div style="background: ${b.color}; height: 100%; width: ${Math.min(100, parseFloat(share))}%;"></div>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    const projGrid = document.getElementById('finance-projection-grid');
    if (projGrid) {
      projGrid.innerHTML = `
        <div style="background: #FFFFFF; padding: 18px; border-radius: 10px; border: 1px solid var(--border-color);">
          <div style="font-size: 0.78rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Monthly Payroll Outflow</div>
          <div style="font-size: 1.45rem; font-weight: 800; color: #1E3A8A; margin-top: 4px;">SAR ${data.monthly_payroll_commitment.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
        </div>
        <div style="background: #FFFFFF; padding: 18px; border-radius: 10px; border: 1px solid var(--border-color);">
          <div style="font-size: 0.78rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Outstanding Vendor Liabilities</div>
          <div style="font-size: 1.45rem; font-weight: 800; color: var(--danger); margin-top: 4px;">SAR ${sum.total_outstanding_payable.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
        </div>
        <div style="background: #ECFDF5; padding: 18px; border-radius: 10px; border: 1px solid #A7F3D0;">
          <div style="font-size: 0.78rem; color: #065F46; font-weight: 700; text-transform: uppercase;">Year-to-Date Settled Outflows</div>
          <div style="font-size: 1.45rem; font-weight: 800; color: var(--primary); margin-top: 4px;">SAR ${sum.total_settled_paid.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
        </div>
      `;
    }

  } catch (err) {
    console.error('Error loading finance analytics:', err);
  }
}

// 9. CALCULATORS
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

    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('eosb-net-val').innerText = `SAR ${data.net_eosb.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('eosb-notes-desc').innerHTML = `
      Duration: <strong>${data.years_of_service} Years</strong> (${data.days_worked} days)<br/>
      Entitlement Multiplier: <strong>${data.multiplier_percentage}%</strong> (${data.article})<br/>
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

    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('gosi-emp-share').innerText = `SAR ${data.employee_deduction.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('gosi-empr-share').innerText = `SAR ${data.employer_contribution.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('gosi-total-share').innerText = `SAR ${data.total_gosi.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

  } catch (err) {
    console.error('GOSI Calculation Error:', err);
  }
}

// 10. SETTINGS & USERS
async function loadUsersList() {
  if (currentUserRole === 'viewer') return;
  try {
    const res = await fetch('/api/users', { headers: getAuthHeaders() });
    if (!res.ok) return;
    allUsers = await res.json();

    const tbody = document.getElementById('users-list-body');
    if (!tbody) return;

    tbody.innerHTML = allUsers.map(u => `
      <tr>
        <td>#USR-${u.id}</td>
        <td><strong>${u.full_name}</strong></td>
        <td><code>${u.email}</code></td>
        <td><span class="badge ${u.role === 'admin' ? 'badge-saudi' : (u.role === 'hr_manager' ? 'badge-active' : 'badge-expat')}">${u.role.toUpperCase()}</span></td>
        <td>${u.created_at || 'N/A'}</td>
        <td>
          ${currentUserRole === 'admin' ? `
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-outline" style="padding: 2px 8px; font-size: 0.75rem;" onclick="openEditUserModal(${u.id}, '${u.full_name}', '${u.email}', '${u.role}')">
                ✏️ Edit
              </button>
              <button class="btn btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="deleteUserAccount(${u.id}, '${u.full_name}')">
                🗑️
              </button>
            </div>
          ` : 'Restricted'}
        </td>
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
      showToast(err.detail || 'User creation failed', 'error');
      return;
    }

    showToast(`User account created for ${fullName}!`);
    document.getElementById('create-user-form').reset();
    loadUsersList();

  } catch (err) {
    showToast(`Failed to create user: ${err}`, 'error');
  }
}

function openEditUserModal(userId, fullName, email, role) {
  document.getElementById('edit-user-id').value = userId;
  document.getElementById('edit-user-fullname').value = fullName;
  document.getElementById('edit-user-email').value = email;
  document.getElementById('edit-user-role').value = role;
  document.getElementById('edit-user-password').value = '';
  openModal('modal-edit-user');
}

async function submitEditUser() {
  const userId = document.getElementById('edit-user-id').value;
  const fullName = document.getElementById('edit-user-fullname').value;
  const email = document.getElementById('edit-user-email').value;
  const role = document.getElementById('edit-user-role').value;
  const password = document.getElementById('edit-user-password').value;

  const payload = {
    full_name: fullName,
    email: email,
    role: role
  };
  if (password && password.trim() !== '') {
    payload.password = password.trim();
  }

  try {
    const res = await fetch(`/api/users/${userId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Update failed', 'error');
      return;
    }

    showToast(`Credentials updated for ${fullName}!`);
    closeModal('modal-edit-user');
    loadUsersList();

  } catch (err) {
    showToast(`Failed to update user: ${err}`, 'error');
  }
}

async function deleteUserAccount(userId, fullName) {
  if (!confirm(`Are you sure you want to delete the user account for ${fullName}?`)) return;

  try {
    const res = await fetch(`/api/users/${userId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Delete failed', 'error');
      return;
    }

    showToast(`User account for ${fullName} removed.`);
    loadUsersList();

  } catch (err) {
    showToast(`Failed to delete user: ${err}`, 'error');
  }
}

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

    if (res.ok) showToast('Company settings saved successfully!');
  } catch (err) {
    showToast(`Failed to save settings: ${err}`, 'error');
  }
}

// 11. BACKUP & RESTORE
async function triggerGoogleDriveBackup() {
  const banner = document.getElementById('backup-status-banner');
  if (banner) {
    banner.style.display = 'block';
    banner.innerHTML = '⏳ <strong>Generating full system backup archive...</strong> Please wait...';
  }

  try {
    const res = await fetch('/api/backup/google-drive', {
      method: 'POST',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Backup generation failed', 'error');
      if (banner) banner.style.display = 'none';
      return;
    }

    const data = await res.json();
    if (banner) {
      banner.style.display = 'block';
      banner.innerHTML = `
        ✅ <strong>Backup Completed Successfully!</strong> File: <code>${data.backup_filename}</code><br/>
        <button onclick="downloadBackupArchive('${data.backup_download_url}')" class="btn btn-outline" style="margin-top: 6px; padding: 4px 10px; font-size: 0.8rem;">
          ⬇️ Download Backup Archive (.ZIP)
        </button>
      `;
    }
    showToast(`Backup archive created: ${data.backup_filename}`);

  } catch (err) {
    showToast(`Backup error: ${err}`, 'error');
    if (banner) banner.style.display = 'none';
  }
}

async function submitRestoreBackup() {
  const fileInput = document.getElementById('restore-backup-file');
  if (!fileInput.files || !fileInput.files[0]) {
    showToast('Please select a backup file (.ZIP or .JSON)', 'error');
    return;
  }

  if (!confirm('WARNING: Restoring from a backup will overwrite existing database records with the backup state. Do you wish to proceed?')) {
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  const token = localStorage.getItem('jwt_token') || '';

  try {
    const res = await fetch('/api/backup/restore', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Restore failed', 'error');
      return;
    }

    const data = await res.json();
    showToast('Database successfully restored from backup archive!');
    fileInput.value = '';
    
    // Refresh all data
    loadDashboardData();
    loadDepartments();
    loadEmployees();
    loadPayrollRuns();
    loadLeaves();
    loadSupplierPayments();
    loadFinanceAnalytics();
    loadSettings();
    loadUsersList();

  } catch (err) {
    showToast(`Restore error: ${err}`, 'error');
  }
}

// Authenticated Browser File & PDF Opening Handlers
function openSupplierStatementPdf(spId) {
  const token = localStorage.getItem('jwt_token') || '';
  window.open(`/api/suppliers/payments/${spId}/statement.pdf?token=${encodeURIComponent(token)}`, '_blank');
}

function openPayslipPdf(detailId) {
  const token = localStorage.getItem('jwt_token') || '';
  window.open(`/api/payroll/details/${detailId}/payslip.pdf?token=${encodeURIComponent(token)}`, '_blank');
}

function downloadWpsFile(runId) {
  const token = localStorage.getItem('jwt_token') || '';
  window.open(`/api/payroll/runs/${runId}/wps.csv?token=${encodeURIComponent(token)}`, '_blank');
}

function downloadDocumentFile(docId) {
  const token = localStorage.getItem('jwt_token') || '';
  window.open(`/api/documents/${docId}/download?token=${encodeURIComponent(token)}`, '_blank');
}

function downloadBackupArchive(url) {
  const token = localStorage.getItem('jwt_token') || '';
  const sep = url.includes('?') ? '&' : '?';
  window.open(`${url}${sep}token=${encodeURIComponent(token)}`, '_blank');
}

