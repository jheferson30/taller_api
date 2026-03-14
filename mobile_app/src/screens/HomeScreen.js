import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  ScrollView, RefreshControl, ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api';
import { colors } from '../theme';

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

  const loadStats = async () => {
    try {
      setError(null);
      const data = await api.getEstadisticas();
      setStats(data);
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
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🔧 Panel del Mecánico</Text>
        <Text style={styles.headerSub}>Toca un estado para ver los tickets</Text>
      </View>

      {/* KPI Cards */}
      <View style={styles.kpiGrid}>
        <KpiCard
          label="Abiertos"
          value={stats?.por_estado?.abiertos ?? 0}
          color="#1e40af"
          bg="#dbeafe"
          onPress={() => navigation.navigate('TicketList', { estado: 'ABIERTO', titulo: 'Tickets Abiertos' })}
        />
        <KpiCard
          label="En Proceso"
          value={stats?.por_estado?.en_proceso ?? 0}
          color="#92400e"
          bg="#fef3c7"
          onPress={() => navigation.navigate('TicketList', { estado: 'EN_PROCESO', titulo: 'En Proceso' })}
        />
        <KpiCard
          label="Finalizados"
          value={stats?.por_estado?.finalizados ?? 0}
          color="#065f46"
          bg="#d1fae5"
          onPress={() => navigation.navigate('TicketList', { estado: 'FINALIZADO', titulo: 'Finalizados' })}
        />
        <KpiCard
          label="Entregados"
          value={stats?.por_estado?.entregados ?? 0}
          color="#3730a3"
          bg="#e0e7ff"
          onPress={() => navigation.navigate('TicketList', { estado: 'ENTREGADO', titulo: 'Entregados' })}
        />
      </View>

      {/* Accesos rápidos */}
      <Text style={styles.sectionTitle}>Acceso Rápido</Text>
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
  );
}

function KpiCard({ label, value, color, bg, onPress }) {
  return (
    <TouchableOpacity style={[styles.kpiCard, { backgroundColor: bg }]} onPress={onPress}>
      <Text style={[styles.kpiValue, { color }]}>{value}</Text>
      <Text style={[styles.kpiLabel, { color }]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, backgroundColor: colors.background },
  header: {
    backgroundColor: colors.primary,
    padding: 24,
    paddingTop: 32,
  },
  headerTitle: { color: '#fff', fontSize: 22, fontWeight: 'bold' },
  headerSub: { color: 'rgba(255,255,255,0.8)', fontSize: 13, marginTop: 4 },
  kpiGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 12,
    gap: 10,
  },
  kpiCard: {
    width: '47%',
    borderRadius: 14,
    padding: 18,
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 6,
  },
  kpiValue: { fontSize: 36, fontWeight: 'bold' },
  kpiLabel: { fontSize: 13, fontWeight: '600', marginTop: 4 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.text,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 8,
  },
  quickBtn: {
    backgroundColor: colors.surface,
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    elevation: 1,
  },
  quickBtnText: { fontSize: 15, color: colors.text, fontWeight: '500' },
  quickBtnArrow: { fontSize: 22, color: colors.textMuted },
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
