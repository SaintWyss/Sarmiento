const state = { devices: [], config: null, owner: null, currentTab: 'linux' };
const $ = id => document.getElementById(id);

function readCookie(...names) {
  for (const name of names) {
    const item = document.cookie.split('; ').find(value => value.startsWith(`${name}=`));
    if (item) return decodeURIComponent(item.slice(name.length + 1));
  }
  return null;
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  if (!['GET', 'HEAD'].includes((options.method || 'GET').toUpperCase())) {
    const csrf = readCookie('__Host-sarmiento_csrf', 'sarmiento_csrf');
    if (csrf) headers['X-Sarmiento-CSRF'] = csrf;
  }
  const response = await fetch(`/api/v1${path}`, {
    credentials: 'same-origin',
    ...options,
    headers,
  });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({ detail: 'Respuesta inválida' }));
  if (!response.ok) throw new Error(data.detail || `Error ${response.status}`);
  return data;
}

function toast(message) {
  const element = $('toast');
  element.textContent = message;
  element.classList.add('show');
  clearTimeout(element._timer);
  element._timer = setTimeout(() => element.classList.remove('show'), 2600);
}

const fmtDate = value => value
  ? new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
  : 'Nunca';

const actionLabels = {
  'auth.login_succeeded': 'Inicio de sesión',
  'auth.login_failed': 'Acceso rechazado',
  'auth.login_blocked': 'Cuenta temporalmente bloqueada',
  'auth.logout': 'Cierre de sesión',
  'auth.password_changed': 'Contraseña modificada',
  'auth.mfa_enabled': 'MFA activado',
  'auth.mfa_disabled': 'MFA desactivado',
  'auth.mfa_verified': 'Segundo factor verificado',
  'enrollment_token.created': 'Token creado',
  'enrollment_token.revoked': 'Token revocado',
  'device.enrolled': 'Dispositivo enrolado',
  'device.updated': 'Dispositivo actualizado',
  'device.credential_rotation_requested': 'Rotación solicitada',
  'device.credential_rotation_issued': 'Nueva credencial emitida',
  'device.credential_rotated': 'Credencial rotada',
  'device.revoked': 'Dispositivo revocado',
};

function showLogin() {
  $('loginView').classList.remove('hidden');
  $('appView').classList.add('hidden');
}

function showApp() {
  $('loginView').classList.add('hidden');
  $('appView').classList.remove('hidden');
}

async function bootstrap() {
  try {
    state.owner = await api('/auth/me');
    showApp();
    state.config = await api('/config/public');
    $('versionLabel').textContent = `v${state.config.version}`;
    $('serverLabel').textContent = `RustDesk: ${state.config.rustdesk_server}`;
    await Promise.all([loadDevices(), loadStats(), loadAudit()]);
  } catch {
    state.owner = null;
    showLogin();
  }
}

async function loadDevices() {
  state.devices = await api('/devices');
  renderDevices();
}

async function loadStats() {
  const stats = await api('/stats');
  $('stats').replaceChildren(...[
    ['Equipos', stats.total_devices],
    ['En línea', stats.online_devices],
    ['Fuera de línea', stats.offline_devices],
    ['Revocados', stats.revoked_devices],
  ].map(([label, value]) => {
    const card = document.createElement('article');
    card.className = 'stat-card';
    const span = document.createElement('span');
    span.textContent = label;
    const strong = document.createElement('strong');
    strong.textContent = value;
    card.append(span, strong);
    return card;
  }));
}

function renderDevices() {
  const term = $('searchInput').value.trim().toLowerCase();
  const filter = $('statusFilter').value;
  const visible = state.devices.filter(device => {
    const haystack = [device.alias, device.rustdesk_id, device.hostname, device.platform, ...device.tags]
      .join(' ')
      .toLowerCase();
    return (!term || haystack.includes(term))
      && (filter === 'all' || (filter === 'online') === device.online);
  });
  $('deviceCount').textContent = `${visible.length} visibles`;
  $('emptyState').classList.toggle('hidden', visible.length > 0);
  $('devices').replaceChildren(...visible.map(deviceCard));
}

