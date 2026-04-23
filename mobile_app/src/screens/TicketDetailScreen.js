import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  RefreshControl, ActivityIndicator, Alert, Image, TextInput, Linking, Share,
  Platform, Keyboard,
} from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import { useFocusEffect } from '@react-navigation/native';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { api } from '../api';
import { getApiBaseUrl, getPdfBaseUrl } from '../config';
import { colors, estadoConfig } from '../theme';
import { useToast } from '../components/Toast';
import { useOffline } from '../hooks/useOffline';
import offlineService from '../services/offlineService';
import authService from '../services/authService';

const ESTADOS_SIGUIENTES = {
  ABIERTO: 'EN_PROCESO',
  EN_PROCESO: 'FINALIZADO',
  FINALIZADO: 'ENTREGADO',
};

const LABELS_SIGUIENTE = {
  ABIERTO: '▶ Iniciar Proceso',
  EN_PROCESO: '✓ Marcar Finalizado',
  FINALIZADO: 'Marcar Entregado',
};

export default function TicketDetailScreen({ route, navigation }) {
  const { ticketId } = route.params;
  const toast = useToast();
  const { isOnline } = useOffline();
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
  const scrollRef = useRef(null);

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
      toast(e.message, 'error');
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
              if (!isOnline) {
                await offlineService.enqueueOperation({
                  type: 'CAMBIAR_ESTADO',
                  endpoint: `/tickets/${ticketId}/estado`,
                  method: 'PATCH',
                  data: { estado: siguiente },
                });
                toast('Sin conexión — el cambio se aplicará cuando vuelva el internet', 'warning');
                setUpdatingEstado(false);
                return;
              }
              await api.updateEstado(ticketId, siguiente);
              await loadData();
            } catch (e) {
              toast(e.message, 'error');
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
  const isEntregado = ticket.estado === 'ENTREGADO';

  const TABS = [
    { key: 'info', label: 'Info' },
    { key: 'procesos', label: `Procesos (${resumen?.contadores?.procesos ?? 0})` },
    { key: 'repuestos', label: `Repuestos (${resumen?.contadores?.repuestos ?? 0})` },
    { key: 'fotos', label: `Fotos (${resumen?.contadores?.fotos ?? 0})` },
    { key: 'finanzas', label: 'Finanzas y Observaciones' },
    ...(isFinalizado || isEntregado ? [{ key: 'entrega', label: isEntregado ? 'Entrega / PDF' : 'Entrega' }] : []),
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
      <KeyboardAwareScrollView
        ref={scrollRef}
        style={styles.content}
        contentContainerStyle={{ flexGrow: 1 }}
        keyboardShouldPersistTaps="handled"
        enableOnAndroid={true}
        extraScrollHeight={20}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />}
      >
        {tab === 'info' && <InfoTab ticket={ticket} fecha={fecha} />}
        {tab === 'procesos' && (
          <ProcesosTab procesos={procesos} ticketId={ticketId} editable={editable} navigation={navigation} onRefresh={loadData} isOnline={isOnline} />
        )}
        {tab === 'repuestos' && (
          <RepuestosTab repuestos={repuestos} compras={compras} ticketId={ticketId} editable={editable} navigation={navigation} onRefresh={loadData} isOnline={isOnline} />
        )}
        {tab === 'fotos' && (
          <FotosTab fotos={fotos} ticketId={ticketId} editable={editable} navigation={navigation} onRefresh={loadData} isOnline={isOnline} />
        )}
        {tab === 'finanzas' && <FinanzasTab resumen={resumen} ticketId={ticketId} editable={editable} onRefresh={loadData} compras={compras} scrollRef={scrollRef} isOnline={isOnline} />}
        {tab === 'entrega' && (
          <EntregaTab ticketId={ticketId} resumen={resumen} ticket={ticket} isEntregado={isEntregado} onSuccess={() => { loadData(); setTab('info'); }} scrollRef={scrollRef} />
        )}
      </KeyboardAwareScrollView>
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

function ProcesosTab({ procesos, ticketId, editable, navigation, onRefresh, isOnline }) {
  const toast = useToast();
  const [baseUrl, setBaseUrl] = React.useState('');
  React.useEffect(() => { getPdfBaseUrl().then(setBaseUrl).catch(() => {}); }, []);

  const handleEliminar = (procesoId) => {
    Alert.alert('Eliminar proceso', '¿Eliminar este proceso?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Eliminar', style: 'destructive',
        onPress: async () => {
          try {
            if (!isOnline) {
              await offlineService.enqueueOperation({
                type: 'DELETE_PROCESO',
                endpoint: `/tickets/${ticketId}/procesos/${procesoId}`,
                method: 'DELETE',
                data: {},
              });
              toast('Sin conexión — se eliminará cuando vuelva el internet', 'warning');
              return;
            }
            await api.eliminarProceso(ticketId, procesoId);
            onRefresh();
          } catch (e) {
            toast(e.message, 'error');
          }
        },
      },
    ]);
  };

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
          <View key={p.id} style={[styles.itemCard, { position: 'relative' }]}>
            {editable && (
              <TouchableOpacity
                style={styles.deleteBtn}
                onPress={() => handleEliminar(p.id)}
              >
                <Text style={styles.deleteBtnText}>✕</Text>
              </TouchableOpacity>
            )}
            {p.foto_url && baseUrl ? (
              <Image
                source={{ uri: `${baseUrl}${p.foto_url}` }}
                style={{ width: '100%', height: 180, borderRadius: 8, marginBottom: 8 }}
                resizeMode="cover"
              />
            ) : null}
            <Text style={styles.itemTitle}>{p.nombre}</Text>
            {p.mecanico && <Text style={styles.itemSub}>{p.mecanico}</Text>}
            {p.descripcion && <Text style={styles.itemDesc}>{p.descripcion}</Text>}
          </View>
        ))
      }
    </View>
  );
}

