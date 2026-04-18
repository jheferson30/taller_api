import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, Image,
} from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import * as ImagePicker from 'expo-image-picker';
import { Picker } from '@react-native-picker/picker';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme';
import { api } from '../api';
import { useToast } from '../components/Toast';

export default function AddCompraScreen({ route, navigation }) {
  const { ticketId } = route.params;
  const toast = useToast();
  const [descripcion, setDescripcion] = useState('');
  const [valor, setValor] = useState('');
  const [responsable, setResponsable] = useState('');
  const [nota, setNota] = useState('');
  const [uri, setUri] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mecanicos, setMecanicos] = useState([]);

  useEffect(() => {
    api.getMecanicos().then((data) => setMecanicos(data)).catch(() => {});
  }, []);

  const seleccionarSoporte = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      toast('Necesitamos acceso a tu galeria', 'warning');
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
      toast('Necesitamos acceso a la camara', 'warning');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled) setUri(result.assets[0].uri);
  };

  const handleGuardar = async () => {
    if (!descripcion.trim()) {
      toast('La descripcion es obligatoria', 'warning');
      return;
    }
    const valorNum = parseInt(valor, 10);
    if (isNaN(valorNum) || valorNum <= 0) {
      toast('Ingresa un valor mayor a 0', 'warning');
      return;
    }
    setLoading(true);
    try {
      await api.createCompra(ticketId, {
        descripcion: descripcion.trim(),
        valor: valorNum,
        responsable: responsable.trim() || null,
        nota: nota.trim() || null,
      }, uri);
      navigation.goBack();
    } catch (e) {
      const msg = e.message?.toLowerCase().includes('network')
        ? uri
          ? 'Error de red al subir el soporte. Verifica tu conexión WiFi e intenta de nuevo, o quita la foto.'
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
      enableOnAndroid={true}
      extraScrollHeight={20}
    >
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
            value={valor ? Number(valor).toLocaleString('es-CO') : ''}
            onChangeText={(t) => {
              const raw = t.replace(/\D/g, '');
              setValor(raw);
            }}
            keyboardType="numeric"
            selection={undefined}
          />

          <Text style={styles.label}>Responsable</Text>
          {mecanicos.length > 0 ? (
            <View style={styles.pickerWrapper}>
              <Picker
                selectedValue={responsable}
                onValueChange={(v) => setResponsable(v)}
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
              <Ionicons name="camera-outline" size={18} color={colors.primary} style={{marginRight: 6}} />
              <Text style={styles.btnFotoText}>Cámara</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnFoto} onPress={seleccionarSoporte}>
              <Ionicons name="images-outline" size={18} color={colors.primary} style={{marginRight: 6}} />
              <Text style={styles.btnFotoText}>Galería</Text>
            </TouchableOpacity>
          </View>

          {uri ? (
            <View style={styles.previewContainer}>
              <Image source={{ uri }} style={styles.preview} resizeMode="cover" />
              <TouchableOpacity style={styles.removeBtn} onPress={() => setUri(null)}>
                <Text style={styles.removeBtnText}>Quitar</Text>
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
    </KeyboardAwareScrollView>
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
    borderColor: colors.border, borderRadius: 10, paddingVertical: 12,
    alignItems: 'center', flexDirection: 'row', justifyContent: 'center',
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
  pickerWrapper: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    overflow: 'hidden',
  },
  picker: { color: colors.text, height: 50 },
});
