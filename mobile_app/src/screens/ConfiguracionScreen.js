import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator,
} from 'react-native';
import {
  getServerIp, getAdminPassword, saveServerIp, saveAdminPassword,
  getIpsGuardadas, eliminarIp, detectarIpActiva,
} from '../config';
import { useToast } from '../components/Toast';

export default function ConfiguracionScreen({ navigation, route }) {
  const primeraVez = route?.params?.primeraVez ?? false;
  const toast = useToast();
  const [ip, setIp] = useState('');
  const [password, setPassword] = useState('');
  const [ipsGuardadas, setIpsGuardadas] = useState([]);
  const [probando, setProbando] = useState(false);
  const [guardando, setGuardando] = useState(false);

  const cargarDatos = useCallback(async () => {
    const [ipActual, pwd, lista] = await Promise.all([
      getServerIp(), getAdminPassword(), getIpsGuardadas(),
    ]);
    setIp(ipActual);
    setPassword(pwd);
    setIpsGuardadas(lista);
  }, []);

  useEffect(() => { cargarDatos(); }, [cargarDatos]);

  const probarConexion = async (ipTarget) => {
    const ipPrueba = (ipTarget || ip).trim();
    if (!ipPrueba) { toast('Ingresa una IP primero', 'warning'); return; }
    setProbando(true);
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(`http://${ipPrueba}:8000/api/mobile/estadisticas`, {
        headers: { 'X-Admin-Password': password },
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.ok) toast(`Servidor encontrado en ${ipPrueba}`, 'success');
      else toast(`El servidor respondio con error ${res.status}`, 'error');
    } catch {
      toast(`No se pudo conectar a ${ipPrueba}:8000`, 'error');
    } finally {
      setProbando(false);
    }
  };

  const guardar = async () => {
    if (!ip.trim()) { toast('La IP no puede estar vacia', 'warning'); return; }
    setGuardando(true);
    try {
      await Promise.all([saveServerIp(ip.trim()), saveAdminPassword(password)]);
      setIpsGuardadas(await getIpsGuardadas());
      toast('Configuracion guardada correctamente', 'success', 2000);
      setTimeout(() => {
        if (primeraVez) navigation.replace('Home');
        else navigation.goBack();
      }, 1200);
    } catch (e) {
      toast('No se pudo guardar: ' + e.message, 'error');
    } finally {
      setGuardando(false);
    }
  };

  const borrarIp = async (ipBorrar) => {
    await eliminarIp(ipBorrar);
    setIpsGuardadas(await getIpsGuardadas());
    setIp(await getServerIp());
    toast('IP eliminada', 'info');
  };

  const autoDetectar = async () => {
    setProbando(true);
    toast('Buscando servidor en la red...', 'info', 15000);
    try {
      const found = await detectarIpActiva(password);
      if (found) {
        setIp(found);
        setIpsGuardadas(await getIpsGuardadas());
        toast(`Servidor encontrado: ${found}`, 'success', 3000);
      } else {
        toast('No se encontro el servidor. Verifica que este encendido y en la misma red.', 'warning', 4000);
      }
    } finally {
      setProbando(false);
    }
  };

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
      {primeraVez && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>No se encontro el servidor. Configura la IP.</Text>
        </View>
      )}
      <Text style={styles.label}>IP del servidor</Text>
      <TextInput style={styles.input} value={ip} onChangeText={setIp}
        placeholder="192.168.1.100" placeholderTextColor="#64748b"
        keyboardType="decimal-pad" autoCapitalize="none" />
      <Text style={styles.label}>Contrasena de administrador</Text>
      <TextInput style={styles.input} value={password} onChangeText={setPassword}
        placeholder="Contrasena" placeholderTextColor="#64748b" secureTextEntry />
      <View style={styles.fila}>
        <TouchableOpacity style={[styles.btn, styles.btnSec, { flex: 1, marginRight: 6 }]}
          onPress={() => probarConexion()} disabled={probando}>
          {probando
            ? <ActivityIndicator color="#3b82f6" size="small" />
            : <Text style={styles.btnSecTxt}>Probar</Text>}
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.btnSec, { flex: 1, marginLeft: 6 }]}
          onPress={autoDetectar} disabled={probando}>
          {probando
            ? <ActivityIndicator color="#3b82f6" size="small" />
            : <Text style={styles.btnSecTxt}>Auto-detectar</Text>}
        </TouchableOpacity>
      </View>
      <TouchableOpacity style={[styles.btn, styles.btnPri]} onPress={guardar} disabled={guardando}>
        {guardando
          ? <ActivityIndicator color="#fff" size="small" />
          : <Text style={styles.btnPriTxt}>Guardar y conectar</Text>}
      </TouchableOpacity>
      {ipsGuardadas.length > 0 && (
        <View style={{ marginTop: 24 }}>
          <Text style={styles.label}>IPs guardadas</Text>
          {ipsGuardadas.map((item) => (
            <View key={item} style={styles.ipFila}>
              <TouchableOpacity style={styles.ipBtn} onPress={() => setIp(item)}>
                <Text style={[styles.ipTxt, item === ip && styles.ipActiva]}>
                  {item === ip ? '* ' : '  '}{item}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.ipProbarBtn} onPress={() => probarConexion(item)}>
                <Text style={styles.ipProbarTxt}>Probar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.ipBorrarBtn} onPress={() => borrarIp(item)}>
                <Text style={styles.ipBorrarTxt}>X</Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a', padding: 16 },
  banner: { backgroundColor: '#7c3aed', borderRadius: 8, padding: 12, marginBottom: 16 },
  bannerText: { color: '#fff', fontSize: 14, textAlign: 'center' },
  label: { color: '#94a3b8', fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: { backgroundColor: '#1e293b', color: '#f1f5f9', borderRadius: 8, padding: 12, fontSize: 15, borderWidth: 1, borderColor: '#334155' },
  fila: { flexDirection: 'row', marginTop: 12 },
  btn: { borderRadius: 8, padding: 13, alignItems: 'center', marginTop: 10 },
  btnPri: { backgroundColor: '#2563eb', marginTop: 16 },
  btnPriTxt: { color: '#fff', fontWeight: 'bold', fontSize: 15 },
  btnSec: { backgroundColor: '#1e293b', borderWidth: 1, borderColor: '#334155' },
  btnSecTxt: { color: '#3b82f6', fontSize: 14 },
  ipFila: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1e293b', borderRadius: 8, marginBottom: 6, paddingLeft: 12 },
  ipBtn: { flex: 1, paddingVertical: 12 },
  ipTxt: { color: '#94a3b8', fontSize: 14 },
  ipActiva: { color: '#3b82f6', fontWeight: 'bold' },
  ipProbarBtn: { paddingHorizontal: 10, paddingVertical: 12 },
  ipProbarTxt: { color: '#3b82f6', fontSize: 13 },
  ipBorrarBtn: { paddingHorizontal: 14, paddingVertical: 12 },
  ipBorrarTxt: { color: '#ef4444', fontSize: 16 },
});