function RepuestosTab({ repuestos, compras = [], ticketId, editable, navigation, onRefresh, isOnline }) {
  const toast = useToast();
  const [baseUrl, setBaseUrl] = React.useState('');
  React.useEffect(() => { getPdfBaseUrl().then(setBaseUrl).catch(() => {}); }, []);

  // Agrupar compras por nombre como cola para manejar duplicados
  const comprasPorNombre = {};
  (compras || []).forEach(c => {
    if (!comprasPorNombre[c.descripcion]) comprasPorNombre[c.descripcion] = [];
    comprasPorNombre[c.descripcion].push(c);
  });
  const comprasUsadas = {};

  const handleEliminar = (repuestoId) => {
    Alert.alert('Eliminar repuesto', '¿Eliminar este repuesto?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Eliminar', style: 'destructive',
        onPress: async () => {
          try {
            if (!isOnline) {
              await offlineService.enqueueOperation({
                type: 'DELETE_REPUESTO',
                endpoint: `/tickets/${ticketId}/repuestos/${repuestoId}`,
                method: 'DELETE',
                data: {},
              });
              toast('Sin conexión — se eliminará cuando vuelva el internet', 'warning');
              return;
            }
            await api.eliminarRepuesto(ticketId, repuestoId);
            onRefresh();
          } catch (e) {
            toast(e.message, 'error');
          }
        },
      },
    ]);
  };

  return (
    <View style={styles.section}>
      {editable && (
        <TouchableOpacity style={styles.addBtn} onPress={() => navigation.navigate('AddRepuesto', { ticketId })}>
          <Text style={styles.addBtnText}>+ Agregar Repuesto</Text>
        </TouchableOpacity>
      )}
      {repuestos.length === 0
        ? <Text style={styles.emptyText}>No hay repuestos registrados</Text>
        : repuestos.map((r) => {
          const cola = comprasPorNombre[r.nombre] || [];
          const idx = comprasUsadas[r.nombre] || 0;
          const compra = cola[idx] || null;
          comprasUsadas[r.nombre] = idx + 1;
          const fotoUri = r.foto_url && baseUrl ? `${baseUrl}${r.foto_url}`
            : compra?.soporte_url ? compra.soporte_url
            : null;
          return (
            <View key={r.id} style={[styles.itemCard, { position: 'relative' }]}>
              {editable && (
                <TouchableOpacity style={styles.deleteBtn} onPress={() => handleEliminar(r.id)}>
                  <Text style={styles.deleteBtnText}>✕</Text>
                </TouchableOpacity>
              )}
              {fotoUri ? (
                <Image
                  source={{ uri: fotoUri }}
                  style={{ width: '100%', height: 160, borderRadius: 8, marginBottom: 8 }}
                  resizeMode="cover"
                />
              ) : null}
              <View style={styles.repuestoRow}>
                <Text style={styles.itemTitle}>{r.nombre}</Text>
                <View style={{ flexDirection: 'row', gap: 6, alignItems: 'center' }}>
                  {compra && (
                    <View style={{ backgroundColor: '#dcfce7', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 }}>
                      <Text style={{ color: '#166534', fontSize: 11, fontWeight: '700' }}>Comprado</Text>
                    </View>
                  )}
                  <View style={styles.cantBadge}>
                    <Text style={styles.cantText}>x{r.cantidad}</Text>
                  </View>
                </View>
              </View>
              {r.marca_referencia && <Text style={styles.itemSub}>{r.marca_referencia}</Text>}
              {compra?.valor > 0 && (
                <Text style={{ color: '#dc2626', fontWeight: '700', fontSize: 13, marginTop: 4 }}>
                  ${compra.valor.toLocaleString('es-CO')}
                  {compra.responsable ? ` · ${compra.responsable}` : ''}
                  {compra.nota ? ` · ${compra.nota}` : ''}
                </Text>
              )}
            </View>
          );
        })
      }
    </View>
  );
}

