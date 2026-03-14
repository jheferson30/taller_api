import React, { useState, useCallback, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator, Alert, Image, TextInput, Linking, Share,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api';
import { colors, estadoConfig } from '../theme';

const ESTADOS_SIGUIENTES = {
  ABIERTO: 'EN_PROCESO',
  EN_PROCESO: 'FINALIZADO',
  FINALIZADO: 'ENTREGADO',
};

const LABELS_SIGUIENTE = {
  ABIERTO: '▶ Iniciar Proceso',
  EN_PROCESO: '✓ Marcar Finalizado',
  FINALIZADO: '📦 Marcar Entregado',
};

export default function TicketDetailScreen({ route, navigation }) {
  const { ticketId } = route.params;
  const [ticket, setTicket] = useState(null);
  const [resumen, setResumen] = useState(null);
  const [procesos, setProcesos] = useState([]);
  const [repuestos, setRepuestos] = useState([]);
  const [fotos, setFotos] = useState([]);
  const [compras, setCompras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tab, setTab] = useState('info');
  const [updatingEstado, setUpdatingEstado] = useState(false);

  const loadData = async () => {
    try {
      const [t, r, p, rep, f, c] = await Promise.all([
        api.getTicket(ticketId),
        api.getResumen(ticketId),
        api.getProcesos(ticketId),
        api.getRepuestos(ticketId),
        api.getFotos(ticketId),
        api.getCompras(ticketId),
      ]);
      setTicket(t);
      setResumen(r);
      setProcesos(p);
      setRepuestos(rep);
      setFotos(f);
      setCompras(c);} catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { loadData(); }, [ticketId]));

  const handleCambiarEstado = () => {
    const siguiente = ESTADOS_SIGUIENTES[ticket.estado];
    if (!siguiente) return;
    const cfg = estadoConfig[siguiente];
    Alert.alert(
      'Cambiar Estado',
      `¿Cambiar a "${cfg.label}"?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Confirmar',
          onPress: async () => {
            setUpdatingEstado(true);
            try {
              await api.updateEstado(ticketId, siguiente);
              await loadData();
            } catch (e) {
              Alert.alert('Error', e.message);
            } finally {
              setUpdatingEstado(false);
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!ticket) return null;

  const cfg = estadoConfig[ticket.estado] || estadoConfig.ABIERTO;
  const siguienteEstado = ESTADOS_SIGUIENTES[ticket.estado];
  const fecha = new Date(ticket.fecha_ingreso).toLocaleString('es-CO');
  const editable = ['ABIERTO', 'EN_PROCESO'].includes(ticket.estado);
  const isFinalizado = ticket.estado === 'FINALIZADO';

  const TABS = [
    { key: 'info', label: 'Info' },
    { key: 'procesos', label: `Procesos (${resumen?.contadores?.procesos ?? 0})` },
    { key: 'repuestos', label: `Repuestos (${resumen?.contadores?.repuestos ?? 0})` },
    { key: 'fotos', label: `Fotos (${resumen?.contadores?.fotos ?? 0})` },
    { key: 'compras', label: `Compras (${resumen?.contadores?.compras ?? 0})` },
    { key: 'finanzas', label: 'Finanzas' },
    ...(isFinalizado ? [{ key: 'entrega', label: '📦 Entrega' }] : []),
  ];

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.ticketHeader}>
        <View style={styles.headerRow}>
          <Text style={styles.placa}>{ticket.placa}</Text>
          <View style={[styles.badge, { backgroundColor: cfg.bg }]}>
            <Text style={[styles.badgeText, { color: cfg.text }]}>{cfg.label}</Text>
          </View>
        </View>
        <Text style={styles.codigo}>{ticket.ticket_codigo}</Text>
        {siguienteEstado && (
          <TouchableOpacity
            style={[styles.estadoBtn, updatingEstado && styles.estadoBtnDisabled]}
            onPress={handleCambiarEstado}
            disabled={updatingEstado}
          >
            {updatingEstado
              ? <ActivityIndicator color="#fff" size="small" />
              : <Text style={styles.estadoBtnText}>{LABELS_SIGUIENTE[ticket.estado]}</Text>
            }
          </TouchableOpacity>
        )}
      </View>

      {/* Tabs - dos filas FIJAS */}
      <View style={styles.tabsContainer}>
        <View style={styles.tabs}>
          {TABS.slice(0, 4).map((t) => (
            <TouchableOpacity
              key={t.key}
              style={[styles.tab, tab === t.key && styles.tabActive]}
              onPress={() => setTab(t.key)}
            >
              <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>
                {t.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        {TABS.length > 4 && (
          <View style={[styles.tabs, styles.tabsRow2]}>
            {TABS.slice(4).map((t) => (
              <TouchableOpacity
                key={t.key}
                style={[styles.tab, styles.tabRow2, tab === t.key && styles.tabActive]}
                onPress={() => setTab(t.key)}
              >
                <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>
                  {t.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>

      <View style={styles.contentWrapper}>
      <ScrollView
        style={styles.content}
        contentContainerStyle={{ flexGrow: 1 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />}
      >
        {tab === 'info' && <InfoTab ticket={ticket} fecha={fecha} />}
        {tab === 'procesos' && (
          <ProcesosTab procesos={procesos} ticketId={ticketId} editable={editable} navigation={navigation} />
        )}
        {tab === 'repuestos' && (
          <RepuestosTab repuestos={repuestos} ticketId={ticketId} editable={editable} navigation={navigation} />
        )}
        {tab === 'fotos' && (
          <FotosTab fotos={fotos} ticketId={ticketId} editable={editable} navigation={navigation} onRefresh={loadData} />
        )}
        {tab === 'compras' && (
          <ComprasTab compras={compras} ticketId={ticketId} editable={editable} navigation={navigation} onRefresh={loadData} />
        )}
        {tab === 'finanzas' && <FinanzasTab resumen={resumen} ticketId={ticketId} editable={editable} onRefresh={loadData} compras={compras} />}
        {tab === 'entrega' && (
          <EntregaTab ticketId={ticketId} onSuccess={() => { loadData(); setTab('info'); }} />
        )}
      </ScrollView>
      </View>
    </View>
  );
}

function InfoTab({ ticket, fecha }) {
  return (
    <View style={styles.section}>
      <InfoRow label="Propietario" value={ticket.nombre_propietario || '—'} />
      <InfoRow label="Teléfono" value={ticket.telefono_propietario || '—'} />
      <InfoRow label="Motivo" value={ticket.motivo_visita} />
      <InfoRow label="Fecha ingreso" value={fecha} />
      <InfoRow label="Kilometraje" value={ticket.kilometraje ? `${ticket.kilometraje} km` : '—'} />
      <InfoRow label="Estado inicial" value={ticket.estado_inicial || '—'} />
      {ticket.observaciones_recepcion && (
        <InfoRow label="Observaciones" value={ticket.observaciones_recepcion} />
      )}
    </View>
  );
}

function ProcesosTab({ procesos, ticketId, editable, navigation }) {
  return (
    <View style={styles.section}>
      {editable && (
        <TouchableOpacity style={styles.addBtn} onPress={() => navigation.navigate('AddProceso', { ticketId })}>
          <Text style={styles.addBtnText}>+ Agregar Proceso</Text>
        </TouchableOpacity>
      )}
      {procesos.length === 0
        ? <Text style={styles.emptyText}>No hay procesos registrados</Text>
        : procesos.map((p) => (
          <View key={p.id} style={styles.itemCard}>
            <Text style={styles.itemTitle}>{p.nombre}</Text>
            {p.mecanico && <Text style={styles.itemSub}>🔧 {p.mecanico}</Text>}
            {p.descripcion && <Text style={styles.itemDesc}>{p.descripcion}</Text>}
          </View>
        ))
      }
    </View>
  );
}

function RepuestosTab({ repuestos, ticketId, editable, navigation }) {
  return (
    <View style={styles.section}>
      {editable && (
        <TouchableOpacity style={styles.addBtn} onPress={() => navigation.navigate('AddRepuesto', { ticketId })}>
          <Text style={styles.addBtnText}>+ Agregar Repuesto</Text>
        </TouchableOpacity>
      )}
      {repuestos.length === 0
        ? <Text style={styles.emptyText}>No hay repuestos registrados</Text>
        : repuestos.map((r) => (
          <View key={r.id} style={styles.itemCard}>
            <View style={styles.repuestoRow}>
              <Text style={styles.itemTitle}>{r.nombre}</Text>
              <View style={styles.cantBadge}>
                <Text style={styles.cantText}>x{r.cantidad}</Text>
              </View>
            </View>
            {r.marca_referencia && <Text style={styles.itemSub}>{r.marca_referencia}</Text>}
          </View>
        ))
      }
    </View>
  );
}

function FotosTab({ fotos, ticketId, editable, navigation, onRefresh }) {
  const handleEliminar = (fotoId) => {
    Alert.alert(
      'Eliminar foto',
      '¿Estás seguro de que quieres eliminar esta foto?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.eliminarFoto(ticketId, fotoId);
              onRefresh();
            } catch (e) {
              Alert.alert('Error', e.message);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={styles.section}>
      {editable && (
        <TouchableOpacity style={styles.addBtn} onPress={() => navigation.navigate('AddFoto', { ticketId })}>
          <Text style={styles.addBtnText}>📷 Agregar Foto</Text>
        </TouchableOpacity>
      )}
      {fotos.length === 0
        ? <Text style={styles.emptyText}>No hay fotos registradas</Text>
        : fotos.map((f) => (
          <View key={f.id} style={styles.fotoCard}>
            <View style={styles.fotoHeader}>
              <View style={styles.tipoBadge}>
                <Text style={styles.tipoText}>{f.tipo}</Text>
              </View>
              {editable && (
                <TouchableOpacity style={styles.deleteBtn} onPress={() => handleEliminar(f.id)}>
                  <Text style={styles.deleteBtnText}>✕ Eliminar</Text>
                </TouchableOpacity>
              )}
            </View>
            <Image
              source={{ uri: `http://10.0.2.2:8000${f.archivo_url}` }}
              style={styles.fotoImg}
              resizeMode="cover"
            />
            {f.descripcion && <Text style={styles.fotoDesc}>{f.descripcion}</Text>}
          </View>
        ))
      }
    </View>
  );
}

