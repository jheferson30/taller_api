import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator,
  Image,
} from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import * as ImagePicker from 'expo-image-picker';
import { Picker } from '@react-native-picker/picker';
import { api } from '../api';
import { colors } from '../theme';
import { useToast } from '../components/Toast';

const PROCESOS_RAPIDOS_DEFAULT = [
  'Cambio de aceite',
  'Mantenimiento de frenos',
  'Cambio de cunas de diracion',
  'Mantenimiento de suspensión',
  'Cambio de kit de arrastre',
  'Cambio de refrigerante',
  'Cambio de líquido de frenos',
  'Mantenimiento preventivo',
  'Mantenimiento correctivo',
  'Mantenimiento general',
];

export default function AddProcesoScreen({ route, navigation }) {
  const { ticketId } = route.params;
  const toast = useToast();
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [mecanico, setMecanico] = useState('');
  const [fotoUri, setFotoUri] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mecanicos, setMecanicos] = useState([]);
  const [procesosRapidos, setProcesosRapidos] = useState(PROCESOS_RAPIDOS_DEFAULT);

  useEffect(() => {
    api.getMecanicos().then((data) => setMecanicos(data)).catch(() => {});
    api.getProcesosRapidos().then((data) => {
      if (data.procesos && data.procesos.length > 0) setProcesosRapidos(data.procesos);
    }).catch(() => {});
  }, []);

  const tomarFoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') { toast('Necesitamos acceso a la camara', 'warning'); return; }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled) setFotoUri(result.assets[0].uri);
  };

  const seleccionarFoto = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') { toast('Necesitamos acceso a la galeria', 'warning'); return; }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.8 });
    if (!result.canceled) setFotoUri(result.assets[0].uri);
  };

  const handleGuardar = async () => {
    if (!nombre.trim()) {
      toast('El nombre del proceso es obligatorio', 'warning');
      return;
    }
    setLoading(true);
    try {
      let foto_url = null;
      if (fotoUri) {
        const uploadResult = await api.subirArchivoFoto(fotoUri);
        foto_url = uploadResult.url;
      }
      await api.createProcesoJson(ticketId, {
        nombre: nombre.trim(),
        descripcion: descripcion.trim() || null,
        mecanico: mecanico.trim() || null,
        foto_url,
      });
      navigation.goBack();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAwareScrollView
      style={styles.container}
      keyboardShouldPersistTaps="handled"
      enableOnAndroid={true}
      extraScrollHeight={20}
    >
      <View style={styles.form}>

          {/* Chips de procesos rápidos */}
          <Text style={styles.label}>Procesos frecuentes</Text>
          <View style={styles.chipsContainer}>
            {procesosRapidos.map((p) => (
              <TouchableOpacity
                key={p}
                style={[styles.chip, nombre === p && styles.chipActive]}
                onPress={() => setNombre(p)}
              >
                <Text style={[styles.chipText, nombre === p && styles.chipTextActive]}>{p}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.label}>Nombre del proceso *</Text>
          <TextInput
            style={styles.input}
            placeholder="Ej: Cambio de aceite"
            placeholderTextColor={colors.textMuted}
            value={nombre}
            onChangeText={setNombre}
          />

          <Text style={styles.label}>📷 Foto (opcional)</Text>
          <View style={styles.botonesRow}>
            <TouchableOpacity style={styles.btnFoto} onPress={tomarFoto}>
              <Text style={styles.btnFotoText}>📷 Cámara</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnFoto} onPress={seleccionarFoto}>
              <Text style={styles.btnFotoText}>🖼 Galería</Text>
            </TouchableOpacity>
          </View>
          {fotoUri && (
            <View style={styles.previewContainer}>
              <Image source={{ uri: fotoUri }} style={styles.preview} resizeMode="cover" />
              <TouchableOpacity style={styles.removeBtn} onPress={() => setFotoUri(null)}>
                <Text style={styles.removeBtnText}>✕ Quitar</Text>
              </TouchableOpacity>
            </View>
          )}

          <Text style={styles.label}>Mecánico responsable</Text>
          {mecanicos.length > 0 ? (
            <View style={styles.pickerWrapper}>
              <Picker
                selectedValue={mecanico}
                onValueChange={(v) => setMecanico(v)}
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
              placeholder="Nombre del mecánico"
              placeholderTextColor={colors.textMuted}
              value={mecanico}
              onChangeText={setMecanico}
            />
          )}

          <Text style={styles.label}>Descripción</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="Detalles del proceso realizado..."
            placeholderTextColor={colors.textMuted}
            value={descripcion}
            onChangeText={setDescripcion}
            multiline
            numberOfLines={4}
            textAlignVertical="top"
          />

          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleGuardar}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>Guardar Proceso</Text>
            }
          </TouchableOpacity>

          <TouchableOpacity style={styles.cancelBtn} onPress={() => navigation.goBack()}>
            <Text style={styles.cancelText}>Cancelar</Text>
          </TouchableOpacity>
        </View>
    </KeyboardAwareScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  form: { padding: 20 },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textMuted,
    marginBottom: 6,
    marginTop: 16,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  chipsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 4,
  },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: colors.surface,
  },
  chipActive: {
    borderColor: colors.primary,
    backgroundColor: colors.primary,
  },
  chipText: { fontSize: 13, color: colors.text },
  chipTextActive: { color: '#fff', fontWeight: '600' },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.text,
  },
  textArea: { height: 100, paddingTop: 12 },
  btn: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 28,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  cancelBtn: { paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  cancelText: { color: colors.textMuted, fontSize: 15 },
  botonesRow: { flexDirection: 'row', gap: 10, marginBottom: 8 },
  btnFoto: {
    flex: 1, backgroundColor: colors.surface, borderWidth: 1,
    borderColor: colors.border, borderRadius: 10, paddingVertical: 12, alignItems: 'center',
  },
  btnFotoText: { fontSize: 14, fontWeight: '600', color: colors.primary },
  previewContainer: { borderRadius: 12, overflow: 'hidden', marginBottom: 8 },
  preview: { width: '100%', height: 180 },
  removeBtn: { backgroundColor: colors.error, padding: 8, alignItems: 'center' },
  removeBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  pickerWrapper: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    overflow: 'hidden',
  },
  picker: { color: colors.text, height: 50 },
});
