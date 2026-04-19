import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, ScrollView, Alert,
} from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import { Picker } from '@react-native-picker/picker';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../api';
import { colors, estadoConfig } from '../theme';
import { useToast } from '../components/Toast';

const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'TRANSFERENCIA', 'TARJETA'];

const emptyVehiculo = {
  placa: '',
  marca: '',
  modelo: '',
  anio: new Date().getFullYear(),
  cilindraje: '',
  color: '',
  nombre_propietario: '',
  telefono_propietario: '',
};

const emptyTicket = {
  motivo_visita: '',
  observaciones_recepcion: '',
  kilometraje: '',
  estado_inicial: '',
  anticipo_recibido: '',
  metodo_pago_anticipo: 'EFECTIVO',
  recepcionado_por: '',
};

// ── Sección con título ────────────────────────────────────────────────────────
function Seccion({ titulo, children }) {
  return (
    <View style={s.seccion}>
      <Text style={s.seccionTitulo}>{titulo}</Text>
      {children}
    </View>
  );
}

// ── Campo de formulario ───────────────────────────────────────────────────────
function Campo({ label, children }) {
  return (
    <View style={s.campo}>
      <Text style={s.campoLabel}>{label}</Text>
      {children}
    </View>
  );
}

// ── Input estilizado ──────────────────────────────────────────────────────────
function Input({ value, onChangeText, placeholder, keyboardType, multiline, editable = true, autoFocus }) {
  return (
    <TextInput
      style={[s.input, multiline && s.inputMulti, !editable && s.inputDisabled]}
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor={colors.textMuted}
      keyboardType={keyboardType}
      multiline={multiline}
      numberOfLines={multiline ? 3 : 1}
      textAlignVertical={multiline ? 'top' : 'center'}
      editable={editable}
      autoFocus={autoFocus}
    />
  );
}

// ── Historial de visitas ──────────────────────────────────────────────────────
function HistorialVisitas({ historial }) {
  if (!historial || historial.length === 0) return null;
  return (
    <View style={s.historialContainer}>
      <Text style={s.historialTitulo}>Historial de visitas ({historial.length})</Text>
      {historial.slice(0, 5).map((h, i) => {
        const cfg = estadoConfig[h.estado] || estadoConfig.ABIERTO;
        const fecha = h.fecha_ingreso
          ? new Date(h.fecha_ingreso).toLocaleDateString('es-CO')
          : '—';
        return (
          <View key={i} style={s.historialItem}>
            <View style={s.historialRow}>
              <Text style={s.historialCodigo}>{h.ticket_codigo}</Text>
              <View style={[s.historialBadge, { backgroundColor: cfg.bg }]}>
                <Text style={[s.historialBadgeText, { color: cfg.text }]}>{cfg.label}</Text>
              </View>
            </View>
            <Text style={s.historialMotivo}>{h.motivo_visita}</Text>
            <Text style={s.historialFecha}>{fecha}</Text>
          </View>
        );
      })}
    </View>
  );
}

