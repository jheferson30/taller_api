import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator,
} from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import { Picker } from '@react-native-picker/picker';
import { colors } from '../theme';
import { api } from '../api';
import { useToast } from '../components/Toast';

const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'TRANSFERENCIA', 'TARJETA'];

export default function CobroRapidoScreen({ route, navigation }) {
  const { placa: placaInicial = '' } = route.params || {};
  const toast = useToast();

  const [placa, setPlaca] = useState(placaInicial.toUpperCase());
  const [descripcion, setDescripcion] = useState('');
  const [valor, setValor] = useState('');
  const [metodo, setMetodo] = useState('EFECTIVO');
  const [loading, setLoading] = useState(false);

  const handleRegistrar = async () => {
    if (!placa.trim()) { toast('La placa es obligatoria', 'warning'); return; }
    if (!descripcion.trim()) { toast('La descripción es obligatoria', 'warning'); return; }
    const valorNum = parseInt(valor, 10);
    if (isNaN(valorNum) || valorNum <= 0) { toast('Ingresa un valor mayor a 0', 'warning'); return; }

    setLoading(true);
    try {
      await api.cobroRapido({
        placa: placa.trim().toUpperCase(),
        descripcion: descripcion.trim(),
        valor: valorNum,
        metodo_pago: metodo,
      });
      toast('Cobro registrado', 'success');
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
      enableOnAndroid
      extraScrollHeight={20}
    >
      <View style={styles.form}>
        <Text style={styles.label}>Placa *</Text>
        <TextInput
          style={styles.input}
          placeholder="Ej: ABC123"
          placeholderTextColor={colors.textMuted}
          value={placa}
          onChangeText={(t) => setPlaca(t.toUpperCase())}
          autoCapitalize="characters"
          autoFocus={!placaInicial}
        />

        <Text style={styles.label}>Descripción *</Text>
        <TextInput
          style={styles.input}
          placeholder="Ej: Cambio de aceite, diagnóstico..."
          placeholderTextColor={colors.textMuted}
          value={descripcion}
          onChangeText={setDescripcion}
          autoFocus={!!placaInicial}
        />

        <Text style={styles.label}>Valor *</Text>
        <TextInput
          style={styles.input}
          placeholder="0"
          placeholderTextColor={colors.textMuted}
          value={valor ? Number(valor).toLocaleString('es-CO') : ''}
          onChangeText={(t) => setValor(t.replace(/\D/g, ''))}
          keyboardType="numeric"
        />

        <Text style={styles.label}>Método de Pago</Text>
        <View style={styles.pickerWrapper}>
          <Picker
            selectedValue={metodo}
            onValueChange={setMetodo}
            style={styles.picker}
            dropdownIconColor={colors.textMuted}
          >
            {METODOS.map((m) => (
              <Picker.Item key={m} label={m.charAt(0) + m.slice(1).toLowerCase()} value={m} />
            ))}
          </Picker>
        </View>

        <TouchableOpacity
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={handleRegistrar}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.btnText}>⚡ Registrar Cobro</Text>
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
  pickerWrapper: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: 10, overflow: 'hidden',
  },
  picker: { color: colors.text, height: 50 },
  btn: {
    backgroundColor: colors.primary, borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginTop: 28,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  cancelBtn: { paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  cancelText: { color: colors.textMuted, fontSize: 15 },
});
