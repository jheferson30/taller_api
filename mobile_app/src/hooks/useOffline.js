import { useState, useEffect } from 'react';
import offlineService from '../services/offlineService';

/**
 * Hook personalizado para acceder al estado offline
 * Expone: isOnline, isSyncing, pendingCount
 */
export function useOffline() {
  const [state, setState] = useState({
    isOnline: true,
    isSyncing: false,
    pendingCount: 0,
  });

  useEffect(() => {
    // Obtener estado inicial
    setState(offlineService.getState());

    // Suscribirse a cambios
    const unsubscribe = offlineService.addListener((newState) => {
      setState(newState);
    });

    return unsubscribe;
  }, []);

  return state;
}
