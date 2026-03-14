import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ScrollView, ActivityIndicator, Alert,
  KeyboardAvoidingView, Platform, Wrap,
} from 'react-native';
import { api } from '../api';
import { colors } from '../theme';

const PROCESOS_RAPIDOS = [
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
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [mecanico, setMecanico] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGuardar = async () => {
    if (!nombre.trim()) {
      Alert.alert('Campo requerido', 'El nombre del proceso es obligatorio');
      return;
    }
    setLoading(true);
    try {
      await api.createProceso(ticketId, {
        nombre: nombre.trim(),
        descripcion: descripcion.trim() || null,
        mecanico: mecanico.trim() || null,
      });
      navigation.goBack();
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.form}>

          {/* Chips de procesos rápidos */}
          <Text style={styles.label}>Procesos frecuentes</Text>
          <View style={styles.chipsContainer}>
            {PROCESOS_RAPIDOS.map((p) => (
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

          <Text style={styles.label}>Mecánico responsable</Text>
          <TextInput
            style={styles.input}
            placeholder="Nombre del mecánico"
            placeholderTextColor={colors.textMuted}
            value={mecanico}
            onChangeText={setMecanico}
          />

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
      </ScrollView>
    </KeyboardAvoidingView>
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
});
