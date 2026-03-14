export const colors = {
  primary: '#1e40af',
  primaryDark: '#1e3a8a',
  primaryLight: '#3b82f6',
  background: '#f8fafc',
  surface: '#ffffff',
  text: '#0f172a',
  textMuted: '#64748b',
  border: '#e2e8f0',
  success: '#059669',
  error: '#dc2626',
  warning: '#f59e0b',

  // Estados de tickets
  estadoAbierto: '#dbeafe',
  estadoAbiertoText: '#1e40af',
  estadoEnProceso: '#fef3c7',
  estadoEnProcesoText: '#92400e',
  estadoFinalizado: '#d1fae5',
  estadoFinalizadoText: '#065f46',
  estadoEntregado: '#e0e7ff',
  estadoEntregadoText: '#3730a3',
};

export const estadoConfig = {
  ABIERTO:     { bg: colors.estadoAbierto,    text: colors.estadoAbiertoText,    label: 'Abierto' },
  EN_PROCESO:  { bg: colors.estadoEnProceso,  text: colors.estadoEnProcesoText,  label: 'En Proceso' },
  FINALIZADO:  { bg: colors.estadoFinalizado, text: colors.estadoFinalizadoText, label: 'Finalizado' },
  ENTREGADO:   { bg: colors.estadoEntregado,  text: colors.estadoEntregadoText,  label: 'Entregado' },
};
