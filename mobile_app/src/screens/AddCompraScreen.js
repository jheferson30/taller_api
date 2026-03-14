import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, Alert, Image,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { colors } from '../theme';

const API_BASE_URL = 'http://10.0.2.2:8000/api/mobile';

export default function AddCompraScreen({ route, navigation }) {
  const { ticketId } = route.params;
  const [descripcion, setDescripcion] = useState('');
  const [valor, setValor] = useState('');
  const [responsable, setResponsable] = useState('');
  const [nota, setNota] = useState('');
  const [uri, setUri] = useState(null);
  const [loading, setLoading] = useState(false);

  const seleccionarSoporte = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permiso requerido', 'Necesitamos acceso a tu galería');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });
    if (!result.canceled) setUri(result.assets[0].uri);
  };

  const tomarFoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permiso requerido', 'Necesitamos acceso a la cámara');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled) setUri(result.assets[0].uri);
  };

  const handleGuardar = async () => {
    if (!descripcion.trim()) {
      Alert.alert('Campo requerido', 'La descripción es obligatoria');
      return;
    }
    const valorNum = parseInt(valor, 10);
    if (isNaN(valorNum) || valorNum <= 0) {
      Alert.alert('Valor inválido', 'Ingresa un valor mayor a 0');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('descripcion', descripcion.trim());
      formData.append('valor', String(valorNum));
      if (responsable.trim()) formData.append('responsable', responsable.trim());
      if (nota.trim()) formData.append('nota', nota.trim());
      if (uri) {
        const filename = uri.split('/').pop();
        const ext = filename.split('.').pop().toLowerCase();
        const type = ext === 'png' ? 'image/png' : 'image/jpeg';
        formData.append('file', { uri, name: filename, type });
      }

      const response = await fetch(`${API_BASE_URL}/tickets/${ticketId}/compras`, {
        method: 'POST',
        body: formData,
        headers: { 'X-Admin-Password': 'la_pulga_fi' },
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${response.status}`);
      }
      navigation.goBack();
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.form}>

          <Text style={styles.label}>Descripción *</Text>
          <TextInput
            style={styles.input}
            placeholder="Ej: Pastillas de freno"
            placeholderTextColor={colors.textMuted}
            value={descripcion}
            onChangeText={setDescripcion}
            autoFocus
          />

          <Text style={styles.label}>Valor *</Text>
          <TextInput
            style={styles.input}
            placeholder="0"
            placeholderTextColor={colors.textMuted}
            value={valor}
            onChangeText={(t) => setValor(t.replace(/[^0-9]/g, ''))}
            keyboardType="numeric"
          />

          <Text style={styles.label}>Responsable</Text>
          <TextInput
            style={styles.input}
            placeholder="Nombre del responsable"
            placeholderTextColor={colors.textMuted}
            value={responsable}
            onChangeText={setResponsable}
          />

          <Text style={styles.label}>Nota</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="Notas adicionales..."
            placeholderTextColor={colors.textMuted}
            value={nota}
            onChangeText={setNota}
            multiline
            numberOfLines={3}
            textAlignVertical="top"
          />

          <Text style={styles.label}>Soporte (Factura/Recibo)</Text>
          <View style={styles.botonesRow}>
            <TouchableOpacity style={styles.btnFoto} onPress={tomarFoto}>
              <Text style={styles.btnFotoText}>📷 Cámara</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnFoto} onPress={seleccionarSoporte}>
              <Text style={styles.btnFotoText}>🖼 Galería</Text>
            </TouchableOpacity>
          </View>

          {uri ? (
            <View style={styles.previewContainer}>
              <Image source={{ uri }} style={styles.preview} resizeMode="cover" />
              <TouchableOpacity style={styles.removeBtn} onPress={() => setUri(null)}>
                <Text style={styles.removeBtnText}>✕ Quitar</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.placeholder}>
              <Text style={styles.placeholderText}>Sin soporte adjunto (opcional)</Text>
            </View>
          )}

          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleGuardar}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>Registrar Compra</Text>
            }
          </TouchableOpacity>

          <TouchableOpacity style={styles.cancelBtn} onPress={() => navigation.goBack()}>
            <Text style={styles.cancelText}>Cancelar</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  form: { padding: 20 },
  label: {
    fontSize: 13, fontWeight: '600', color: colors.textMuted,
    marginBottom: 6, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5,
  },
  input: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: colors.text,
  },
  textArea: { height: 90, paddingTop: 12 },
  botonesRow: { flexDirection: 'row', gap: 10, marginTop: 4 },
  btnFoto: {
    flex: 1, backgroundColor: colors.surface, borderWidth: 1,
    borderColor: colors.border, borderRadius: 10, paddingVertical: 12, alignItems: 'center',
  },
  btnFotoText: { fontSize: 14, fontWeight: '600', color: colors.primary },
  previewContainer: { marginTop: 10, borderRadius: 10, overflow: 'hidden' },
  preview: { width: '100%', height: 180 },
  removeBtn: { backgroundColor: colors.error, padding: 8, alignItems: 'center' },
  removeBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  placeholder: {
    marginTop: 10, height: 80, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.border, borderRadius: 10,
    justifyContent: 'center', alignItems: 'center', borderStyle: 'dashed',
  },
  placeholderText: { color: colors.textMuted, fontSize: 13 },
  btn: {
    backgroundColor: colors.primary, borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginTop: 28,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  cancelBtn: { paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  cancelText: { color: colors.textMuted, fontSize: 15 },
});