// ── Formulario del ticket ─────────────────────────────────────────────────────
function FormTicket({ ticket, setTicket, mecanicos }) {
  return (
    <Seccion titulo="Nuevo Ticket de Ingreso">
      <Campo label="¿Por qué viene el cliente? *">
        <Input
          value={ticket.motivo_visita}
          onChangeText={(v) => setTicket({ ...ticket, motivo_visita: v })}
          placeholder="Ej: Cambio de aceite y revisión de frenos"
          autoFocus
        />
      </Campo>
      <Campo label="Observaciones del cliente">
        <Input
          value={ticket.observaciones_recepcion}
          onChangeText={(v) => setTicket({ ...ticket, observaciones_recepcion: v })}
          placeholder="Ej: Ruido en el freno delantero..."
          multiline
        />
      </Campo>
      <View style={s.fila}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <Campo label="Kilometraje">
            <Input
              value={ticket.kilometraje}
              onChangeText={(v) => setTicket({ ...ticket, kilometraje: v.replace(/\D/g, '') })}
              placeholder="Ej: 15000"
              keyboardType="numeric"
            />
          </Campo>
        </View>
        <View style={{ flex: 1 }}>
          <Campo label="Estado inicial">
            <Input
              value={ticket.estado_inicial}
              onChangeText={(v) => setTicket({ ...ticket, estado_inicial: v })}
              placeholder="Ej: Freno blando"
            />
          </Campo>
        </View>
      </View>
      <View style={s.fila}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <Campo label="Anticipo recibido">
            <Input
              value={ticket.anticipo_recibido ? Number(ticket.anticipo_recibido).toLocaleString('es-CO') : ''}
              onChangeText={(v) => setTicket({ ...ticket, anticipo_recibido: v.replace(/\D/g, '') })}
              placeholder="0"
              keyboardType="numeric"
            />
          </Campo>
        </View>
        <View style={{ flex: 1 }}>
          <Campo label="Método de pago">
            <View style={s.pickerWrapper}>
              <Picker
                selectedValue={ticket.metodo_pago_anticipo}
                onValueChange={(v) => setTicket({ ...ticket, metodo_pago_anticipo: v })}
                style={s.picker}
                dropdownIconColor={colors.textMuted}
              >
                {METODOS.map((m) => (
                  <Picker.Item key={m} label={m.charAt(0) + m.slice(1).toLowerCase()} value={m} />
                ))}
              </Picker>
            </View>
          </Campo>
        </View>
      </View>
      <Campo label="Recepcionado por">
        {mecanicos.length > 0 ? (
          <View style={s.pickerWrapper}>
            <Picker
              selectedValue={ticket.recepcionado_por}
              onValueChange={(v) => setTicket({ ...ticket, recepcionado_por: v })}
              style={s.picker}
              dropdownIconColor={colors.textMuted}
            >
              <Picker.Item label="— Sin asignar —" value="" />
              {mecanicos.filter((m) => m.activo).map((m) => (
                <Picker.Item key={m.id} label={m.nombre} value={m.nombre} />
              ))}
            </Picker>
          </View>
        ) : (
          <Input
            value={ticket.recepcionado_por}
            onChangeText={(v) => setTicket({ ...ticket, recepcionado_por: v })}
            placeholder="Nombre del recepcionista"
          />
        )}
      </Campo>
    </Seccion>
  );
}