function deviceCard(device) {
  const card = document.createElement('article');
  card.className = `device-card ${device.online ? 'online' : ''}`;
  const header = document.createElement('div');
  header.className = 'device-card-header';
  const status = document.createElement('div');
  status.className = 'device-status';
  const dot = document.createElement('span');
  dot.className = 'dot';
  const statusText = document.createElement('span');
  statusText.textContent = device.online ? 'En línea' : 'Fuera de línea';
  status.append(dot, statusText);
  const last = document.createElement('span');
  last.className = 'device-status';
  last.textContent = fmtDate(device.last_seen);
  header.append(status, last);
  const name = document.createElement('div');
  name.className = 'device-name';
  name.textContent = device.alias;
  const id = document.createElement('div');
  id.className = 'device-id';
  id.textContent = `ID ${device.rustdesk_id}`;
  const meta = document.createElement('div');
  meta.className = 'device-meta';
  [device.platform, device.architecture, ...device.tags].filter(Boolean).forEach(text => {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.textContent = text;
    meta.append(tag);
  });
  if (device.credential_rotation_pending) {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.textContent = 'rotación pendiente';
    meta.append(tag);
  }
  const actions = document.createElement('div');
  actions.className = 'card-actions';
  const connect = document.createElement('a');
  connect.className = 'connect';
  connect.href = device.connect_uri;
  connect.textContent = 'Conectar';
  connect.addEventListener('click', () => {
    navigator.clipboard?.writeText(device.rustdesk_id).catch(() => {});
    setTimeout(() => toast(`ID ${device.rustdesk_id} copiado como respaldo`), 700);
  });
  const manage = document.createElement('button');
  manage.className = 'manage';
  manage.textContent = 'Administrar';
  manage.onclick = () => openEdit(device);
  actions.append(connect, manage);
  card.append(header, name, id, meta, actions);
  return card;
}

async function loadAudit() {
  const items = await api('/audit?limit=30');
  $('auditList').replaceChildren(...items.map(item => {
    const row = document.createElement('div');
    row.className = 'audit-row';
    const time = document.createElement('time');
    time.textContent = fmtDate(item.created_at);
    const label = document.createElement('strong');
    label.textContent = actionLabels[item.action] || item.action;
    const actor = document.createElement('span');
    actor.textContent = item.actor_type;
    row.append(time, label, actor);
    return row;
  }));
}

function openEdit(device) {
  $('editDeviceId').value = device.id;
  $('editTitle').textContent = device.alias;
  $('editAlias').value = device.alias;
  $('editTags').value = device.tags.join(', ');
  $('editError').textContent = '';
  $('editDialog').showModal();
}

function installCommand() {
  const token = $('issuedToken').value;
  const base = location.origin;
  if (state.currentTab === 'linux') {
    return `curl -fsSL ${base}/agent/install-linux.sh | sudo bash -s -- --url ${base} --token '${token}'`;
  }
  if (state.currentTab === 'macos') {
    return `curl -fsSL ${base}/agent/install-macos.sh | sudo bash -s -- --url ${base} --token '${token}'`;
  }
  return `iwr ${base}/agent/install-windows.ps1 -UseBasicParsing | iex; Install-SarmientoAgent -Url '${base}' -Token '${token}'`;
}

function updateCommand() {
  $('installCommand').textContent = installCommand();
}

function openSecurity() {
  $('currentPassword').value = '';
  $('newPassword').value = '';
  $('repeatPassword').value = '';
  $('mfaDisablePassword').value = '';
  $('mfaDisableCode').value = '';
  $('mfaEnableCode').value = '';
  $('mfaSetupBox').classList.add('hidden');
  $('recoveryPanel').classList.add('hidden');
  $('passwordError').textContent = '';
  const enabled = Boolean(state.owner?.mfa_enabled);
  $('mfaStatus').textContent = enabled
    ? 'MFA está activado. El inicio de sesión exige TOTP o un código de recuperación.'
    : 'MFA todavía no está activado. Se recomienda para cualquier despliegue accesible desde Internet.';
  $('mfaDisabledPanel').classList.toggle('hidden', enabled);
  $('mfaEnabledPanel').classList.toggle('hidden', !enabled);
  $('passwordDialog').showModal();
}

$('loginForm').addEventListener('submit', async event => {
  event.preventDefault();
  $('loginError').textContent = '';
  try {
    await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        username: $('username').value,
        password: $('password').value,
        verification_code: $('verificationCode').value || null,
      }),
    });
    $('password').value = '';
    $('verificationCode').value = '';
    await bootstrap();
  } catch (error) {
    $('loginError').textContent = error.message;
  }
});

$('viewerButton').onclick = () => {
  const base = location.origin;
  $('viewerLinuxCommand').textContent = `curl -fsSL ${base}/viewer/install-linux.sh | sudo bash -s -- ${base}`;
  $('viewerWindowsCommand').textContent = `iwr ${base}/viewer/install-windows.ps1 -UseBasicParsing | iex; Install-SarmientoViewer -Url '${base}'`;
  $('viewerMacCommand').textContent = `curl -fsSL ${base}/viewer/install-macos.sh | bash`;
  $('viewerDialog').showModal();
};

$('passwordButton').onclick = openSecurity;

$('mfaSetupButton').onclick = async () => {
  try {
    const setup = await api('/auth/mfa/setup', { method: 'POST' });
    $('mfaSecret').value = setup.secret;
    $('mfaUri').value = setup.provisioning_uri;
    $('mfaSetupBox').classList.remove('hidden');
  } catch (error) {
    $('passwordError').textContent = error.message;
  }
};

