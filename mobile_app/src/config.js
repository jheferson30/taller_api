import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_PASSWORD = 'la_pulga_fi';

const KEY_IPS = '@taller_server_ips';
const KEY_IP_ACTIVA = '@taller_server_ip';
const KEY_PASSWORD = '@taller_admin_password';

export async function getServerIp() {
  try {
    const ip = await AsyncStorage.getItem(KEY_IP_ACTIVA);
    return ip || '';
  } catch {
    return '';
  }
}

export async function getAdminPassword() {
  try {
    const pwd = await AsyncStorage.getItem(KEY_PASSWORD);
    return pwd || DEFAULT_PASSWORD;
  } catch {
    return DEFAULT_PASSWORD;
  }
}

export async function saveServerIp(ip) {
  await AsyncStorage.setItem(KEY_IP_ACTIVA, ip);
  const lista = await getIpsGuardadas();
  if (!lista.includes(ip)) {
    await AsyncStorage.setItem(KEY_IPS, JSON.stringify([ip, ...lista].slice(0, 5)));
  }
}

export async function saveAdminPassword(password) {
  await AsyncStorage.setItem(KEY_PASSWORD, password);
}

export async function getIpsGuardadas() {
  try {
    const raw = await AsyncStorage.getItem(KEY_IPS);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function eliminarIp(ip) {
  const lista = await getIpsGuardadas();
  const nueva = lista.filter(i => i !== ip);
  await AsyncStorage.setItem(KEY_IPS, JSON.stringify(nueva));
  const activa = await getServerIp();
  if (activa === ip) {
    await AsyncStorage.setItem(KEY_IP_ACTIVA, nueva.length > 0 ? nueva[0] : '');
  }
}

async function probarHost(ip, pwd, timeout) {
  const t = timeout || 1500;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), t);
  try {
    const res = await fetch(`http://${ip}:8000/api/mobile/estadisticas`, {
      headers: { 'X-Admin-Password': pwd },
      signal: controller.signal,
    });
    clearTimeout(timer);
    return res.ok ? ip : null;
  } catch {
    clearTimeout(timer);
    return null;
  }
}

/**
 * Deteccion automatica:
 * 1. Prueba IPs guardadas
 * 2. Escanea rangos comunes de red WiFi
 */
export async function detectarIpActiva(password) {
  const pwd = password || await getAdminPassword();

  // 1. Probar IPs guardadas primero (rapido)
  const lista = await getIpsGuardadas();
  if (lista.length > 0) {
    const resultados = await Promise.allSettled(lista.map(ip => probarHost(ip, pwd, 3000)));
    for (let i = 0; i < resultados.length; i++) {
      if (resultados[i].status === 'fulfilled' && resultados[i].value) {
        await AsyncStorage.setItem(KEY_IP_ACTIVA, lista[i]);
        return lista[i];
      }
    }
  }

  // 2. Escaneo de rangos comunes en paralelo por lotes
  const prefijos = ['192.168.1', '192.168.0', '192.168.100', '192.168.2', '10.0.0', '10.0.1'];
  const candidatos = [];
  for (const prefijo of prefijos) {
    for (let i = 1; i <= 254; i++) {
      candidatos.push(`${prefijo}.${i}`);
    }
  }

  const LOTE = 50;
  for (let i = 0; i < candidatos.length; i += LOTE) {
    const lote = candidatos.slice(i, i + LOTE);
    const res = await Promise.allSettled(lote.map(ip => probarHost(ip, pwd, 800)));
    for (let j = 0; j < res.length; j++) {
      if (res[j].status === 'fulfilled' && res[j].value) {
        const ipEncontrada = lote[j];
        await AsyncStorage.setItem(KEY_IP_ACTIVA, ipEncontrada);
        await saveServerIp(ipEncontrada);
        return ipEncontrada;
      }
    }
  }

  return null;
}

export async function getApiBaseUrl() {
  const ip = await getServerIp();
  return `http://${ip}:8000/api/mobile`;
}

export async function getAuthBaseUrl() {
  const ip = await getServerIp();
  return `http://${ip}:8000`;
}

export async function getPdfBaseUrl() {
  const ip = await getServerIp();
  return `http://${ip}:8000`;
}