// ── Pantalla principal ────────────────────────────────────────────────────────
export default function RecepcionScreen({ navigation }) {
  const toast = useToast();
  const [step, setStep] = useState('search'); // search | new | existing
  const [placaBusqueda, setPlacaBusqueda] = useState('');
  const [buscando, setBuscando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [vehiculo, setVehiculo] = useState(emptyVehiculo);
  const [ticket, setTicket] = useState(emptyTicket);
  const [ficha, setFicha] = useState(null);
  const [mecanicos, setMecanicos] = useState([]);
  const [esNuevo, setEsNuevo] = useState(false); // true = crear vehículo, false = solo ticket

  useEffect(() => {
    api.getMecanicos().then(setMecanicos).catch(() => {});
  }, []);

  function resetForm() {
    setStep('search');
    setPlacaBusqueda('');
    setVehiculo(emptyVehiculo);
    setTicket(emptyTicket);
    setFicha(null);
    setEsNuevo(false);
  }

  async function handleBuscar() {
    const placa = placaBusqueda.trim().toUpperCase();
    if (placa.length < 3) {
      toast('Ingresa al menos 3 caracteres', 'warning');
      return;
    }
    setBuscando(true);
    try {
      const data = await api.buscarVehiculo(placa);
      if (!data.existe) {
        setVehiculo({ ...emptyVehiculo, placa });
        setTicket(emptyTicket);
        setFicha(null);
        setEsNuevo(true);
        setStep('form');
      } else {
        const v = data.vehiculo;
        setVehiculo(v);
        setEsNuevo(false);
        // Cargar historial
        try {
          const detalle = await api.fichaVehiculo(v.placa);
          setFicha(detalle);
        } catch (_) {}
        setTicket(emptyTicket);
        setStep('form');
      }
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBuscando(false);
    }
  }

  async function handleGuardar() {
    if (!ticket.motivo_visita.trim()) {
      toast('El motivo de la visita es obligatorio', 'warning');
      return;
    }
    if (esNuevo && (!vehiculo.marca.trim() || !vehiculo.modelo.trim())) {
      toast('Marca y modelo son obligatorios para vehículos nuevos', 'warning');
      return;
    }
    setGuardando(true);
    try {
      if (esNuevo) {
        await api.crearVehiculo({
          placa: vehiculo.placa,
          marca: vehiculo.marca.trim(),
          modelo: vehiculo.modelo.trim(),
          anio: Number(vehiculo.anio) || new Date().getFullYear(),
          cilindraje: vehiculo.cilindraje.trim() || null,
          color: vehiculo.color.trim() || null,
          nombre_propietario: vehiculo.nombre_propietario.trim() || null,
          telefono_propietario: vehiculo.telefono_propietario.trim() || null,
        });
      }
      const ticketCreado = await api.crearTicketIngreso(vehiculo.placa, {
        motivo_visita: ticket.motivo_visita.trim(),
        observaciones_recepcion: ticket.observaciones_recepcion.trim() || null,
        kilometraje: ticket.kilometraje ? Number(ticket.kilometraje) : null,
        estado_inicial: ticket.estado_inicial.trim() || null,
        anticipo_recibido: Number(ticket.anticipo_recibido || 0),
        metodo_pago_anticipo: ticket.metodo_pago_anticipo,
        recepcionado_por: ticket.recepcionado_por || null,
      });
      toast('✓ Ticket creado exitosamente', 'success');
      // Navegar al detalle del ticket recién creado
      setTimeout(() => {
        resetForm();
        navigation.navigate('TicketDetail', { ticketId: ticketCreado.id });
      }, 800);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setGuardando(false);
    }
  }

  // ── PASO 1: Búsqueda ────────────────────────────────────────────────────────
  if (step === 'search') {
    return (
      <View style={s.container}>
        <View style={s.searchCard}>
          <Text style={s.searchTitle}>Ingresa la placa del vehículo</Text>
          <TextInput
            style={s.searchInput}
            placeholder="Ej: ABC123"
            placeholderTextColor={colors.textMuted}
            value={placaBusqueda}
            onChangeText={(v) => setPlacaBusqueda(v.toUpperCase())}
            autoCapitalize="characters"
            autoFocus
            onSubmitEditing={handleBuscar}
            returnKeyType="search"
          />
          <TouchableOpacity
            style={[s.searchBtn, buscando && s.btnDisabled]}
            onPress={handleBuscar}
            disabled={buscando}
          >
            {buscando
              ? <ActivityIndicator color="#0A1017" />
              : <Text style={s.searchBtnText}>Buscar Vehículo</Text>
            }
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // ── PASO 2: Formulario (nuevo o existente) ──────────────────────────────────
  return (
    <KeyboardAwareScrollView
      style={s.container}
      keyboardShouldPersistTaps="handled"
      enableOnAndroid
      extraScrollHeight={20}
    >
      {/* Header */}
      <View style={s.formHeader}>
        <TouchableOpacity onPress={resetForm} style={s.backBtn}>
          <Ionicons name="arrow-back" size={18} color={colors.primary} />
          <Text style={s.backBtnText}>Volver</Text>
        </TouchableOpacity>
        <View style={s.formHeaderInfo}>
          <Text style={s.formHeaderPlaca}>{vehiculo.placa}</Text>
          <View style={[s.formHeaderBadge, { backgroundColor: esNuevo ? '#fef3c7' : '#dcfce7' }]}>
            <Text style={[s.formHeaderBadgeText, { color: esNuevo ? '#92400e' : '#166534' }]}>
              {esNuevo ? 'Vehículo nuevo' : 'Vehículo registrado'}
            </Text>
          </View>
        </View>
      </View>

      <View style={s.formBody}>
        {/* Datos del vehículo — solo si es nuevo */}
        {esNuevo && (
          <Seccion titulo="Datos del Vehículo">
            <Campo label="Placa">
              <Input value={vehiculo.placa} editable={false} />
            </Campo>
            <View style={s.fila}>
              <View style={{ flex: 1, marginRight: 8 }}>
                <Campo label="Marca *">
                  <Input
                    value={vehiculo.marca}
                    onChangeText={(v) => setVehiculo({ ...vehiculo, marca: v })}
                    placeholder="Ej: Yamaha"
                  />
                </Campo>
              </View>
              <View style={{ flex: 1 }}>
                <Campo label="Modelo *">
                  <Input
                    value={vehiculo.modelo}
                    onChangeText={(v) => setVehiculo({ ...vehiculo, modelo: v })}
                    placeholder="Ej: FZ-16"
                  />
                </Campo>
              </View>
            </View>
            <View style={s.fila}>
              <View style={{ flex: 1, marginRight: 8 }}>
                <Campo label="Año">
                  <Input
                    value={String(vehiculo.anio)}
                    onChangeText={(v) => setVehiculo({ ...vehiculo, anio: v.replace(/\D/g, '') })}
                    placeholder="2024"
                    keyboardType="numeric"
                  />
                </Campo>
              </View>
              <View style={{ flex: 1 }}>
                <Campo label="Cilindraje">
                  <Input
                    value={vehiculo.cilindraje}
                    onChangeText={(v) => setVehiculo({ ...vehiculo, cilindraje: v })}
                    placeholder="Ej: 150cc"
                  />
                </Campo>
              </View>
            </View>
            <Campo label="Color">
              <Input
                value={vehiculo.color}
                onChangeText={(v) => setVehiculo({ ...vehiculo, color: v })}
                placeholder="Ej: Negro"
              />
            </Campo>
            <View style={s.fila}>
              <View style={{ flex: 1, marginRight: 8 }}>
                <Campo label="Propietario">
                  <Input
                    value={vehiculo.nombre_propietario}
                    onChangeText={(v) => setVehiculo({ ...vehiculo, nombre_propietario: v })}
                    placeholder="Ej: Juan Pérez"
                  />
                </Campo>
              </View>
              <View style={{ flex: 1 }}>
                <Campo label="Teléfono">
                  <Input
                    value={vehiculo.telefono_propietario}
                    onChangeText={(v) => setVehiculo({ ...vehiculo, telefono_propietario: v })}
                    placeholder="3001234567"
                    keyboardType="phone-pad"
                  />
                </Campo>
              </View>
            </View>
          </Seccion>
        )}

        {/* Info del vehículo existente */}
        {!esNuevo && (
          <Seccion titulo="Información del Vehículo">
            <View style={s.infoGrid}>
              {[
                ['Marca', vehiculo.marca],
                ['Modelo', vehiculo.modelo],
                ['Año', vehiculo.anio],
                ['Color', vehiculo.color || '—'],
                ['Propietario', vehiculo.nombre_propietario || '—'],
                ['Teléfono', vehiculo.telefono_propietario || '—'],
              ].map(([label, value]) => (
                <View key={label} style={s.infoItem}>
                  <Text style={s.infoLabel}>{label}</Text>
                  <Text style={s.infoValue}>{value}</Text>
                </View>
              ))}
            </View>
            <HistorialVisitas historial={ficha?.historial_visitas} />
          </Seccion>
        )}

        {/* Formulario del ticket */}
        <FormTicket ticket={ticket} setTicket={setTicket} mecanicos={mecanicos} />

        {/* Botones */}
        <View style={s.acciones}>
          <TouchableOpacity style={s.btnCancelar} onPress={resetForm} disabled={guardando}>
            <Text style={s.btnCancelarText}>Cancelar</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[s.btnGuardar, guardando && s.btnDisabled]}
            onPress={handleGuardar}
            disabled={guardando}
          >
            {guardando
              ? <ActivityIndicator color="#0A1017" />
              : <Text style={s.btnGuardarText}>
                  {esNuevo ? 'Crear Vehículo y Ticket' : 'Crear Ticket'}
                </Text>
            }
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAwareScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A1017' },

  // Búsqueda
  searchCard: {
    margin: 24,
    marginTop: 40,
    backgroundColor: '#1C2B3A',
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  searchTitle: { color: '#94a3b8', fontSize: 14, marginBottom: 16, textAlign: 'center' },
  searchInput: {
    backgroundColor: '#0A1017',
    borderWidth: 2,
    borderColor: colors.primary,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    textAlign: 'center',
    letterSpacing: 2,
    marginBottom: 16,
  },
  searchBtn: {
    backgroundColor: '#D4920A',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  searchBtnText: { color: '#0A1017', fontWeight: '700', fontSize: 16 },

  // Header formulario
  formHeader: {
    backgroundColor: '#0F1923',
    padding: 16,
    paddingTop: 12,
  },
  backBtn: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  backBtnText: { color: colors.primary, fontSize: 14, fontWeight: '600', marginLeft: 4 },
  formHeaderInfo: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  formHeaderPlaca: { color: '#fff', fontSize: 22, fontWeight: '800', letterSpacing: 1 },
  formHeaderBadge: { borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 },
  formHeaderBadgeText: { fontSize: 12, fontWeight: '700' },

  // Cuerpo formulario
  formBody: { padding: 16 },

  // Sección
  seccion: {
    backgroundColor: '#1C2B3A',
    borderRadius: 14,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.07)',
  },
  seccionTitulo: {
    color: colors.primary,
    fontSize: 13,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 14,
  },

  // Campo
  campo: { marginBottom: 12 },
  campoLabel: { color: '#94a3b8', fontSize: 12, fontWeight: '600', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.4 },

  // Input
  input: {
    backgroundColor: '#0F1923',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 11,
    fontSize: 15,
    color: '#fff',
  },
  inputMulti: { height: 80, paddingTop: 10 },
  inputDisabled: { opacity: 0.5 },

  // Fila
  fila: { flexDirection: 'row' },

  // Picker
  pickerWrapper: {
    backgroundColor: '#0F1923',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    borderRadius: 10,
    overflow: 'hidden',
  },
  picker: { color: '#fff', height: 48 },

  // Info vehículo existente
  infoGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  infoItem: {
    width: '47%',
    backgroundColor: '#0F1923',
    borderRadius: 10,
    padding: 10,
  },
  infoLabel: { color: '#64748b', fontSize: 11, fontWeight: '600', textTransform: 'uppercase', marginBottom: 2 },
  infoValue: { color: '#fff', fontSize: 14, fontWeight: '600' },

  // Historial
  historialContainer: { marginTop: 14 },
  historialTitulo: { color: '#94a3b8', fontSize: 12, fontWeight: '700', textTransform: 'uppercase', marginBottom: 8 },
  historialItem: {
    backgroundColor: '#0F1923',
    borderRadius: 10,
    padding: 10,
    marginBottom: 6,
  },
  historialRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  historialCodigo: { color: '#fff', fontSize: 12, fontWeight: '700' },
  historialBadge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 },
  historialBadgeText: { fontSize: 11, fontWeight: '700' },
  historialMotivo: { color: '#94a3b8', fontSize: 13 },
  historialFecha: { color: '#64748b', fontSize: 11, marginTop: 2 },

  // Botones acción
  acciones: { flexDirection: 'row', gap: 10, marginTop: 8, marginBottom: 32 },
  btnCancelar: {
    flex: 1,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  btnCancelarText: { color: '#94a3b8', fontWeight: '600', fontSize: 15 },
  btnGuardar: {
    flex: 2,
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  btnGuardarText: { color: '#0A1017', fontWeight: '700', fontSize: 15 },
  btnDisabled: { opacity: 0.5 },
});
