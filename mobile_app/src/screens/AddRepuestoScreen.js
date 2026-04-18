import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, Switch,
  StyleSheet, ActivityIndicator, Image,
} from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import { Picker } from '@react-native-picker/picker';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../api';
import { colors } from '../theme';
import { useToast } from '../components/Toast';
import authService from '../services/authService';
import { getApiBaseUrl, getPdfBaseUrl } from '../config';
import { useOffline } from '../hooks/useOffline';
import offlineService from '../services/offlineService';

const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'TRANSFERENCIA', 'TARJETA'];

export default function AddRepuestoScreen({ route, navigation }) {
  const { ticketId } = route.params;
  const toast = useToast();
  const { isOnline } = useOffline();

  const [nombre, setNombre] = useState('');
  const [cantidad, setCantidad] = useState('1');
  const [marcaReferencia, setMarcaReferencia] = useState('');

  const [fueComprado, setFueComprado] = useState(false);
  const [valor, setValor] = useState('');
  const [responsable, setResponsable] = useState('');
  const [nota, setNota] = useState('');
  const [fotoRepuesto, setFotoRepuesto] = useState(null); // foto del repuesto
  const [uriSoporte, setUriSoporte] = useState(null);    // soporte/factura de compra
  const [mecanicos, setMecanicos] = useState([]);

  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    api.getMecanicos().then(setMecanicos).catch(() => {});
  }, []);

  // Foto del repuesto
  const seleccionarFotoRepuesto = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') { toast('Necesitamos acceso a tu galería', 'warning'); return; }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.8 });
    if (!result.canceled) {
      const uri = result.assets[0].uri;
      console.log('Foto seleccionada:', uri);
      setFotoRepuesto(uri);
    }
  };

  const tomarFotoRepuesto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') { toast('Necesitamos acceso a la cámara', 'warning'); return; }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled) {
      const uri = result.assets[0].uri;
      console.log('Foto tomada:', uri);
      setFotoRepuesto(uri);
    }
  };

  // Soporte/factura de compra
  const seleccionarSoporte = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') { toast('Necesitamos acceso a tu galería', 'warning'); return; }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.8 });
    if (!result.canceled) setUriSoporte(result.assets[0].uri);
  };

  const tomarSoporte = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') { toast('Necesitamos acceso a la cámara', 'warning'); return; }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled) setUriSoporte(result.assets[0].uri);
  };

  const ajustarCantidad = (delta) => {
    const actual = parseInt(cantidad, 10) || 1;
    setCantidad(String(Math.max(1, actual + delta)));
  };

  const handleGuardar = async () => {
    if (!nombre.trim()) { toast('El nombre del repuesto es obligatorio', 'warning'); return; }
    const cantidadNum = parseInt(cantidad, 10);
    if (isNaN(cantidadNum) || cantidadNum < 1) { toast('La cantidad debe ser mayor a 0', 'warning'); return; }
    if (fueComprado) {
      const valorNum = parseInt(valor, 10);
      if (isNaN(valorNum) || valorNum <= 0) { toast('Ingresa un valor mayor a 0 para la compra', 'warning'); return; }
    }

    setLoading(true);
    try {
      // Sin conexión: encolar
      if (!isOnline) {
        await offlineService.enqueueOperation({
          type: 'CREATE_REPUESTO_CON_FOTO',
          endpoint: `/tickets/${ticketId}/repuestos`,
          method: 'POST',
          data: {
            ticketId,
            nombre: nombre.trim(),
            cantidad: cantidadNum,
            marcaReferencia: marcaReferencia.trim() || null,
            fotoUri: fotoRepuesto || null,
            fueComprado,
            valor: fueComprado ? parseInt(valor, 10) : 0,
            responsable: responsable || null,
            nota: nota.trim() || null,
            soporteUri: uriSoporte || null,
          },
        });
        toast('Sin conexión — se subirá automáticamente cuando vuelva el internet', 'warning');
        navigation.goBack();
        return;
      }

      // Con conexión: flujo normal
      let foto_url = null;
      if (fotoRepuesto) {
        const baseUrl = await getPdfBaseUrl();
        const filename = fotoRepuesto.split('/').pop();
        const ext = filename.split('.').pop().toLowerCase();
        const type = ext === 'png' ? 'image/png' : 'image/jpeg';
        const formData = new FormData();
        formData.append('file', { uri: fotoRepuesto, name: filename, type });
        const res = await authService.authenticatedRequest(`${baseUrl}/upload/foto`, {
          method: 'POST',
          body: formData,
        });
        if (res.ok) {
          const data = await res.json();
          foto_url = data.url;
        }
      }

      await api.createRepuesto(ticketId, {
        nombre: nombre.trim(),
        cantidad: cantidadNum,
        marca_referencia: marcaReferencia.trim() || null,
        foto_url,
      });

      if (fueComprado) {
        await api.createCompra(ticketId, {
          descripcion: nombre.trim(),
          valor: parseInt(valor, 10),
          responsable: responsable || null,
          nota: nota.trim() || null,
        }, uriSoporte || fotoRepuesto);
      }

      navigation.goBack();
    } catch (e) {
      const tienefoto = !!(fotoRepuesto || uriSoporte);
      const msg = e.message?.toLowerCase().includes('network')
        ? tienefoto
          ? 'Error de red al subir la foto. Verifica tu conexión WiFi e intenta de nuevo, o quita la foto y guarda sin ella.'
          : 'Error de red. Verifica tu conexión e intenta de nuevo.'
        : e.message;
      toast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAwareScrollView
      style={styles.container}
      keyboardShouldPersistTaps="handled"
      enableOnAndroid
      extraScrollHeight={20}
    >
      <View style={styles.form}>
        <Text style={styles.label}>Nombre del repuesto *</Text>
        <TextInput
          style={styles.input}
          placeholder="Ej: Filtro de aceite, Pastillas de freno..."
          placeholderTextColor={colors.textMuted}
          value={nombre}
          onChangeText={setNombre}
          autoFocus
        />

        <Text style={styles.label}>Cantidad *</Text>
        <View style={styles.cantidadRow}>
          <TouchableOpacity style={styles.cantBtn} onPress={() => ajustarCantidad(-1)}>
            <Text style={styles.cantBtnText}>−</Text>
          </TouchableOpacity>
          <TextInput
            style={styles.cantInput}
            value={cantidad}
            onChangeText={setCantidad}
            keyboardType="numeric"
            textAlign="center"
          />
          <TouchableOpacity style={styles.cantBtn} onPress={() => ajustarCantidad(1)}>
            <Text style={styles.cantBtnText}>+</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.label}>Marca / Referencia</Text>
        <TextInput
          style={styles.input}
          placeholder="Ej: Bosch, NGK, OEM..."
          placeholderTextColor={colors.textMuted}
          value={marcaReferencia}
          onChangeText={setMarcaReferencia}
        />

        {/* Foto del repuesto (siempre disponible) */}
        <Text style={styles.label}>Foto del repuesto (opcional)</Text>
        <View style={styles.botonesRow}>
          <TouchableOpacity style={styles.btnFoto} onPress={tomarFotoRepuesto}>
            <Ionicons name="camera-outline" size={18} color={colors.primary} style={{marginRight: 6}} />
            <Text style={styles.btnFotoText}>Cámara</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.btnFoto} onPress={seleccionarFotoRepuesto}>
            <Ionicons name="images-outline" size={18} color={colors.primary} style={{marginRight: 6}} />
            <Text style={styles.btnFotoText}>Galería</Text>
          </TouchableOpacity>
        </View>
        {fotoRepuesto ? (
          <View style={styles.previewContainer}>
            <Image
              key={fotoRepuesto}
              source={{ uri: fotoRepuesto }}
              style={styles.preview}
              resizeMode="cover"
              onError={(e) => console.log('Error imagen:', e.nativeEvent.error)}
              onLoad={() => console.log('Imagen cargada OK')}
            />
            <TouchableOpacity style={styles.removeBtn} onPress={() => setFotoRepuesto(null)}>
              <Text style={styles.removeBtnText}>Quitar</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderText}>Sin foto adjunta (opcional)</Text>
          </View>
        )}

        {/* Toggle ¿Fue comprado? */}
        <View style={styles.toggleRow}>
          <Text style={styles.toggleLabel}>¿Fue comprado?</Text>
          <Switch
            value={fueComprado}
            onValueChange={setFueComprado}
            trackColor={{ false: colors.border, true: colors.primary }}
            thumbColor={fueComprado ? '#fff' : '#f4f3f4'}
          />
        </View>

        {fueComprado && (
          <>
            <Text style={styles.label}>Valor *</Text>
            <TextInput
              style={styles.input}
              placeholder="0"
              placeholderTextColor={colors.textMuted}
              value={valor ? Number(valor).toLocaleString('es-CO') : ''}
              onChangeText={(t) => setValor(t.replace(/\D/g, ''))}
              keyboardType="numeric"
            />

            <Text style={styles.label}>Responsable</Text>
            {mecanicos.length > 0 ? (
              <View style={styles.pickerWrapper}>
                <Picker
                  selectedValue={responsable}
                  onValueChange={setResponsable}
                  style={styles.picker}
                  dropdownIconColor={colors.textMuted}
                >
                  <Picker.Item label="— Sin asignar —" value="" />
                  {mecanicos.filter(m => m.activo).map((m) => (
                    <Picker.Item key={m.id} label={m.nombre} value={m.nombre} />
                  ))}
                </Picker>
              </View>
            ) : (
              <TextInput
                style={styles.input}
                placeholder="Nombre del responsable"
                placeholderTextColor={colors.textMuted}
                value={responsable}
                onChangeText={setResponsable}
              />
            )}

            <Text style={styles.label}>Nota</Text>
            <TextInput
              style={[styles.input, { height: 80, paddingTop: 12 }]}
              placeholder="Notas adicionales..."
              placeholderTextColor={colors.textMuted}
              value={nota}
              onChangeText={setNota}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />
          </>
        )}

        <TouchableOpacity
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={handleGuardar}
          disabled={loading}
        >
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Guardar Repuesto</Text>}
        </TouchableOpacity>

        <TouchableOpacity style={styles.cancelBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.cancelText}>Cancelar</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAwareScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A1017' },
  form: { padding: 20 },
  label: {
    fontSize: 13, fontWeight: '600', color: '#94a3b8',
    marginBottom: 6, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5,
  },
  input: {
    backgroundColor: '#1C2B3A', borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: '#fff',
  },
  cantidadRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  cantBtn: {
    backgroundColor: '#D4920A', width: 44, height: 44,
    borderRadius: 10, justifyContent: 'center', alignItems: 'center',
  },
  cantBtnText: { color: '#0A1017', fontSize: 22, fontWeight: '700', lineHeight: 26 },
  cantInput: {
    flex: 1, backgroundColor: '#1C2B3A', borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 10, paddingVertical: 10, fontSize: 18, fontWeight: '700', color: '#fff',
  },
  toggleRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    marginTop: 20, paddingVertical: 12, paddingHorizontal: 14,
    backgroundColor: '#1C2B3A', borderRadius: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)',
  },
  toggleLabel: { fontSize: 15, color: '#fff', fontWeight: '600' },
  botonesRow: { flexDirection: 'row', gap: 10, marginTop: 4 },
  btnFoto: {
    flex: 1, backgroundColor: '#1C2B3A', borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)', borderRadius: 10, paddingVertical: 12,
    alignItems: 'center', flexDirection: 'row', justifyContent: 'center',
  },
  btnFotoText: { fontSize: 14, fontWeight: '600', color: '#D4920A' },
  previewContainer: { marginTop: 10, borderRadius: 10, minHeight: 200 },
  preview: { width: '100%', height: 200, borderRadius: 10 },
  removeBtn: { backgroundColor: '#C0392B', padding: 8, alignItems: 'center' },
  removeBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  placeholder: {
    marginTop: 10, height: 80, backgroundColor: '#1C2B3A',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)', borderRadius: 10,
    justifyContent: 'center', alignItems: 'center', borderStyle: 'dashed',
  },
  placeholderText: { color: '#94a3b8', fontSize: 13 },
  pickerWrapper: {
    backgroundColor: '#1C2B3A', borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 10, overflow: 'hidden',
  },
  picker: { color: '#fff', height: 50 },
  btn: {
    backgroundColor: '#D4920A', borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginTop: 28,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#0A1017', fontWeight: '700', fontSize: 16 },
  cancelBtn: { paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  cancelText: { color: '#94a3b8', fontSize: 15 },
});