function FotosTab({ fotos, ticketId, editable, navigation, onRefresh, isOnline }) {
  const toast = useToast();
  const [baseUrl, setBaseUrl] = React.useState('');
  React.useEffect(() => { getPdfBaseUrl().then(setBaseUrl).catch(() => {}); }, []);

  const fotosVisibles = fotos.filter(f => f.tipo !== 'PROCESO');

  const handleEliminar = (fotoId) => {
    Alert.alert(
      'Eliminar foto',
      '¿Estas seguro de que quieres eliminar esta foto?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: async () => {
            try {
              if (!isOnline) {
                await offlineService.enqueueOperation({
                  type: 'DELETE_FOTO',
                  endpoint: `/tickets/${ticketId}/fotos/${fotoId}`,
                  method: 'DELETE',
                  data: {},
                });
                toast('Sin conexión — se eliminará cuando vuelva el internet', 'warning');
                return;
              }
              await api.eliminarFoto(ticketId, fotoId);
              onRefresh();
            } catch (e) {
              toast(e.message, 'error');
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
          <Text style={styles.addBtnText}>Agregar Foto</Text>
        </TouchableOpacity>
      )}
      {fotosVisibles.length === 0
        ? <Text style={styles.emptyText}>No hay fotos registradas</Text>
        : fotosVisibles.map((f) => (
          <View key={f.id} style={styles.fotoCard}>
            <View style={styles.fotoHeader}>
              <View style={styles.tipoBadge}>
                <Text style={styles.tipoText}>{f.tipo}</Text>
              </View>
              {editable && (
                <TouchableOpacity style={styles.deleteBtn} onPress={() => handleEliminar(f.id)}>
                  <Text style={styles.deleteBtnText}>✕</Text>
                </TouchableOpacity>
              )}
            </View>
            {baseUrl ? (
              <Image
                source={{ uri: `${baseUrl}${f.archivo_url}` }}
                style={styles.fotoImg}
                resizeMode="cover"
              />
            ) : null}
            {f.descripcion && <Text style={styles.fotoDesc}>{f.descripcion}</Text>}
          </View>
        ))
      }
    </View>
  );
}


