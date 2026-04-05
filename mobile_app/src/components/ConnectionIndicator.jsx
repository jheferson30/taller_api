import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useOffline } from '../hooks/useOffline';

/**
 * Indicador visual de estado de conexión y operaciones pendientes
 */
export function ConnectionIndicator() {
  const { isOnline, isSyncing, pendingCount } = useOffline();

  if (isOnline && pendingCount === 0) {
    return null; // No mostrar nada si está online y no hay operaciones pendientes
  }

  return (
    <View style={styles.container}>
      <View style={[styles.indicator, isOnline ? styles.online : styles.offline]}>
        <Text style={styles.dot}>{isOnline ? '●' : '○'}</Text>
        <Text style={styles.text}>
          {isSyncing ? 'Sincronizando...' : isOnline ? 'En línea' : 'Sin conexión'}
        </Text>
        {pendingCount > 0 && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{pendingCount}</Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 1000,
    alignItems: 'center',
    paddingTop: 8,
  },
  indicator: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  online: {
    backgroundColor: '#10b981',
  },
  offline: {
    backgroundColor: '#ef4444',
  },
  dot: {
    fontSize: 12,
    color: '#fff',
    marginRight: 6,
  },
  text: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  badge: {
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginLeft: 8,
    minWidth: 20,
    alignItems: 'center',
  },
  badgeText: {
    color: '#ef4444',
    fontSize: 10,
    fontWeight: 'bold',
  },
});
