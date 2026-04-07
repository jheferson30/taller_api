// Canal de eventos para manejar sesión expirada desde cualquier parte de la app
const listeners = [];

export const sessionEvents = {
  onSessionExpired(callback) {
    listeners.push(callback);
    return () => {
      const idx = listeners.indexOf(callback);
      if (idx > -1) listeners.splice(idx, 1);
    };
  },
  emitSessionExpired() {
    listeners.forEach(cb => cb());
  },
};
