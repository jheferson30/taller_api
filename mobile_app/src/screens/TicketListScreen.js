import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  RefreshControl, ActivityIndicator, TextInput,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api';
import { colors, estadoConfig } from '../theme';

export default function TicketListScreen({ route, navigation }) {
  const { estado = null, titulo = 'Tickets' } = route.params || {};
  const [tickets, setTickets] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [error, setError] = useState(null);

  const loadTickets = async () => {
    try {
      setError(null);
      const data = await api.getTickets(estado);
      setTickets(data);
      setFiltered(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => {
    navigation.setOptions({ title: titulo });
    loadTickets();
  }, [estado]));

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(
      tickets.filter(
        (t) =>
          t.placa.toLowerCase().includes(q) ||
          t.ticket_codigo.toLowerCase().includes(q) ||
          (t.nombre_propietario || '').toLowerCase().includes(q)
      )
    );
  }, [search, tickets]);

  const onRefresh = () => { setRefreshing(true); loadTickets(); };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={loadTickets}>
          <Text style={styles.retryText}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.searchInput}
        placeholder="Buscar por placa, código o propietario..."
        value={search}
        onChangeText={setSearch}
        placeholderTextColor={colors.textMuted}
      />
      <FlatList
        data={filtered}
        keyExtractor={(item) => String(item.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={filtered.length === 0 ? styles.emptyContainer : { padding: 12 }}
        ListEmptyComponent={
          <View style={styles.center}>
            <Text style={styles.emptyText}>No hay tickets</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TicketCard
            ticket={item}
            onPress={() => navigation.navigate('TicketDetail', { ticketId: item.id })}
          />
        )}
      />
    </View>
  );
}

function TicketCard({ ticket, onPress }) {
  const cfg = estadoConfig[ticket.estado] || estadoConfig.ABIERTO;
  const fecha = new Date(ticket.fecha_ingreso).toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.cardTop}>
        <Text style={styles.placa}>{ticket.placa}</Text>
        <View style={[styles.badge, { backgroundColor: cfg.bg }]}>
          <Text style={[styles.badgeText, { color: cfg.text }]}>{cfg.label}</Text>
        </View>
      </View>
      <Text style={styles.codigo}>{ticket.ticket_codigo}</Text>
      <Text style={styles.motivo} numberOfLines={1}>{ticket.motivo_visita}</Text>
      <View style={styles.cardBottom}>
        <Text style={styles.meta}>{ticket.nombre_propietario || 'Sin propietario'}</Text>
        <Text style={styles.meta}>{fecha}</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  searchInput: {
    margin: 12,
    backgroundColor: colors.surface,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.text,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
    elevation: 2,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 4,
  },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  placa: { fontSize: 18, fontWeight: 'bold', color: colors.text, letterSpacing: 1 },
  badge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 20 },
  badgeText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  codigo: { fontSize: 12, color: colors.textMuted, marginBottom: 4 },
  motivo: { fontSize: 14, color: colors.text, marginBottom: 8 },
  cardBottom: { flexDirection: 'row', justifyContent: 'space-between' },
  meta: { fontSize: 12, color: colors.textMuted },
  errorText: { color: colors.error, marginBottom: 16, textAlign: 'center' },
  retryBtn: { backgroundColor: colors.primary, paddingHorizontal: 24, paddingVertical: 10, borderRadius: 8 },
  retryText: { color: '#fff', fontWeight: '700' },
  emptyText: { color: colors.textMuted, fontSize: 16 },
});
