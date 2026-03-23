import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_PASSWORD = 'la_pulga_fi';
const MDNS_HOST = 'taller-pulga.local';

const KEY_IPS = '@taller_server_ips';
const KEY_IP_ACTIVA = '@taller_server_ip';
const KEY_PASSWORD = '@taller_admin_password';

export async function getServerIp() {
  try {
    const ip = await AsyncStorage.getItem(KEY_IP_ACTIVA);
    return ip || MDNS_HOST;
  } catch {
    return MDNS_HOST;
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
  if (activa === ip && nueva.length > 0) {
    await AsyncStorage.setItem(KEY_IP_ACTIVA, nueva[0]);
  }
}

async function probarHost(host, pwd, timeout = 3000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(`http://${host}:8000/api/mobile/estadisticas`, {
      headers: { 'X-Admin-Password': pwd },
      signal: controller.signal,
    });
    clearTimeout(timer);
    return res.ok ? host : null;
  } catch {
    clearTimeout(timer);
    return null;
  }
}

/**
 * Deteccion automatica:
 * 1. Prueba taller-pulga.local (mDNS)
 * 2. Prueba IPs guardadas
 * 3. Escanea rango 192.168.x.x y 10.x.x.x comunes
 */
export async function detectarIpActiva(password) {
  const pwd = password || await getAdminPassword();

  // 1. Intentar mDNS primero
  const mdns = await probarHost(MDNS_HOST, pwd, 2000);
  if (mdns) {
    await AsyncStorage.setItem(KEY_IP_ACTIVA, mdns);
    return mdns;
  }

  // 2. Probar IPs guardadas
  const lista = await getIpsGuardadas();
  if (lista.length > 0) {
    const resultados = await Promise.allSettled(lista.map(ip => probarHost(ip, pwd)));
    for (let i = 0; i < resultados.length; i++) {
      if (resultados[i].status === 'fulfilled' && resultados[i].value) {
        await AsyncStorage.setItem(KEY_IP_ACTIVA, lista[i]);
        return lista[i];
      }
    }
  }

  // 3. Escaneo automatico de rangos comunes (paralelo, rapido)
  const candidatos = [];
  // Rangos mas comunes en redes WiFi de taller/casa
  for (let i = 1; i <= 254; i++) {
    candidatos.push(`192.168.1.${i}`);
    candidatos.push(`192.168.0.${i}`);
    candidatos.push(`192.168.100.${i}`);
    candidatos.push(`10.0.0.${i}`);
    candidatos.push(`10.181.58.${i}`);
  }

  // Escanear en lotes de 30 para no saturar
  const LOTE = 30;
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

export async function getPdfBaseUrl() {
  const ip = await getServerIp();
  return `http://${ip}:8000`;
}