function ComprasTab({ compras, ticketId, editable, navigation, onRefresh }) {
  const handleEliminar = (compraId) => {
    Alert.alert('Eliminar compra', '¿Eliminar esta compra?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Eliminar', style: 'destructive',
        onPress: async () => {
          try {
            await api.eliminarCompra(ticketId, compraId);
            onRefresh();
          } catch (e) {
            Alert.alert('Error', e.message);
          }
        },
      },
    ]);
  };

  const fmt = (v) => v != null ? `$${v.toLocaleString('es-CO')}` : '—';

  return (
    <View style={styles.section}>
      {editable && (
        <TouchableOpacity style={styles.addBtn} onPress={() => navigation.navigate('AddCompra', { ticketId })}>
          <Text style={styles.addBtnText}>+ Registrar Compra</Text>
        </TouchableOpacity>
      )}
      {compras.length === 0
        ? <Text style={styles.emptyText}>No hay compras registradas</Text>
        : compras.map((c) => (
          <View key={c.id} style={styles.itemCard}>
            {c.soporte_url ? (
              <Image
                source={{ uri: `http://10.0.2.2:8000${c.soporte_url}` }}
                style={{ width: '100%', height: 160, borderRadius: 0 }}
                resizeMode="cover"
              />
            ) : null}
            <View style={styles.compraRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.itemTitle}>{c.descripcion}</Text>
                {c.responsable && <Text style={styles.itemSub}>👤 {c.responsable}</Text>}
                {c.nota && <Text style={styles.itemDesc}>{c.nota}</Text>}
              </View>
              <View style={styles.compraValorCol}>
                <Text style={styles.compraValor}>{fmt(c.valor)}</Text>
                {editable && (
                  <TouchableOpacity style={styles.deleteBtn} onPress={() => handleEliminar(c.id)}>
                    <Text style={styles.deleteBtnText}>✕</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          </View>
        ))
      }
    </View>
  );
}

function FinanzasTab({ resumen, ticketId, editable, onRefresh, compras = [] }) {
  const [cobros, setCobros] = useState([]);
  const [concepto, setConcepto] = useState('');
  const [valorCobro, setValorCobro] = useState('');
  const [totalServicio, setTotalServicio] = useState('');
  const [metodoPago, setMetodoPago] = useState('Efectivo');
  const [savingFinanzas, setSavingFinanzas] = useState(false);
  const [addingCobro, setAddingCobro] = useState(false);

  const METODOS = ['Efectivo', 'Transferencia', 'Tarjeta', 'Nequi', 'Daviplata'];

  useEffect(() => {
    api.getCobros(ticketId).then(setCobros).catch(() => {});
    if (resumen?.finanzas?.total_servicio != null) {
      setTotalServicio(String(resumen.finanzas.total_servicio));
    }
  }, [ticketId, resumen]);

  if (!resumen) return null;
  const f = resumen.finanzas;
  const fmt = (v) => v != null ? `$${v.toLocaleString('es-CO')}` : '$0';

  const handleAgregarCobro = async () => {
    if (!concepto.trim()) {
      Alert.alert('Campo requerido', 'El concepto es obligatorio');
      return;
    }
    const valorNum = parseInt(valorCobro, 10);
    if (isNaN(valorNum) || valorNum <= 0) {
      Alert.alert('Valor inválido', 'Ingresa un valor numérico mayor a 0');
      return;
    }
    setAddingCobro(true);
    try {
      await api.createCobro(ticketId, { concepto: concepto.trim(), valor: valorNum });
      setConcepto('');
      setValorCobro('');
      const [c, r] = await Promise.all([api.getCobros(ticketId), onRefresh()]);
      setCobros(c || []);
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setAddingCobro(false);
    }
  };

  const handleEliminarCobro = (cobroId) => {
    Alert.alert('Eliminar cobro', '¿Eliminar este cobro?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Eliminar', style: 'destructive',
        onPress: async () => {
          try {
            await api.eliminarCobro(ticketId, cobroId);
            const c = await api.getCobros(ticketId);
            setCobros(c);
            onRefresh();
          } catch (e) {
            Alert.alert('Error', e.message);
          }
        },
      },
    ]);
  };

  const handleActualizarFinanzas = async () => {
    setSavingFinanzas(true);
    try {
      await api.actualizarFinanzas(ticketId, {
        total_servicio: parseInt(totalServicio) || 0,
        metodo_pago_final: metodoPago,
      });
      await onRefresh();
      Alert.alert('✓', 'Finanzas actualizadas');
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setSavingFinanzas(false);
    }
  };

  const totalCobros = cobros.reduce((s, c) => s + c.valor, 0);

  return (
    <View style={styles.section}>
      {/* Banner egresos */}
      {f.total_egresos > 0 && (
        <View style={styles.finBanner}>
          <Text style={styles.finBannerTitle}>💰 Egresos del Ticket: {fmt(f.total_egresos)}</Text>
          <Text style={styles.finBannerSub}>Has gastado {fmt(f.total_egresos)} en compras para este ticket.</Text>
        </View>
      )}

      {/* Tarjetas resumen */}
      <View style={styles.finCards}>
        <View style={styles.finCard}>
          <Text style={styles.finCardLabel}>Anticipo Recibido</Text>
          <Text style={styles.finCardValue}>{fmt(f.anticipo)}</Text>
        </View>
        <View style={[styles.finCard, f.total_egresos > 0 && styles.finCardRed]}>
          <Text style={styles.finCardLabel}>Total Egresos</Text>
          <Text style={[styles.finCardValue, { color: colors.error }]}>{fmt(f.total_egresos)}</Text>
        </View>
        <View style={styles.finCard}>
          <Text style={styles.finCardLabel}>Total del Servicio</Text>
          <Text style={[styles.finCardValue, { color: colors.primary }]}>{fmt(f.total_servicio)}</Text>
        </View>
        <View style={styles.finCard}>
          <Text style={styles.finCardLabel}>Saldo Pendiente</Text>
          <Text style={styles.finCardValue}>{fmt(f.saldo_pendiente)}</Text>
        </View>
      </View>

      {/* Detalle egresos */}
      {compras?.length > 0 && (
        <View style={styles.finSection}>
          <Text style={styles.finSectionTitle}>Detalle de Egresos</Text>
          {compras.map((c, i) => (
            <View key={i} style={styles.finDetalleRow}>
              <Text style={styles.finDetalleLabel}>{c.descripcion}</Text>
              <Text style={[styles.finDetalleValue, { color: colors.error }]}>{fmt(c.valor)}</Text>
            </View>
          ))}
          <View style={styles.divider} />
          <View style={styles.finDetalleRow}>
            <Text style={[styles.finDetalleLabel, { fontWeight: '700' }]}>Total Egresos</Text>
            <Text style={[styles.finDetalleValue, { fontWeight: '700' }]}>{fmt(f.total_egresos)}</Text>
          </View>
        </View>
      )}

      {/* Items de cobro */}
      {editable && (
        <View style={styles.finSection}>
          <Text style={styles.finSectionTitle}>Items de Cobro</Text>
          <View style={styles.finForm}>
            <Text style={styles.fieldLabel}>Concepto *</Text>
            <TextInput
              style={styles.fieldInput}
              placeholder="Ej: Mantenimiento, Mano de obra, Diagnóstico"
              placeholderTextColor={colors.textMuted}
              value={concepto}
              onChangeText={setConcepto}
            />
            <Text style={styles.fieldLabel}>Valor *</Text>
            <TextInput
              style={styles.fieldInput}
              placeholder="0"
              placeholderTextColor={colors.textMuted}
              value={valorCobro}
              onChangeText={(t) => setValorCobro(t.replace(/[^0-9]/g, ''))}
              keyboardType="numeric"
            />
            <TouchableOpacity
              style={[styles.addBtn, addingCobro && styles.btnDisabled]}
              onPress={handleAgregarCobro}
              disabled={addingCobro}
            >
              {addingCobro
                ? <ActivityIndicator color="#fff" size="small" />
                : <Text style={styles.addBtnText}>Agregar Cobro</Text>
              }
            </TouchableOpacity>
          </View>
          {cobros.length === 0
            ? <Text style={[styles.emptyText, { marginTop: 8 }]}>No hay cobros definidos</Text>
            : cobros.map((c) => (
              <View key={c.id} style={styles.finCobroRow}>
                <Text style={styles.finDetalleLabel}>{c.concepto}</Text>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Text style={[styles.finDetalleValue, { color: colors.primary }]}>{fmt(c.valor)}</Text>
                  <TouchableOpacity onPress={() => handleEliminarCobro(c.id)}>
                    <Text style={{ color: colors.error, fontWeight: '700' }}>✕</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          }
          {cobros.length > 0 && (
            <View style={styles.finDetalleRow}>
              <Text style={[styles.finDetalleLabel, { fontWeight: '700' }]}>Total Cobros</Text>
              <Text style={[styles.finDetalleValue, { fontWeight: '700', color: colors.primary }]}>{fmt(totalCobros)}</Text>
            </View>
          )}
        </View>
      )}

      {/* Definir finanzas */}
      {editable && (
        <View style={styles.finSection}>
          <Text style={styles.finSectionTitle}>Definir Finanzas</Text>
          <Text style={styles.fieldLabel}>Total del Servicio *</Text>
          <TextInput
            style={styles.fieldInput}
            placeholder="0"
            placeholderTextColor={colors.textMuted}
            value={totalServicio}
            onChangeText={(t) => setTotalServicio(t.replace(/[^0-9]/g, ''))}
            keyboardType="numeric"
          />
          <Text style={styles.fieldLabel}>Método de Pago Final</Text>
          <View style={styles.finMetodosRow}>
            {METODOS.map((m) => (
              <TouchableOpacity
                key={m}
                style={[styles.finMetodoBtn, metodoPago === m && styles.finMetodoBtnActive]}
                onPress={() => setMetodoPago(m)}
              >
                <Text style={[styles.finMetodoBtnText, metodoPago === m && styles.finMetodoBtnTextActive]}>{m}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity
            style={[styles.addBtn, savingFinanzas && styles.btnDisabled]}
            onPress={handleActualizarFinanzas}
            disabled={savingFinanzas}
          >
            {savingFinanzas
              ? <ActivityIndicator color="#fff" size="small" />
              : <Text style={styles.addBtnText}>Actualizar Finanzas</Text>
            }
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

function EntregaTab({ ticketId, onSuccess, ticketCodigo }) {
  const [confirmadoPor, setConfirmadoPor] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [recomendaciones, setRecomendaciones] = useState('');
  const [proximoMantenimiento, setProximoMantenimiento] = useState('');
  const [loading, setLoading] = useState(false);

  const handleEntregar = async () => {
    if (!confirmadoPor.trim()) {
      Alert.alert('Campo requerido', 'Ingresa quién confirma la entrega');
      return;
    }
    Alert.alert(
      'Confirmar entrega',
      '¿Marcar este ticket como entregado?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Confirmar',
          onPress: async () => {
            setLoading(true);
            try {
              await api.entregarTicket(ticketId, {
                confirmado_entrega_por: confirmadoPor.trim(),
                observaciones_finales: observaciones.trim() || null,
                recomendaciones: recomendaciones.trim() || null,
                proximo_mantenimiento: proximoMantenimiento.trim() || null,
              });
              Alert.alert('✓ Éxito', 'Ticket marcado como entregado');
              onSuccess();
            } catch (e) {
              Alert.alert('Error', e.message);
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={styles.section}>
      <View style={styles.entregaCard}>
        <Text style={styles.entregaTitle}>📦 Registrar Entrega</Text>
        <Text style={styles.entregaSubtitle}>Completa los datos para finalizar la entrega del vehículo</Text>
      </View>

      <Text style={styles.fieldLabel}>Confirmado por *</Text>
      <TextInput
        style={styles.fieldInput}
        placeholder="Nombre de quien recibe el vehículo"
        placeholderTextColor={colors.textMuted}
        value={confirmadoPor}
        onChangeText={setConfirmadoPor}
      />

      <Text style={styles.fieldLabel}>Observaciones finales</Text>
      <TextInput
        style={[styles.fieldInput, styles.fieldTextArea]}
        placeholder="Observaciones sobre el trabajo realizado..."
        placeholderTextColor={colors.textMuted}
        value={observaciones}
        onChangeText={setObservaciones}
        multiline
        numberOfLines={3}
        textAlignVertical="top"
      />

      <Text style={styles.fieldLabel}>Recomendaciones</Text>
      <TextInput
        style={[styles.fieldInput, styles.fieldTextArea]}
        placeholder="Recomendaciones para el cliente..."
        placeholderTextColor={colors.textMuted}
        value={recomendaciones}
        onChangeText={setRecomendaciones}
        multiline
        numberOfLines={3}
        textAlignVertical="top"
      />

      <Text style={styles.fieldLabel}>Próximo mantenimiento</Text>
      <TextInput
        style={styles.fieldInput}
        placeholder="Ej: En 3 meses o 3000 km"
        placeholderTextColor={colors.textMuted}
        value={proximoMantenimiento}
        onChangeText={setProximoMantenimiento}
      />

      <TouchableOpacity
        style={[styles.entregaBtn, loading && styles.btnDisabled]}
        onPress={handleEntregar}
        disabled={loading}
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.entregaBtnText}>📦 Confirmar Entrega</Text>
        }
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.pdfBtn}
        onPress={() => Linking.openURL(api.getPdfUrl(ticketId))}
      >
        <Text style={styles.pdfBtnText}>📄 Ver / Descargar PDF del cliente</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.pdfShareBtn}
        onPress={async () => {
          try {
            await Share.share({ message: `PDF del ticket: ${api.getPdfUrl(ticketId)}` });
          } catch (e) {
            Alert.alert('Error', e.message);
          }
        }}
      >
        <Text style={styles.pdfShareBtnText}>🔗 Compartir enlace del PDF</Text>
      </TouchableOpacity>
    </View>
  );
}

function InfoRow({ label, value }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function FinRow({ label, value, color, bold }) {
  return (
    <View style={styles.finRow}>
      <Text style={styles.finLabel}>{label}</Text>
      <Text style={[styles.finValue, { color }, bold && { fontSize: 18 }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  ticketHeader: { backgroundColor: colors.primary, padding: 16 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  placa: { fontSize: 22, fontWeight: 'bold', color: '#fff', letterSpacing: 1 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  badgeText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  codigo: { fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 12 },
  estadoBtn: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.5)',
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: 'center',
  },
  estadoBtnDisabled: { opacity: 0.6 },
  estadoBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  tabsContainer: {
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tabsScroll: {
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    maxHeight: 46,
  },
  tabs: { flexDirection: 'row' },
  tabsRow2: { borderTopWidth: 1, borderTopColor: colors.border },
  tab: { flex: 1, paddingVertical: 9, paddingHorizontal: 4, alignItems: 'center' },
  tabRow2: { flex: 1 },
  tabActive: { borderBottomWidth: 2, borderBottomColor: colors.primary },
  tabText: { fontSize: 11, color: colors.textMuted, fontWeight: '500', textAlign: 'center' },
  tabTextActive: { color: colors.primary, fontWeight: '700' },
  content: { flex: 1 },
  contentWrapper: { flex: 1, overflow: 'hidden' },
  section: { padding: 16 },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  infoLabel: { fontSize: 13, color: colors.textMuted, flex: 1 },
  infoValue: { fontSize: 13, color: colors.text, fontWeight: '600', flex: 2, textAlign: 'right' },
  addBtn: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    marginBottom: 14,
  },
  addBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  itemCard: {
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  itemTitle: { fontSize: 14, fontWeight: '700', color: colors.text },
  itemSub: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  itemDesc: { fontSize: 13, color: colors.text, marginTop: 4 },
  repuestoRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cantBadge: { backgroundColor: colors.primaryLight, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 2 },
  cantText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  emptyText: { color: colors.textMuted, textAlign: 'center', marginTop: 24, fontSize: 14 },
  fotoCard: {
    backgroundColor: colors.surface,
    borderRadius: 10,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  compraRow: { flexDirection: 'row', alignItems: 'flex-start' },
  compraValorCol: { alignItems: 'flex-end', gap: 6 },
  compraValor: { fontSize: 16, fontWeight: '700', color: colors.error },
  fotoHeader: { flexDirection: 'row', padding: 8, justifyContent: 'space-between', alignItems: 'center' },
  tipoBadge: { backgroundColor: colors.primaryLight, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 },
  tipoText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  deleteBtn: { backgroundColor: colors.error, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 4 },
  deleteBtnText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  fotoImg: { width: '100%', height: 200 },
  fotoDesc: { padding: 8, fontSize: 13, color: colors.textMuted },
  finRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  finLabel: { fontSize: 14, color: colors.textMuted },
  finValue: { fontSize: 15, fontWeight: '700' },
  finBanner: { backgroundColor: '#fef9c3', borderWidth: 1, borderColor: '#fde047', borderRadius: 8, padding: 12, marginBottom: 12 },
  finBannerTitle: { fontSize: 14, fontWeight: '700', color: '#854d0e' },
  finBannerSub: { fontSize: 12, color: '#92400e', marginTop: 2 },
  finCards: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  finCard: { flex: 1, minWidth: '45%', backgroundColor: colors.surface, borderRadius: 8, borderWidth: 1, borderColor: colors.border, padding: 10 },
  finCardRed: { backgroundColor: '#fef2f2', borderColor: '#fecaca' },
  finCardLabel: { fontSize: 11, color: colors.textMuted, marginBottom: 4 },
  finCardValue: { fontSize: 16, fontWeight: '700', color: colors.text },
  finSection: { backgroundColor: colors.surface, borderRadius: 10, borderWidth: 1, borderColor: colors.border, padding: 12, marginBottom: 12 },
  finSectionTitle: { fontSize: 15, fontWeight: '700', color: colors.text, marginBottom: 10 },
  finDetalleRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  finDetalleLabel: { fontSize: 13, color: colors.text, flex: 1 },
  finDetalleValue: { fontSize: 13, color: colors.text },
  finForm: { backgroundColor: colors.background, borderRadius: 8, padding: 10, marginBottom: 10 },
  finCobroRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.border },
  finMetodosRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  finMetodoBtn: { paddingVertical: 6, paddingHorizontal: 12, borderRadius: 20, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  finMetodoBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  finMetodoBtnText: { fontSize: 12, color: colors.textMuted },
  finMetodoBtnTextActive: { color: '#fff', fontWeight: '600' },
  divider: { height: 8 },
  // Entrega
  entregaCard: {
    backgroundColor: colors.primaryDark,
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
  },
  entregaTitle: { fontSize: 18, fontWeight: '700', color: '#fff', marginBottom: 4 },
  entregaSubtitle: { fontSize: 13, color: 'rgba(255,255,255,0.75)' },
  fieldLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textMuted,
    marginBottom: 6,
    marginTop: 14,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  fieldInput: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.text,
  },
  fieldTextArea: { height: 90, paddingTop: 12 },
  entregaBtn: {
    backgroundColor: colors.primaryDark,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 24,
  },
  btnDisabled: { opacity: 0.6 },
  entregaBtnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  pdfBtn: { marginTop: 12, backgroundColor: '#f0f9ff', borderWidth: 1, borderColor: '#0ea5e9', borderRadius: 10, padding: 14, alignItems: 'center' },
  pdfBtnText: { color: '#0369a1', fontWeight: '600', fontSize: 14 },
  pdfShareBtn: { marginTop: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, alignItems: 'center' },
  pdfShareBtnText: { color: colors.primary, fontWeight: '600', fontSize: 14 },
});
