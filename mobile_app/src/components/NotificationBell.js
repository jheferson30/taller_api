import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  FlatList,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../api';
import { colors } from '../theme';
import { useToast } from './Toast';

const POLL_INTERVAL_MS = 30000; // 30 segundos

export default function NotificationBell() {
  const [total, setTotal] = useState(0);
  const [notificaciones, setNotificaciones] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [marcando, setMarcando] = useState(null);
  const toast = useToast();

  const fetchNoLeidas = useCallback(async () => {
    try {
      const data = await api.getNotificacionesNoLeidas();
      setTotal(data?.total ?? 0);
      setNotificaciones(data?.notificaciones ?? []);
    } catch (error) {
      // Silencioso - no mostrar error en polling
      console.log('Error al obtener notificaciones:', error.message);
    }
  }, []);

  const fetchTodas = useCallback(async () => {
    setLoading(true);
    try {
      // Obtener conteo de no leídas
      const dataNoLeidas = await api.getNotificacionesNoLeidas();
      setTotal(dataNoLeidas?.total ?? 0);

      // Obtener todas las notificaciones
      const dataTodas = await api.getNotificacionesTodas();
      setNotificaciones(dataTodas?.notificaciones ?? []);
    } catch (error) {
      toast('Error al cargar notificaciones', 'error');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  // Polling cada 30 segundos
  useEffect(() => {
    fetchNoLeidas();
    const interval = setInterval(fetchNoLeidas, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchNoLeidas]);

  const marcarLeida = async (id) => {
    setMarcando(id);
    try {
      await api.marcarNotificacionLeida(id);
      
      // Actualizar estado local
      setNotificaciones(prev =>
        prev.map(n => (n.id === id ? { ...n, leida: true } : n))
      );
      setTotal(prev => Math.max(0, prev - 1));
    } catch (error) {
      toast('Error al marcar como leída', 'error');
    } finally {
      setMarcando(null);
    }
  };

  const marcarTodasLeidas = async () => {
    setMarcando('all');
    try {
      await api.marcarTodasNotificacionesLeidas();
      
      // Actualizar estado local
      setNotificaciones(prev => prev.map(n => ({ ...n, leida: true })));
      setTotal(0);
      
      toast('Todas marcadas como leídas', 'success');
    } catch (error) {
      toast('Error al marcar todas como leídas', 'error');
    } finally {
      setMarcando(null);
    }
  };

  const handleOpenModal = () => {
    setModalVisible(true);
    fetchTodas();
  };

  const formatFecha = (fechaStr) => {
    const d = new Date(fechaStr);
    const ahora = new Date();
    const diffMs = ahora - d;
    const diffMin = Math.floor(diffMs / 60000);
    
    if (diffMin < 1) return 'ahora';
    if (diffMin < 60) return `hace ${diffMin} min`;
    
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `hace ${diffH}h`;
    
    const diffD = Math.floor(diffH / 24);
    if (diffD < 7) return `hace ${diffD}d`;
    
    return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
  };

  const getIcono = (tipo) => {
    switch (tipo) {
      case 'TICKET_ASIGNADO':
        return 'construct-outline';
      case 'RENOVACION_PLAN':
        return 'alert-circle-outline';
      case 'LIMITE_PLAN':
        return 'warning-outline';
      case 'VENCIMIENTO':
        return 'time-outline';
      case 'SEGURIDAD':
        return 'shield-outline';
      default:
        return 'notifications-outline';
    }
  };

  // Filtrar notificaciones de tipo RENOVACION_PLAN (tienen su propio banner)
  const notifDropdown = notificaciones.filter(n => n.tipo !== 'RENOVACION_PLAN');

  const renderNotificacion = ({ item }) => (
    <View
      style={[
        styles.notifItem,
        !item.leida && styles.notifItemNoLeida,
      ]}
    >
      {/* Punto azul para no leídas */}
      {!item.leida && <View style={styles.puntoAzul} />}

      {/* Ícono */}
      <Ionicons
        name={getIcono(item.tipo)}
        size={24}
        color={item.leida ? colors.textMuted : colors.primary}
        style={styles.notifIcon}
      />

      {/* Contenido */}
      <View style={styles.notifContent}>
        <Text style={[styles.notifTitulo, !item.leida && styles.notifTituloNoLeida]}>
          {item.titulo}
        </Text>
        <Text style={styles.notifMensaje} numberOfLines={2}>
          {item.mensaje}
        </Text>
        <Text style={styles.notifFecha}>{formatFecha(item.fecha_creacion)}</Text>
      </View>

      {/* Botón marcar leída */}
      {!item.leida && (
        <TouchableOpacity
          onPress={() => marcarLeida(item.id)}
          disabled={marcando === item.id}
          style={styles.btnMarcarLeida}
        >
          {marcando === item.id ? (
            <ActivityIndicator size="small" color={colors.primary} />
          ) : (
            <Ionicons name="checkmark" size={18} color={colors.primary} />
          )}
        </TouchableOpacity>
      )}
    </View>
  );

  return (
    <>
      {/* Botón campana */}
      <TouchableOpacity
        onPress={handleOpenModal}
        style={styles.bellButton}
        accessibilityLabel={
          total > 0 ? `${total} notificaciones no leídas` : 'Sin notificaciones'
        }
      >
        <Ionicons name="notifications-outline" size={24} color="#fff" />
        {total > 0 && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{total > 99 ? '99+' : total}</Text>
          </View>
        )}
      </TouchableOpacity>

      {/* Modal de notificaciones */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {/* Header */}
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                Notificaciones
                {notifDropdown.length > 0 && (
                  <Text style={styles.modalCount}> ({notifDropdown.length})</Text>
                )}
              </Text>
              <View style={styles.headerButtons}>
                {total > 0 && (
                  <TouchableOpacity
                    onPress={marcarTodasLeidas}
                    disabled={marcando === 'all'}
                    style={styles.btnLeerTodas}
                  >
                    {marcando === 'all' ? (
                      <ActivityIndicator size="small" color={colors.primary} />
                    ) : (
                      <>
                        <Ionicons name="checkmark-done" size={16} color={colors.primary} />
                        <Text style={styles.btnLeerTodasText}>Leer todas</Text>
                      </>
                    )}
                  </TouchableOpacity>
                )}
                <TouchableOpacity
                  onPress={() => setModalVisible(false)}
                  style={styles.btnCerrar}
                >
                  <Ionicons name="close" size={24} color="#fff" />
                </TouchableOpacity>
              </View>
            </View>

            {/* Lista */}
            {loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={colors.primary} />
              </View>
            ) : notifDropdown.length === 0 ? (
              <View style={styles.emptyContainer}>
                <Ionicons name="notifications-off-outline" size={48} color={colors.textMuted} />
                <Text style={styles.emptyText}>Sin notificaciones pendientes</Text>
              </View>
            ) : (
              <FlatList
                data={notifDropdown}
                renderItem={renderNotificacion}
                keyExtractor={(item) => item.id.toString()}
                style={styles.lista}
                contentContainerStyle={styles.listaContent}
              />
            )}
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  bellButton: {
    position: 'relative',
    padding: 8,
  },
  badge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: '#ef4444',
    borderRadius: 10,
    minWidth: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1C2B3A',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
    minHeight: '50%',
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  modalCount: {
    fontSize: 16,
    fontWeight: '400',
    color: colors.textMuted,
  },
  headerButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  btnLeerTodas: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  btnLeerTodasText: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: '600',
  },
  btnCerrar: {
    padding: 4,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 14,
    marginTop: 12,
  },
  lista: {
    flex: 1,
  },
  listaContent: {
    paddingBottom: 16,
  },
  notifItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
    backgroundColor: '#0f172a',
  },
  notifItemNoLeida: {
    backgroundColor: '#1e3a5f',
  },
  puntoAzul: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#3b82f6',
    marginTop: 8,
    marginRight: 8,
  },
  notifIcon: {
    marginRight: 12,
    marginTop: 2,
  },
  notifContent: {
    flex: 1,
  },
  notifTitulo: {
    fontSize: 14,
    color: '#f1f5f9',
    marginBottom: 4,
  },
  notifTituloNoLeida: {
    fontWeight: '600',
  },
  notifMensaje: {
    fontSize: 13,
    color: colors.textMuted,
    lineHeight: 18,
    marginBottom: 4,
  },
  notifFecha: {
    fontSize: 11,
    color: '#475569',
  },
  btnMarcarLeida: {
    padding: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    marginLeft: 8,
  },
});
