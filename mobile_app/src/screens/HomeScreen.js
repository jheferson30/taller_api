import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  ScrollView, RefreshControl, ActivityIndicator, StatusBar,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api';
import { colors } from '../theme';
import authService from '../services/authService';

const FILTROS = [
  { label: 'Todos', value: null },
  { label: 'Abiertos', value: 'ABIERTO' },
  { label: 'En Proceso', value: 'EN_PROCESO' },
  { label: 'Finalizados', value: 'FINALIZADO' },
];

export default function HomeScreen({ navigation }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);

  // Mapeo de roles del backend a español
  const getRoleName = (roles) => {
    console.log('Roles recibidos:', roles);
    if (!roles || roles.length === 0) return 'Usuario';
    // Los roles vienen como array de strings directamente: ["MECANICO", "ADMIN"]
    console.log('Primer rol:', roles[0]);
    if (roles.includes('ADMIN')) return 'Administrador';
    if (roles.includes('MECANICO')) return 'Mecánico';
    if (roles.includes('RECEPCIONISTA')) return 'Recepcionista';
    return 'Usuario';
  };

  const loadStats = async () => {
    try {
      setError(null);
      const [data, currentUser] = await Promise.all([
        api.getEstadisticas(),
        authService.getUser()
      ]);
      console.log('Usuario cargado:', currentUser);
      setStats(data);
      setUser(currentUser);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { loadStats(); }, []));

  const onRefresh = () => { setRefreshing(true); loadStats(); };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Conectando al servidor...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorIcon}>⚠️</Text>
        <Text style={styles.errorTitle}>Sin conexión</Text>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={loadStats}>
          <Text style={styles.retryText}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor="#0F1923" />
      <ScrollView
        style={styles.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTop}>{getRoleName(user?.roles)}</Text>
        <View style={styles.headerTitleRow}>
          <Text style={styles.headerTitleWhite}>Panel </Text>
          <Text style={styles.headerTitleAmber}>{getRoleName(user?.roles)}</Text>
        </View>
      </View>

      {/* KPI Cards */}
      <View style={styles.kpiGrid}>
        <KpiCard
          label="Abiertos"
          value={stats?.por_estado?.abiertos ?? 0}
          isEnProceso={false}
          onPress={() => navigation.navigate('TicketList', { estado: 'ABIERTO', titulo: 'Tickets Abiertos' })}
        />
        <KpiCard
          label="En Proceso"
          value={stats?.por_estado?.en_proceso ?? 0}
          isEnProceso={true}
          onPress={() => navigation.navigate('TicketList', { estado: 'EN_PROCESO', titulo: 'En Proceso' })}
        />
        <KpiCard
          label="Finalizados"
          value={stats?.por_estado?.finalizados ?? 0}
          isEnProceso={false}
          onPress={() => navigation.navigate('TicketList', { estado: 'FINALIZADO', titulo: 'Finalizados' })}
        />
        <KpiCard
          label="Entregados"
          value={stats?.por_estado?.entregados ?? 0}
          isEnProceso={false}
          onPress={() => navigation.navigate('TicketList', { estado: 'ENTREGADO', titulo: 'Entregados' })}
        />
      </View>

      {/* Accesos rápidos */}
      <Text style={styles.sectionTitle}>Acceso Rápido</Text>

      <TouchableOpacity
        style={styles.quickBtn}
        onPress={() => navigation.navigate('Recepcion', {})}
      >
        <Text style={styles.quickBtnText}><Text style={{ color: '#D4920A' }}>›</Text> Recepción de Vehículos</Text>
        <Text style={styles.quickBtnArrow}>›</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.quickBtn}
        onPress={() => navigation.navigate('CobroRapido', {})}
      >
        <Text style={styles.quickBtnText}><Text style={{ color: '#D4920A' }}>›</Text> Cobro Rápido</Text>
        <Text style={styles.quickBtnArrow}>›</Text>
      </TouchableOpacity>

      {FILTROS.map((f) => (
        <TouchableOpacity
          key={f.label}
          style={styles.quickBtn}
          onPress={() => navigation.navigate('TicketList', { estado: f.value, titulo: f.label })}
        >
          <Text style={styles.quickBtnText}>{f.label}</Text>
          <Text style={styles.quickBtnArrow}>›</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
    </>
  );
}

function KpiCard({ label, value, isEnProceso, onPress }) {
  return (
    <TouchableOpacity style={styles.kpiCard} onPress={onPress}>
      <Text style={[styles.kpiValue, isEnProceso && { color: '#D4920A' }]}>{value}</Text>
      <Text style={styles.kpiLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A1017' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, backgroundColor: '#0A1017' },
  header: {
    backgroundColor: colors.primary,
    padding: 24,
    paddingTop: 32,
  },
  headerTitle: { color: '#fff', fontSize: 22, fontWeight: 'bold' },
  headerTop: { color: '#fff', fontSize: 14, marginBottom: 8, opacity: 0.9 },
  headerTitleRow: { flexDirection: 'row', alignItems: 'center' },
  headerTitleWhite: { color: '#fff', fontSize: 28, fontWeight: 'bold' },
  headerTitleAmber: { color: '#D4920A', fontSize: 28, fontWeight: 'bold' },
  headerSub: { color: 'rgba(255,255,255,0.8)', fontSize: 13, marginTop: 4 },
  kpiGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 12,
    gap: 10,
  },
  kpiCard: {
    width: '47%',
    backgroundColor: '#1C2B3A',
    borderRadius: 12,
    padding: 18,
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 6,
  },
  kpiValue: { fontSize: 32, fontWeight: '700', color: '#FFFFFF' },
  kpiLabel: { fontSize: 13, fontWeight: '600', marginTop: 4, color: 'rgba(255,255,255,0.5)' },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 8,
  },
  quickBtn: {
    backgroundColor: '#1C2B3A',
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.07)',
    elevation: 1,
  },
  quickBtnText: { fontSize: 15, color: '#fff', fontWeight: '500' },
  quickBtnArrow: { fontSize: 22, color: '#D4920A' },
  quickBtnDestacado: { backgroundColor: '#1C2B3A', borderColor: 'rgba(255,255,255,0.07)' },
  loadingText: { marginTop: 12, color: colors.textMuted, fontSize: 14 },
  errorIcon: { fontSize: 48, marginBottom: 12 },
  errorTitle: { fontSize: 18, fontWeight: 'bold', color: colors.text, marginBottom: 8 },
  errorText: { fontSize: 13, color: colors.textMuted, textAlign: 'center', marginBottom: 20 },
  retryBtn: {
    backgroundColor: colors.primary,
    paddingHorizontal: 28,
    paddingVertical: 12,
    borderRadius: 10,
  },
  retryText: { color: '#fff', fontWeight: '700', fontSize: 15 },
});
