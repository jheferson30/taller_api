import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, Alert,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
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

  // ── Estado del escáner QR ──────────────────────────────────────────────
  const [modoQr, setModoQr] = useState(false);
  const [permisoCamera, solicitarPermiso] = useCameraPermissions();
  const yaLeyoRef = useRef(false); // evita procesar el mismo QR dos veces

  const cargarDatos = useCallback(async () => {
    const [ipActual, pwd, lista] = await Promise.all([
      getServerIp(), getAdminPassword(), getIpsGuardadas(),
    ]);
    setIp(ipActual);
    setPassword(pwd);
    setIpsGuardadas(lista);
  }, []);

  useEffect(() => { cargarDatos(); }, [cargarDatos]);

  // ── Abrir escáner ──────────────────────────────────────────────────────
  const abrirEscanerQr = async () => {
    if (!permisoCamera) return;

    if (!permisoCamera.granted) {
      const resultado = await solicitarPermiso();
      if (!resultado.granted) {
        Alert.alert(
          'Permiso necesario',
          'La app necesita acceso a la cámara para escanear el QR. Habilítalo en los ajustes del teléfono.',
        );
        return;
      }
    }

    yaLeyoRef.current = false;
    setModoQr(true);
  };

  // ── Procesar código QR leído ───────────────────────────────────────────
  const onQrLeido = ({ data }) => {
    // La cámara puede disparar este evento varias veces para el mismo frame
    if (yaLeyoRef.current) return;
    yaLeyoRef.current = true;
    setModoQr(false);

    try {
      // El backend devuelve el payload como base64(JSON)
      const json = JSON.parse(atob(data));
      const { ip: ipQr, password: pwdQr } = json;

      if (!ipQr) {
        toast('QR inválido: no contiene IP', 'error');
        return;
      }

      // Rellenar los campos automáticamente
      setIp(ipQr);
      if (pwdQr) setPassword(pwdQr);

      toast(`QR leído: ${ipQr}`, 'success', 2500);
    } catch {
      toast('No se pudo leer el QR. Asegúrate de apuntar al QR de la pantalla del PC.', 'error', 3000);
    }
  };

  // ── Probar conexión ────────────────────────────────────────────────────
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
      else toast(`El servidor respondió con error ${res.status}`, 'error');
    } catch {
      toast(`No se pudo conectar a ${ipPrueba}:8000`, 'error');
    } finally {
      setProbando(false);
    }
  };

  // ── Guardar ────────────────────────────────────────────────────────────
  const guardar = async () => {
    if (!ip.trim()) { toast('La IP no puede estar vacía', 'warning'); return; }
    setGuardando(true);
    try {
      await Promise.all([saveServerIp(ip.trim()), saveAdminPassword(password)]);
      setIpsGuardadas(await getIpsGuardadas());
      toast('Configuración guardada correctamente', 'success', 2000);
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
        toast('No se encontró el servidor. Verifica que esté encendido y en la misma red.', 'warning', 4000);
      }
    } finally {
      setProbando(false);
    }
  };

  // ── Pantalla del escáner QR ────────────────────────────────────────────
  if (modoQr) {
    return (
      <View style={styles.scannerContainer}>
        <CameraView
          style={styles.camera}
          facing="back"
          barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
          onBarcodeScanned={onQrLeido}
        />

        {/* Overlay con recuadro guía */}
        <View style={styles.overlay}>
          <View style={styles.overlayTop} />
          <View style={styles.overlayMiddle}>
            <View style={styles.overlaySide} />
            <View style={styles.scanBox}>
              {/* Esquinas decorativas */}
              <View style={[styles.corner, styles.cornerTL]} />
              <View style={[styles.corner, styles.cornerTR]} />
              <View style={[styles.corner, styles.cornerBL]} />
              <View style={[styles.corner, styles.cornerBR]} />
            </View>
            <View style={styles.overlaySide} />
          </View>
          <View style={styles.overlayBottom}>
            <Text style={styles.scanInstruccion}>
              Apunta al QR que aparece en la pantalla del PC{'\n'}(página Configuración)
            </Text>
            <TouchableOpacity style={styles.cancelarScanBtn} onPress={() => setModoQr(false)}>
              <Text style={styles.cancelarScanTxt}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    );
  }

  // ── Pantalla normal de configuración ──────────────────────────────────
  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">

      {primeraVez && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>No se encontró el servidor. Configura la IP.</Text>
        </View>
      )}

      {/* Botón QR — la opción más fácil, va primero y bien destacada */}
      <TouchableOpacity style={styles.btnQr} onPress={abrirEscanerQr}>
        <Text style={styles.btnQrIcon}>📷</Text>
        <View>
          <Text style={styles.btnQrTitulo}>Escanear QR del PC</Text>
          <Text style={styles.btnQrSub}>La forma más fácil. Abre Configuración en el PC y apunta aquí.</Text>
        </View>
      </TouchableOpacity>

      <View style={styles.separador}>
        <View style={styles.separadorLinea} />
        <Text style={styles.separadorTxt}>o configura manualmente</Text>
        <View style={styles.separadorLinea} />
      </View>

      <Text style={styles.label}>IP del servidor</Text>
      <TextInput
        style={styles.input}
        value={ip}
        onChangeText={setIp}
        placeholder="192.168.1.100"
        placeholderTextColor="#64748b"
        keyboardType="decimal-pad"
        autoCapitalize="none"
      />

      <Text style={styles.label}>Contraseña de administrador</Text>
      <TextInput
        style={styles.input}
        value={password}
        onChangeText={setPassword}
        placeholder="Contraseña"
        placeholderTextColor="#64748b"
        secureTextEntry
      />

      <View style={styles.fila}>
        <TouchableOpacity
          style={[styles.btn, styles.btnSec, { flex: 1, marginRight: 6 }]}
          onPress={() => probarConexion()}
          disabled={probando}
        >
          {probando
            ? <ActivityIndicator color="#3b82f6" size="small" />
            : <Text style={styles.btnSecTxt}>Probar</Text>}
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.btn, styles.btnSec, { flex: 1, marginLeft: 6 }]}
          onPress={autoDetectar}
          disabled={probando}
        >
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

