import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView, Alert } from 'react-native';
import { getServerIp, saveServerIp, getIpsGuardadas, eliminarIp, detectarIpActiva, getAdminPassword, saveAdminPassword } from '../config';
import authService from '../services/authService';

export default function ConfiguracionScreen({ navigation, route }) {
  const [ip, setIp] = useState('');
  const [password, setPassword] = useState('');
  const [ipsGuardadas, setIpsGuardadas] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [user, setUser] = useState(null);
  const primeraVez = route.params?.primeraVez || false;

  useEffect(() => { cargarDatos(); }, []);

  const cargarDatos = async () => {
    const [ipActual, pwd, lista, currentUser] = await Promise.all([
      getServerIp(), getAdminPassword(), getIpsGuardadas(), authService.getUser(),
    ]);
    setIp(ipActual); setPassword(pwd); setIpsGuardadas(lista); setUser(currentUser);
  };

  const guardar = async () => {
    if (!ip) { Alert.alert('Error', 'Ingresa una IP valida'); return; }
    await saveServerIp(ip);
    await saveAdminPassword(password);
    Alert.alert('Exito', 'Configuracion guardada');
    await cargarDatos();
    if (primeraVez) navigation.replace('Login');
  };

  const buscarAutomatico = async () => {
    setBuscando(true);
    try {
      const ipEncontrada = await detectarIpActiva(password);
      if (ipEncontrada) { setIp(ipEncontrada); Alert.alert('Exito', 'Servidor encontrado en ' + ipEncontrada); await cargarDatos(); }
      else Alert.alert('No encontrado', 'No se pudo detectar el servidor');
    } catch (e) { Alert.alert('Error', e.message); }
    finally { setBuscando(false); }
  };

  const seleccionarIp = async (ipSel) => { setIp(ipSel); await saveServerIp(ipSel); await cargarDatos(); };

  const borrarIp = async (ipBorrar) => {
    Alert.alert('Confirmar', 'Eliminar ' + ipBorrar + '?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Eliminar', style: 'destructive', onPress: async () => { await eliminarIp(ipBorrar); await cargarDatos(); } },
    ]);
  };

  const handleLogout = async () => {
    Alert.alert('Cerrar Sesion', 'Estas seguro?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Cerrar Sesion', style: 'destructive', onPress: async () => { await authService.logout(); navigation.replace('Login'); } },
    ]);
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#0f172a' }}>
      <ScrollView style={s.container}>
        <View style={s.section}>
          <Text style={s.title}>Servidor</Text>
          <Text style={s.label}>IP del Servidor</Text>
          <TextInput style={s.input} placeholder="192.168.1.100" placeholderTextColor="#64748b" value={ip} onChangeText={setIp} keyboardType="decimal-pad" autoCorrect={false} autoCapitalize="none" />
          <Text style={s.label}>Contrasena Admin</Text>
          <TextInput style={s.input} placeholder="Contrasena" placeholderTextColor="#64748b" value={password} onChangeText={setPassword} secureTextEntry />
          <TouchableOpacity style={s.btn} onPress={guardar}><Text style={s.btnTxt}>Guardar</Text></TouchableOpacity>
          <TouchableOpacity style={[s.btn, s.btnGray]} onPress={buscarAutomatico} disabled={buscando}>
            <Text style={s.btnTxtWhite}>{buscando ? 'Buscando...' : 'Buscar Automaticamente'}</Text>
          </TouchableOpacity>
        </View>
        {ipsGuardadas.length > 0 && (
          <View style={s.section}>
            <Text style={s.title}>IPs Guardadas</Text>
            {ipsGuardadas.map((ipG) => (
              <View key={ipG} style={s.ipRow}>
                <TouchableOpacity style={s.ipBtn} onPress={() => seleccionarIp(ipG)}>
                  <Text style={s.ipTxt}>{ipG}</Text>
                  {ipG === ip && <Text style={{ color: '#D4920A', fontWeight: 'bold' }}>ok</Text>}
                </TouchableOpacity>
                <TouchableOpacity style={s.delBtn} onPress={() => borrarIp(ipG)}>
                  <Text style={{ color: '#fff', fontWeight: 'bold' }}>X</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}
        {user && (
          <View style={s.section}>
            <Text style={s.title}>Sesion</Text>
            <Text style={s.info}>Usuario: {user.username}</Text>
            <TouchableOpacity style={[s.btn, s.btnRed]} onPress={handleLogout}><Text style={s.btnTxtWhite}>Cerrar Sesion</Text></TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A1017' },
  section: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#1e293b' },
  title: { fontSize: 18, fontWeight: 'bold', color: '#fff', marginBottom: 16 },
  label: { fontSize: 14, color: '#94a3b8', marginBottom: 8 },
  info: { fontSize: 14, color: '#94a3b8', marginBottom: 8 },
  input: { backgroundColor: '#1e293b', borderWidth: 1, borderColor: '#334155', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16, color: '#fff', marginBottom: 16 },
  btn: { backgroundColor: '#D4920A', borderRadius: 8, paddingVertical: 12, alignItems: 'center', marginBottom: 12 },
  btnGray: { backgroundColor: '#1C2B3A', borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' },
  btnRed: { backgroundColor: '#C0392B' },
  btnTxt: { color: '#0A1017', fontSize: 16, fontWeight: '700' },
  btnTxtWhite: { color: '#ffffff', fontSize: 16, fontWeight: '700' },
  ipRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  ipBtn: { flex: 1, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#1e293b', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, marginRight: 8 },
  ipTxt: { color: '#fff', fontSize: 16 },
  delBtn: { backgroundColor: '#C0392B', borderRadius: 8, width: 40, height: 40, justifyContent: 'center', alignItems: 'center' },
});