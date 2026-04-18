import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, Image,
} from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../api';
import { colors } from '../theme';
import { useToast } from '../components/Toast';
import { useOffline } from '../hooks/useOffline';
import offlineService from '../services/offlineService';

const TIPOS = ['ANTES', 'DESPUES', 'OTRA'];

export default function AddFotoScreen({ route, navigation }) {
  const { ticketId } = route.params;
  const toast = useToast();
  const { isOnline } = useOffline();
  const [uri, setUri] = useState(null);
  const [descripcion, setDescripcion] = useState('');
  const [tipo, setTipo] = useState('OTRA');
  const [loading, setLoading] = useState(false);

  const seleccionarFoto = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      toast('Necesitamos acceso a tu galeria para subir fotos', 'warning');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });
    if (!result.canceled) {
      setUri(result.assets[0].uri);
    }
  };

  const tomarFoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      toast('Necesitamos acceso a la camara', 'warning');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled) {
      setUri(result.assets[0].uri);
    }
  };

  const handleGuardar = async () => {
    if (!uri) {
      toast('Selecciona o toma una foto primero', 'warning');
      return;
    }
    setLoading(true);
    try {
      if (!isOnline) {
        await offlineService.enqueueOperation({
          type: 'CREATE_FOTO',
          endpoint: `/tickets/${ticketId}/fotos`,
          method: 'POST',
          data: { ticketId, fotoUri: uri, descripcion: descripcion.trim() || null, tipo },
        });
        toast('Sin conexión — se subirá automáticamente cuando vuelva el internet', 'warning');
        navigation.goBack();
        return;
      }
      await api.subirFoto(ticketId, uri, descripcion.trim() || null, tipo);
      navigation.goBack();
    } catch (e) {
      const msg = e.message?.toLowerCase().includes('network')
        ? 'Error de red al subir la foto. Verifica tu conexión WiFi e intenta de nuevo.'
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
      enableOnAndroid={true}
      extraScrollHeight={20}
    >
      <View style={styles.form}>

          {/* Tipo de foto */}
          <Text style={styles.label}>Tipo de foto</Text>
          <View style={styles.tiposRow}>
            {TIPOS.map((t) => (
              <TouchableOpacity
                key={t}
                style={[styles.tipoBtn, tipo === t && styles.tipoBtnActive]}
                onPress={() => setTipo(t)}
              >
                <Text style={[styles.tipoBtnText, tipo === t && styles.tipoBtnTextActive]}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Botones de selección */}
          <View style={styles.botonesRow}>
            <TouchableOpacity style={styles.btnFoto} onPress={tomarFoto}>
              <Ionicons name="camera-outline" size={18} color={colors.primary} style={{marginRight: 6}} />
              <Text style={styles.btnFotoText}>Cámara</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnFoto} onPress={seleccionarFoto}>
              <Ionicons name="images-outline" size={18} color={colors.primary} style={{marginRight: 6}} />
              <Text style={styles.btnFotoText}>Galería</Text>
            </TouchableOpacity>
          </View>

          {/* Preview */}
          {uri && (
            <View style={styles.previewContainer}>
              <Image source={{ uri }} style={styles.preview} resizeMode="cover" />
              <TouchableOpacity style={styles.removeBtn} onPress={() => setUri(null)}>
                <Text style={styles.removeBtnText}>✕ Quitar</Text>
              </TouchableOpacity>
            </View>
          )}

          {!uri && (
            <View style={styles.placeholder}>
              <Text style={styles.placeholderText}>Sin foto seleccionada</Text>
            </View>
          )}

          <Text style={styles.label}>Descripción</Text>
          <TextInput
            style={styles.input}
            placeholder="Ej: Daño en el motor antes de reparar..."
            placeholderTextColor={colors.textMuted}
            value={descripcion}
            onChangeText={setDescripcion}
          />

          <TouchableOpacity
            style={[styles.btn, (!uri || loading) && styles.btnDisabled]}
            onPress={handleGuardar}
            disabled={!uri || loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>Guardar Foto</Text>
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
  container: { flex: 1, backgroundColor: '#0A1017' },
  form: { padding: 20 },
  label: {
    fontSize: 13, fontWeight: '600', color: '#94a3b8',
    marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5,
  },
  tiposRow: { flexDirection: 'row', gap: 10 },
  tipoBtn: {
    flex: 1, borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 10, paddingVertical: 10, alignItems: 'center',
    backgroundColor: '#1C2B3A',
  },
  tipoBtnActive: { borderColor: '#D4920A', backgroundColor: '#D4920A' },
  tipoBtnText: { fontSize: 13, fontWeight: '600', color: '#fff' },
  tipoBtnTextActive: { color: '#0A1017' },
  botonesRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  btnFoto: {
    flex: 1, backgroundColor: '#1C2B3A', borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)', borderRadius: 10, paddingVertical: 14,
    alignItems: 'center', flexDirection: 'row', justifyContent: 'center',
  },
  btnFotoText: { fontSize: 15, fontWeight: '600', color: '#D4920A' },
  previewContainer: { marginTop: 12, borderRadius: 12, overflow: 'hidden' },
  preview: { width: '100%', height: 220 },
  removeBtn: { backgroundColor: '#C0392B', padding: 8, alignItems: 'center' },
  removeBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  placeholder: {
    marginTop: 12, height: 120, backgroundColor: '#1C2B3A',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)', borderRadius: 12,
    justifyContent: 'center', alignItems: 'center', borderStyle: 'dashed',
  },
  placeholderText: { color: '#94a3b8', fontSize: 14 },
  input: {
    backgroundColor: '#1C2B3A', borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: '#fff',
  },
  btn: {
    backgroundColor: '#D4920A', borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginTop: 28,
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#0A1017', fontWeight: '700', fontSize: 16 },
  cancelBtn: { paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  cancelText: { color: '#94a3b8', fontSize: 15 },
});