const SCAN_BOX = 220;
const CORNER = 22;
const CORNER_BORDER = 4;

const styles = StyleSheet.create({
  // ── Contenedor principal ──
  container: { flex: 1, backgroundColor: '#0f172a', padding: 16 },

  // ── Banner primer uso ──
  banner: { backgroundColor: '#7c3aed', borderRadius: 8, padding: 12, marginBottom: 16 },
  bannerText: { color: '#fff', fontSize: 14, textAlign: 'center' },

  // ── Botón QR ──
  btnQr: {
    flexDirection: 'row', alignItems: 'center', gap: 14,
    backgroundColor: '#1e3a5f', borderWidth: 1.5, borderColor: '#3b82f6',
    borderRadius: 12, padding: 16, marginTop: 8,
  },
  btnQrIcon: { fontSize: 32 },
  btnQrTitulo: { color: '#93c5fd', fontWeight: '700', fontSize: 15 },
  btnQrSub: { color: '#64748b', fontSize: 12, marginTop: 2 },

  // ── Separador ──
  separador: { flexDirection: 'row', alignItems: 'center', marginVertical: 20, gap: 8 },
  separadorLinea: { flex: 1, height: 1, backgroundColor: '#1e293b' },
  separadorTxt: { color: '#475569', fontSize: 12 },

  // ── Campos ──
  label: { color: '#94a3b8', fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: {
    backgroundColor: '#1e293b', color: '#f1f5f9', borderRadius: 8,
    padding: 12, fontSize: 15, borderWidth: 1, borderColor: '#334155',
  },

  // ── Botones ──
  fila: { flexDirection: 'row', marginTop: 12 },
  btn: { borderRadius: 8, padding: 13, alignItems: 'center', marginTop: 10 },
  btnPri: { backgroundColor: '#2563eb', marginTop: 16 },
  btnPriTxt: { color: '#fff', fontWeight: 'bold', fontSize: 15 },
  btnSec: { backgroundColor: '#1e293b', borderWidth: 1, borderColor: '#334155' },
  btnSecTxt: { color: '#3b82f6', fontSize: 14 },

  // ── IPs guardadas ──
  ipFila: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#1e293b', borderRadius: 8, marginBottom: 6, paddingLeft: 12,
  },
  ipBtn: { flex: 1, paddingVertical: 12 },
  ipTxt: { color: '#94a3b8', fontSize: 14 },
  ipActiva: { color: '#3b82f6', fontWeight: 'bold' },
  ipProbarBtn: { paddingHorizontal: 10, paddingVertical: 12 },
  ipProbarTxt: { color: '#3b82f6', fontSize: 13 },
  ipBorrarBtn: { paddingHorizontal: 14, paddingVertical: 12 },
  ipBorrarTxt: { color: '#ef4444', fontSize: 16 },

  // ── Escáner QR ──
  scannerContainer: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1 },

  overlay: { ...StyleSheet.absoluteFillObject, justifyContent: 'space-between' },
  overlayTop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.55)' },
  overlayMiddle: { flexDirection: 'row', height: SCAN_BOX },
  overlaySide: { flex: 1, backgroundColor: 'rgba(0,0,0,0.55)' },
  overlayBottom: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.55)',
    alignItems: 'center', justifyContent: 'center', gap: 16,
  },

  scanBox: { width: SCAN_BOX, height: SCAN_BOX },

  // Esquinas del recuadro guía
  corner: { position: 'absolute', width: CORNER, height: CORNER, borderColor: '#3b82f6' },
  cornerTL: { top: 0, left: 0, borderTopWidth: CORNER_BORDER, borderLeftWidth: CORNER_BORDER },
  cornerTR: { top: 0, right: 0, borderTopWidth: CORNER_BORDER, borderRightWidth: CORNER_BORDER },
  cornerBL: { bottom: 0, left: 0, borderBottomWidth: CORNER_BORDER, borderLeftWidth: CORNER_BORDER },
  cornerBR: { bottom: 0, right: 0, borderBottomWidth: CORNER_BORDER, borderRightWidth: CORNER_BORDER },

  scanInstruccion: { color: '#fff', fontSize: 14, textAlign: 'center', lineHeight: 22 },
  cancelarScanBtn: {
    backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 10,
    paddingHorizontal: 28, paddingVertical: 12,
  },
  cancelarScanTxt: { color: '#fff', fontWeight: '700', fontSize: 15 },
});