function FinanzasTab({ resumen, ticketId, editable, onRefresh, compras = [], scrollRef, isOnline }) {
  const toast = useToast();
  const [cobros, setCobros] = useState([]);
  const [concepto, setConcepto] = useState('');
  const [valorCobro, setValorCobro] = useState('');
  const [metodoPago, setMetodoPago] = useState('Efectivo');
  const [savingFinanzas, setSavingFinanzas] = useState(false);
  const [addingCobro, setAddingCobro] = useState(false);
  const [cobrosRapidos, setCobrosRapidos] = useState([]);
  const [observaciones, setObservaciones] = useState({ observaciones_finales: '', recomendaciones: '', proximo_mantenimiento: '' });
  const [finalizando, setFinalizando] = useState(false);

  const METODOS = ['EFECTIVO', 'TRANSFERENCIA', 'TARJETA', 'NEQUI', 'DAVIPLATA'];

  // Formatea número con separadores de miles
  const fmtInput = (v) => {
    const n = String(v).replace(/\D/g, '');
    return n ? Number(n).toLocaleString('es-CO') : '';
  };
  const parseInput = (v) => v.replace(/\D/g, '');

  useEffect(() => {
    api.getCobros(ticketId).then(setCobros).catch(() => {});
    if (resumen?.finanzas?.metodo_pago_final) {
      setMetodoPago(resumen.finanzas.metodo_pago_final.toUpperCase());
    }
  }, [ticketId, resumen]);

  useEffect(() => {
    api.getCobrosRapidos().then((r) => { if (r?.cobros) setCobrosRapidos(r.cobros); }).catch(() => {});
  }, []);

  if (!resumen) return null;
  const f = resumen.finanzas;
  const fmt = (v) => v != null ? `$${v.toLocaleString('es-CO')}` : '$0';

  const handleAgregarCobro = async () => {
    if (!concepto.trim()) {
      toast('El concepto es obligatorio', 'warning');
      return;
    }
    const valorNum = parseInt(valorCobro, 10);
    if (isNaN(valorNum) || valorNum <= 0) {
      toast('Ingresa un valor numerico mayor a 0', 'warning');
      return;
    }
    setAddingCobro(true);
    try {
      if (!isOnline) {
        await offlineService.enqueueOperation({
          type: 'CREATE_COBRO',
          endpoint: `/tickets/${ticketId}/cobros`,
          method: 'POST',
          data: { concepto: concepto.trim(), valor: valorNum },
        });
        setConcepto('');
        setValorCobro('');
        toast('Sin conexión — se registrará cuando vuelva el internet', 'warning');
        return;
      }
      await api.createCobro(ticketId, { concepto: concepto.trim(), valor: valorNum });
      setConcepto('');
      setValorCobro('');
      const [c, r] = await Promise.all([api.getCobros(ticketId), onRefresh()]);
      setCobros(c || []);
    } catch (e) {
      toast(e.message, 'error');
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
            if (!isOnline) {
              await offlineService.enqueueOperation({
                type: 'DELETE_COBRO',
                endpoint: `/tickets/${ticketId}/cobros/${cobroId}`,
                method: 'DELETE',
                data: {},
              });
              toast('Sin conexión — se eliminará cuando vuelva el internet', 'warning');
              return;
            }
            await api.eliminarCobro(ticketId, cobroId);
            const c = await api.getCobros(ticketId);
            setCobros(c);
            onRefresh();
          } catch (e) {
            toast(e.message, 'error');
          }
        },
      },
    ]);
  };

  const handleAgregarEgresoComoCobro = async (descripcion, valor) => {
    try {
      await api.createCobro(ticketId, { concepto: descripcion, valor });
      const c = await api.getCobros(ticketId);
      setCobros(c || []);
      onRefresh();
      toast(`"${descripcion}" agregado como cobro`, 'success');
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const handleActualizarFinanzas = async () => {
    if (totalCobros <= 0) {
      toast('Agrega al menos un cobro antes de guardar', 'warning');
      return;
    }
    setSavingFinanzas(true);
    try {
      await api.actualizarFinanzas(ticketId, {
        total_servicio: totalCobros,
        metodo_pago_final: metodoPago,
      });
      await onRefresh();
      toast('Finanzas guardadas', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSavingFinanzas(false);
    }
  };

  const totalCobros = cobros.reduce((s, c) => s + c.valor, 0);

  const handleFinalizar = async () => {
    if (totalCobros <= 0) {
      toast('Agrega al menos un cobro antes de finalizar', 'warning');
      return;
    }
    Alert.alert('Finalizar Ticket', '¿Finalizar este ticket? Ya no podrás agregar más procesos.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Finalizar',
        onPress: async () => {
          setFinalizando(true);
          try {
            // Si está ABIERTO, pasar primero a EN_PROCESO
            if (resumen?.ticket?.estado === 'ABIERTO') {
              await api.cambiarEstadoTicket(ticketId, 'EN_PROCESO');
            }
            // Guardar finanzas y observaciones
            await api.actualizarFinanzas(ticketId, {
              total_servicio: totalCobros,
              metodo_pago_final: metodoPago,
              observaciones_finales: observaciones.observaciones_finales || null,
              recomendaciones: observaciones.recomendaciones || null,
              proximo_mantenimiento: observaciones.proximo_mantenimiento || null,
            });
            // Luego finalizar
            await api.finalizarTicket(ticketId);
            await onRefresh();
            toast('Ticket finalizado', 'success');
          } catch (e) {
            toast(e.message, 'error');
          } finally {
            setFinalizando(false);
          }
        },
      },
    ]);
  };

  return (
    <View style={styles.section}>
      {/* Banner egresos */}
      {f.total_egresos > 0 && (
        <View style={styles.finBanner}>
          <Text style={styles.finBannerTitle}>Egresos del Ticket: {fmt(f.total_egresos)}</Text>
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
            <TouchableOpacity
              key={i}
              style={styles.finDetalleRow}
              onPress={editable ? () => handleAgregarEgresoComoCobro(c.descripcion, c.valor) : undefined}
              activeOpacity={editable ? 0.5 : 1}
            >
              <Text style={styles.finDetalleLabel}>{c.descripcion}</Text>
              <Text style={[styles.finDetalleValue, { color: colors.error }]}>{fmt(c.valor)}</Text>
            </TouchableOpacity>
          ))}
          <View style={styles.divider} />
          <View style={styles.finDetalleRow}>
            <Text style={[styles.finDetalleLabel, { fontWeight: '700' }]}>Total Egresos</Text>
            <Text style={[styles.finDetalleValue, { fontWeight: '700' }]}>{fmt(f.total_egresos)}</Text>
          </View>
          {editable && (
            <Text style={styles.egresoHint}>Toca un egreso para agregarlo como cobro</Text>
          )}
        </View>
      )}

      {/* Cobros y cierre */}
      {editable && (
        <View style={styles.finSection}>
          <Text style={styles.finSectionTitle}>Cobros y Cierre</Text>

          {/* Formulario agregar cobro */}
          <View style={styles.finForm}>
            {cobrosRapidos.length > 0 && (
              <View style={{ marginBottom: 10 }}>
                <Text style={[styles.fieldLabel, { marginBottom: 6 }]}>Acceso rápido</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                  {cobrosRapidos.map((c, i) => (
                    <TouchableOpacity
                      key={i}
                      style={styles.quickChip}
                      onPress={() => setConcepto(c)}
                    >
                      <Text style={styles.quickChipText}>{c}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}
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
              value={fmtInput(valorCobro)}
              onChangeText={(t) => setValorCobro(parseInput(t))}
              keyboardType="numeric"
            />
            <TouchableOpacity
              style={[styles.addBtn, addingCobro && styles.btnDisabled]}
              onPress={handleAgregarCobro}
              disabled={addingCobro}
            >
              {addingCobro
                ? <ActivityIndicator color="#fff" size="small" />
                : <Text style={styles.addBtnText}>+ Agregar Cobro</Text>
              }
            </TouchableOpacity>
          </View>

          {/* Lista de cobros */}
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

          {/* Total calculado automáticamente */}
          {cobros.length > 0 && (
            <>
              <View style={[styles.finDetalleRow, { marginTop: 4 }]}>
                <Text style={[styles.finDetalleLabel, { fontWeight: '700' }]}>Total del Servicio</Text>
                <Text style={[styles.finDetalleValue, { fontWeight: '700', color: colors.primary }]}>{fmt(totalCobros)}</Text>
              </View>

              {f.anticipo > 0 && (
                <>
                  <View style={styles.finDetalleRow}>
                    <Text style={[styles.finDetalleLabel, { color: '#16a34a' }]}>— Anticipo recibido</Text>
                    <Text style={[styles.finDetalleValue, { color: '#16a34a' }]}>-{fmt(f.anticipo)}</Text>
                  </View>
                  <View style={[styles.finDetalleRow, { borderTopWidth: 2, borderTopColor: colors.primary, paddingTop: 6 }]}>
                    <Text style={[styles.finDetalleLabel, { fontWeight: '700' }]}>Saldo a Pagar</Text>
                    <Text style={[styles.finDetalleValue, { fontWeight: '700', color: colors.primary }]}>
                      {fmt(Math.max(0, totalCobros - f.anticipo))}
                    </Text>
                  </View>
                </>
              )}

              {/* Método de pago — se selecciona en Entrega */}

              <TouchableOpacity
                style={[styles.addBtn, { marginTop: 12 }, savingFinanzas && styles.btnDisabled]}
                onPress={handleActualizarFinanzas}
                disabled={savingFinanzas}
              >
                {savingFinanzas
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.addBtnText}>Listo para Cobro</Text>
                }
              </TouchableOpacity>
            </>
          )}
        </View>
      )}
      {/* Observaciones y Recomendaciones */}
      {editable && (
        <View style={styles.finSection}>
          <Text style={styles.finSectionTitle}>Observaciones y Recomendaciones</Text>

          <Text style={styles.fieldLabel}>Observaciones Finales</Text>
          <TextInput
            style={[styles.fieldInput, styles.fieldTextArea]}
            placeholder="Observaciones sobre el trabajo realizado..."
            placeholderTextColor={colors.textMuted}
            value={observaciones.observaciones_finales}
            onChangeText={(t) => setObservaciones({ ...observaciones, observaciones_finales: t })}
            multiline
            numberOfLines={3}
            textAlignVertical="top"
          />

          <Text style={styles.fieldLabel}>Recomendaciones</Text>
          <TextInput
            style={[styles.fieldInput, styles.fieldTextArea]}
            placeholder="Recomendaciones para el cliente..."
            placeholderTextColor={colors.textMuted}
            value={observaciones.recomendaciones}
            onChangeText={(t) => setObservaciones({ ...observaciones, recomendaciones: t })}
            multiline
            numberOfLines={3}
            textAlignVertical="top"
          />

          <Text style={styles.fieldLabel}>Próximo Mantenimiento</Text>
          <TextInput
            style={styles.fieldInput}
            placeholder="Ej: 2026-06 o en 5000 km"
            placeholderTextColor={colors.textMuted}
            value={observaciones.proximo_mantenimiento}
            onChangeText={(t) => setObservaciones({ ...observaciones, proximo_mantenimiento: t })}
          />

          <TouchableOpacity
            style={[styles.entregaBtn, { marginTop: 16, backgroundColor: '#16a34a' }, finalizando && styles.btnDisabled]}
            onPress={handleFinalizar}
            disabled={finalizando}
          >
            {finalizando
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.entregaBtnText}>Finalizar Ticket</Text>
            }
          </TouchableOpacity>
          <Text style={{ color: colors.textMuted, fontSize: 12, textAlign: 'center', marginTop: 6 }}>
            Al finalizar el ticket no podrás agregar más procesos. El cobro se registra al entregar.
          </Text>
        </View>
      )}
    </View>
  );
}