$('mfaEnableButton').onclick = async () => {
  try {
    const result = await api('/auth/mfa/enable', {
      method: 'POST',
      body: JSON.stringify({ secret: $('mfaSecret').value, code: $('mfaEnableCode').value }),
    });
    $('recoveryCodes').textContent = result.recovery_codes.join('\n');
    $('mfaDisabledPanel').classList.add('hidden');
    $('recoveryPanel').classList.remove('hidden');
    toast('MFA activado. Guardá los códigos antes de continuar.');
  } catch (error) {
    $('passwordError').textContent = error.message;
  }
};

$('copyRecoveryButton').onclick = async () => {
  await navigator.clipboard.writeText($('recoveryCodes').textContent);
  toast('Códigos copiados');
};

$('finishMfaButton').onclick = () => {
  $('passwordDialog').close();
  showLogin();
};

$('mfaDisableButton').onclick = async () => {
  if (!confirm('¿Desactivar MFA? El panel quedará protegido únicamente por contraseña.')) return;
  try {
    await api('/auth/mfa/disable', {
      method: 'POST',
      body: JSON.stringify({
        current_password: $('mfaDisablePassword').value,
        code: $('mfaDisableCode').value,
      }),
    });
    $('passwordDialog').close();
    showLogin();
    toast('MFA desactivado. Iniciá sesión nuevamente.');
  } catch (error) {
    $('passwordError').textContent = error.message;
  }
};

$('changePasswordButton').onclick = async () => {
  const current = $('currentPassword').value;
  const next = $('newPassword').value;
  if (next !== $('repeatPassword').value) {
    $('passwordError').textContent = 'Las contraseñas nuevas no coinciden';
    return;
  }
  try {
    await api('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: current, new_password: next }),
    });
    $('passwordDialog').close();
    showLogin();
    toast('Contraseña cambiada. Iniciá sesión nuevamente.');
  } catch (error) {
    $('passwordError').textContent = error.message;
  }
};

$('logoutButton').onclick = async () => {
  try {
    await api('/auth/logout', { method: 'POST' });
  } finally {
    state.owner = null;
    showLogin();
  }
};

$('refreshButton').onclick = async () => {
  await Promise.all([loadDevices(), loadStats(), loadAudit()]);
  toast('Datos actualizados');
};
$('reloadAudit').onclick = loadAudit;
$('searchInput').oninput = renderDevices;
$('statusFilter').onchange = renderDevices;
$('newTokenButton').onclick = () => {
  $('issuedTokenBox').classList.add('hidden');
  $('tokenError').textContent = '';
  $('tokenDialog').showModal();
};
$('createTokenButton').onclick = async () => {
  try {
    const issued = await api('/enrollment-tokens', {
      method: 'POST',
      body: JSON.stringify({
        label: $('tokenLabel').value,
        ttl_minutes: Number($('tokenTtl').value),
      }),
    });
    $('issuedToken').value = issued.token;
    $('issuedTokenBox').classList.remove('hidden');
    updateCommand();
    toast('Token creado');
  } catch (error) {
    $('tokenError').textContent = error.message;
  }
};
document.querySelectorAll('[data-tab]').forEach(button => {
  button.onclick = () => {
    state.currentTab = button.dataset.tab;
    document.querySelectorAll('[data-tab]').forEach(item => item.classList.toggle('active', item === button));
    updateCommand();
  };
});
$('copyCommandButton').onclick = async () => {
  await navigator.clipboard.writeText(installCommand());
  toast('Comando copiado');
};
$('saveDeviceButton').onclick = async () => {
  try {
    const id = $('editDeviceId').value;
    await api(`/devices/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        alias: $('editAlias').value,
        tags: $('editTags').value.split(',').map(item => item.trim()).filter(Boolean),
      }),
    });
    $('editDialog').close();
    await Promise.all([loadDevices(), loadAudit()]);
    toast('Dispositivo actualizado');
  } catch (error) {
    $('editError').textContent = error.message;
  }
};
$('rotateTokenButton').onclick = async () => {
  if (!confirm('El agente renovará su credencial automáticamente en el próximo heartbeat. ¿Continuar?')) return;
  try {
    const id = $('editDeviceId').value;
    await api(`/devices/${id}/rotate-token`, { method: 'POST' });
    $('editDialog').close();
    await Promise.all([loadDevices(), loadAudit()]);
    toast('Rotación solicitada al agente');
  } catch (error) {
    $('editError').textContent = error.message;
  }
};
$('revokeDeviceButton').onclick = async () => {
  if (!confirm('El agente perderá acceso al control-plane hasta volver a enrolarlo. ¿Revocar?')) return;
  try {
    const id = $('editDeviceId').value;
    await api(`/devices/${id}/revoke`, { method: 'POST' });
    $('editDialog').close();
    await Promise.all([loadDevices(), loadStats(), loadAudit()]);
    toast('Dispositivo revocado');
  } catch (error) {
    $('editError').textContent = error.message;
  }
};

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
bootstrap();
setInterval(() => Promise.all([loadDevices(), loadStats()]).catch(() => {}), 30000);
