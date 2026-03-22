import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_IP = '192.168.100.163';
const DEFAULT_PASSWORD = 'la_pulga_fi';

const KEY_IP = '@taller_server_ip';
const KEY_PASSWORD = '@taller_admin_password';

export async function getServerIp() {
  try {
    const ip = await AsyncStorage.getItem(KEY_IP);
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
  await AsyncStorage.setItem(KEY_IP, ip);
}

export async function saveAdminPassword(password) {
  await AsyncStorage.setItem(KEY_PASSWORD, password);
}

export async function getApiBaseUrl() {
  const ip = await getServerIp();
  return `http://${ip}:8000/api/mobile`;
}

export async function getPdfBaseUrl() {
  const ip = await getServerIp();
  return `http://${ip}:8000`;
}
