import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_IP = '192.168.100.163';
const DEFAULT_PASSWORD = 'la_pulga_fi';

const KEY_IPS = '@taller_server_ips';       // lista de IPs guardadas
const KEY_IP_ACTIVA = '@taller_server_ip';  // IP que funcionó por última vez
const KEY_PASSWORD = '@taller_admin_password';

export async function getServerIp() {
  try {
    const ip = await AsyncStorage.getItem(KEY_IP_ACTIVA);
    return ip || DEFAULT_IP;
  } catch {
    return DEFAULT_IP;
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
  // Agregar a la lista si no existe
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
    return raw ? JSON.parse(raw) : [DEFAULT_IP];
  } catch {
    return [DEFAULT_IP];
  }
}

export async function eliminarIp(ip) {
  const lista = await getIpsGuardadas();
  const nueva = lista.filter(i => i !== ip);
  await AsyncStorage.setItem(KEY_IPS, JSON.stringify(nueva));
  // Si era la activa, poner la primera disponible
  const activa = await getServerIp();
  if (activa === ip && nueva.length > 0) {
    await AsyncStorage.setItem(KEY_IP_ACTIVA, nueva[0]);
  }
}

/**
 * Prueba todas las IPs guardadas en paralelo y devuelve la primera que responde.
 * Si ninguna responde, devuelve null.
 */
export async function detectarIpActiva(password) {
  const lista = await getIpsGuardadas();
  const pwd = password || await getAdminPassword();

  const resultados = await Promise.allSettled(
    lista.map(async (ip) => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3000);
      try {
        const res = await fetch(`http://${ip}:8000/api/mobile/estadisticas`, {
          headers: { 'X-Admin-Password': pwd },
          signal: controller.signal,
        });
        clearTimeout(timer);
        if (res.ok) return ip;
        throw new Error('no ok');
      } catch {
        clearTimeout(timer);
        throw new Error('sin respuesta');
      }
    })
  );

  for (let i = 0; i < resultados.length; i++) {
    if (resultados[i].status === 'fulfilled') {
      await AsyncStorage.setItem(KEY_IP_ACTIVA, lista[i]);
      return lista[i];
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