function EntregaTab({ ticketId, resumen, ticket, isEntregado, onSuccess, ticketCodigo, scrollRef }) {
  const toast = useToast();
  const [confirmadoPor, setConfirmadoPor] = useState('');
  const [metodoPago, setMetodoPago] = useState('EFECTIVO');
  const [cobros, setCobros] = useState([]);
  const [loading, setLoading] = useState(false);

  const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'TRANSFERENCIA', 'TARJETA'];

  useEffect(() => {
    api.getCobros(ticketId).then(setCobros).catch(() => {});
  }, [ticketId]);

  const fmt = (v) => v != null ? `$${Number(v).toLocaleString('es-CO')}` : '$0';
  const totalServicio = resumen?.finanzas?.total_servicio || 0;
  const anticipo = resumen?.finanzas?.anticipo || 0;
  const totalCobrar = Math.max(0, totalServicio - anticipo);

  const handleDescargarPdf = async () => {
    try {
      toast('Generando PDF...', 'info');
      const base = await getPdfBaseUrl();
      const nombreArchivo = `ticket_${ticket?.ticket_codigo || ticketId}.pdf`;
      const destino = FileSystem.cacheDirectory + nombreArchivo;

      // Descargar con JWT en header usando fetch autenticado
      const response = await authService.authenticatedRequest(
        `${base}/tickets/${ticketId}/pdf`, {}
      );

      if (!response.ok) {
        throw new Error(`Error ${response.status} al generar el PDF`);
      }

      // Convertir respuesta a base64 y guardar
      const blob = await response.blob();
      const reader = new FileReader();
      reader.readAsDataURL(blob);
      reader.onloadend = async () => {
        const base64data = reader.result.split(',')[1];
        await FileSystem.writeAsStringAsync(destino, base64data, {
          encoding: FileSystem.EncodingType.Base64,
        });
        const puedeCompartir = await Sharing.isAvailableAsync();
        if (puedeCompartir) {
          await Sharing.shareAsync(destino, {
            mimeType: 'application/pdf',
            dialogTitle: `PDF ${ticket?.ticket_codigo || ticketId}`,
            UTI: 'com.adobe.pdf',
          });
        } else {
          Linking.openURL(destino);
        }
      };
    } catch (e) {
      toast('Error al descargar PDF: ' + e.message, 'error');
    }
  };

  // ── Vista para ticket ENTREGADO ──────────────────────────────────────────
  if (isEntregado) {
    return (
      <View style={styles.section}>
        {/* Info de entrega */}
        <View style={{ backgroundColor: '#f0fdf4', borderRadius: 12, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: '#86efac' }}>
          <Text style={{ color: '#166534', fontWeight: '700', fontSize: 15, marginBottom: 10 }}>✓ Ticket Entregado</Text>
          {ticket?.confirmado_entrega_por && (
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}>
              <Text style={{ color: '#374151', fontSize: 13 }}>Confirmado por</Text>
              <Text style={{ color: '#374151', fontSize: 13, fontWeight: '600' }}>{ticket.confirmado_entrega_por}</Text>
            </View>
          )}
          {ticket?.fecha_entrega && (
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}>
              <Text style={{ color: '#374151', fontSize: 13 }}>Fecha entrega</Text>
              <Text style={{ color: '#374151', fontSize: 13, fontWeight: '600' }}>
                {new Date(ticket.fecha_entrega).toLocaleString('es-CO')}
              </Text>
            </View>
          )}
          {ticket?.metodo_pago_final && (
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}>
              <Text style={{ color: '#374151', fontSize: 13 }}>Método de pago</Text>
              <Text style={{ color: '#374151', fontSize: 13, fontWeight: '600' }}>{ticket.metodo_pago_final}</Text>
            </View>
          )}
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderTopWidth: 1, borderTopColor: '#d1fae5', marginTop: 4 }}>
            <Text style={{ color: '#166534', fontWeight: '700', fontSize: 15 }}>Total cobrado</Text>
            <Text style={{ color: '#166534', fontWeight: '700', fontSize: 15 }}>{fmt(totalServicio)}</Text>
          </View>
        </View>

        {/* Observaciones finales */}
        {ticket?.observaciones_finales && (
          <View style={{ backgroundColor: '#1C2B3A', borderRadius: 10, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)' }}>
            <Text style={{ color: '#94a3b8', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', marginBottom: 6 }}>Observaciones Finales</Text>
            <Text style={{ color: '#fff', fontSize: 14 }}>{ticket.observaciones_finales}</Text>
          </View>
        )}

        {/* Recomendaciones */}
        {ticket?.recomendaciones && (
          <View style={{ backgroundColor: '#1C2B3A', borderRadius: 10, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)' }}>
            <Text style={{ color: '#94a3b8', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', marginBottom: 6 }}>Recomendaciones</Text>
            <Text style={{ color: '#fff', fontSize: 14 }}>{ticket.recomendaciones}</Text>
          </View>
        )}

        {/* Próximo mantenimiento */}
        {ticket?.proximo_mantenimiento && (
          <View style={{ backgroundColor: '#1C2B3A', borderRadius: 10, padding: 12, marginBottom: 14, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)' }}>
            <Text style={{ color: '#94a3b8', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', marginBottom: 6 }}>Próximo Mantenimiento</Text>
            <Text style={{ color: '#D4920A', fontSize: 14, fontWeight: '600' }}>{ticket.proximo_mantenimiento}</Text>
          </View>
        )}

        {/* Botón PDF */}
        <TouchableOpacity style={styles.pdfBtn} onPress={handleDescargarPdf}>
          <Text style={styles.pdfBtnText}>📄 Descargar / Compartir PDF</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // ── Vista para ticket FINALIZADO (formulario de entrega) ─────────────────
  const handleEntregar = async () => {
    if (!confirmadoPor.trim()) {
      toast('Ingresa quien confirma la entrega', 'warning');
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
                metodo_pago_final: metodoPago,
              });
              toast('Ticket entregado y cobrado', 'success');
              onSuccess();
            } catch (e) {
              toast(e.message, 'error');
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
        <Text style={styles.entregaTitle}>Registrar Entrega al Cliente</Text>
        <Text style={styles.entregaSubtitle}>Completa los datos para finalizar la entrega del vehículo</Text>
      </View>

      {/* Desglose de cobros */}
      {totalServicio > 0 && (
        <View style={{ backgroundColor: '#f0fdf4', borderRadius: 10, padding: 12, marginBottom: 16, borderWidth: 1, borderColor: '#86efac' }}>
          {cobros.map((c, i) => (
            <View key={i} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: '#d1fae5' }}>
              <Text style={{ color: '#374151', fontSize: 13 }}>{c.concepto}</Text>
              <Text style={{ color: '#374151', fontSize: 13 }}>{fmt(c.valor)}</Text>
            </View>
          ))}
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#d1fae5' }}>
            <Text style={{ color: '#374151', fontWeight: '600' }}>Total del servicio</Text>
            <Text style={{ color: '#374151', fontWeight: '600' }}>{fmt(totalServicio)}</Text>
          </View>
          {anticipo > 0 && (
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#d1fae5' }}>
              <Text style={{ color: '#16a34a' }}>— Anticipo recibido</Text>
              <Text style={{ color: '#16a34a' }}>-{fmt(anticipo)}</Text>
            </View>
          )}
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8 }}>
            <Text style={{ color: '#166534', fontWeight: '700', fontSize: 16 }}>Total a Cobrar</Text>
            <Text style={{ color: '#166534', fontWeight: '700', fontSize: 16 }}>{fmt(totalCobrar)}</Text>
          </View>
        </View>
      )}

      <Text style={styles.fieldLabel}>Confirmado por *</Text>
      <TextInput
        style={styles.fieldInput}
        placeholder="Nombre de quien recibe el vehículo"
        placeholderTextColor={colors.textMuted}
        value={confirmadoPor}
        onChangeText={setConfirmadoPor}
      />

      <Text style={styles.fieldLabel}>Método de Pago *</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {METODOS.map((m) => (
          <TouchableOpacity
            key={m}
            onPress={() => setMetodoPago(m)}
            style={{
              paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20,
              backgroundColor: metodoPago === m ? '#166534' : '#e5e7eb',
            }}
          >
            <Text style={{ color: metodoPago === m ? '#fff' : '#374151', fontSize: 13, fontWeight: '600' }}>{m}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity
        style={[styles.entregaBtn, loading && styles.btnDisabled]}
        onPress={handleEntregar}
        disabled={loading}
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.entregaBtnText}>Entregar y Cobrar</Text>
        }
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.pdfBtn}
        onPress={handleDescargarPdf}
      >
        <Text style={styles.pdfBtnText}>📄 Descargar / Compartir PDF</Text>
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
  container: { flex: 1, backgroundColor: '#0A1017' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0A1017' },
  ticketHeader: { backgroundColor: '#0F1923', padding: 16 },
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
    backgroundColor: '#1C2B3A',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  tabsScroll: {
    backgroundColor: '#1C2B3A',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
    maxHeight: 46,
  },
  tabs: { flexDirection: 'row' },
  tabsRow2: { borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.1)' },
  tab: { flex: 1, paddingVertical: 9, paddingHorizontal: 4, alignItems: 'center' },
  tabRow2: { flex: 1 },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#D4920A' },
  tabText: { fontSize: 11, color: '#94a3b8', fontWeight: '500', textAlign: 'center' },
  tabTextActive: { color: '#D4920A', fontWeight: '700' },
  content: { flex: 1 },
  contentWrapper: { flex: 1, overflow: 'hidden' },
  section: { padding: 16 },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  infoLabel: { fontSize: 13, color: '#94a3b8', flex: 1 },
  infoValue: { fontSize: 13, color: '#fff', fontWeight: '600', flex: 2, textAlign: 'right' },
  addBtn: {
    backgroundColor: '#D4920A',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    marginBottom: 14,
  },
  addBtnText: { color: '#0A1017', fontWeight: '700', fontSize: 14 },
  itemCard: {
    backgroundColor: '#1C2B3A',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  deleteBtn: {
    position: 'absolute', top: 6, right: 6, zIndex: 10,
    backgroundColor: 'rgba(239,68,68,0.85)',
    borderRadius: 10,
    width: 22, height: 22,
    justifyContent: 'center', alignItems: 'center',
  },
  deleteBtnText: { color: '#fff', fontWeight: '700', fontSize: 11, lineHeight: 13 },
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
  egresoHint: { fontSize: 11, color: colors.textMuted, textAlign: 'center', marginTop: 6, fontStyle: 'italic' },
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
  quickChip: { backgroundColor: colors.primaryLight, borderRadius: 16, paddingHorizontal: 12, paddingVertical: 6 },
  quickChipText: { color: '#fff', fontSize: 12, fontWeight: '600' },
});
