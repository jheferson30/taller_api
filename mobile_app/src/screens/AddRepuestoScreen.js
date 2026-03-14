import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ScrollView, ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { api } from '../api';
import { colors } from '../theme';

export default function AddRepuestoScreen({ route, navigation }) {
  const { ticketId } = route.params;
  const [nombre, setNombre] = useState('');
  const [cantidad, setCantidad] = useState('1');
  const [marcaReferencia, setMarcaReferencia] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGuardar = async () => {
    if (!nombre.trim()) {
      Alert.alert('Campo requerido', 'El nombre del repuesto es obligatorio');
      return;
    }

    const cantidadNum = parseInt(cantidad, 10);
    if (isNaN(cantidadNum) || cantidadNum < 1) {
      Alert.alert('Cantidad inválida', 'La cantidad debe ser un número mayor a 0');
      return;
    }

    setLoading(true);
    try {
      await api.createRepuesto(ticketId, {
        nombre: nombre.trim(),
        cantidad: cantidadNum,
        marca_referencia: marcaReferencia.trim() || null,
      });
      navigation.goBack();
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setLoading(false);
    }
  };

  const ajustarCantidad = (delta) => {
    const actual = parseInt(cantidad, 10) || 1;
    const nuevo = Math.max(1, actual + delta);
    setCantidad(String(nuevo));
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
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

          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleGuardar}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>Guardar Repuesto</Text>
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
  cantidadRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  cantBtn: {
    backgroundColor: colors.primary,
    width: 44,
    height: 44,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cantBtnText: { color: '#fff', fontSize: 22, fontWeight: '700', lineHeight: 26 },
  cantInput: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingVertical: 10,
    fontSize: 18,
    fontWeight: '700',
    color: colors.text,
  },
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
