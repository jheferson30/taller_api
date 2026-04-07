import React, { createContext, useContext, useState, useRef, useCallback } from 'react';
import { View, Text, StyleSheet, Animated, TouchableOpacity } from 'react-native';

const ToastContext = createContext(null);

const ICONS = { success: 'OK', error: 'X', info: 'i', warning: '!' };
const COLORS = {
  success: { bg: '#14532d', border: '#22c55e', text: '#86efac', icon: '#22c55e' },
  error:   { bg: '#450a0a', border: '#ef4444', text: '#fca5a5', icon: '#ef4444' },
  info:    { bg: '#0c1a3a', border: '#0F1923', text: '#93c5fd', icon: '#0F1923' },
  warning: { bg: '#431407', border: '#f97316', text: '#fdba74', icon: '#f97316' },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);

  const show = useCallback((message, type, duration) => {
    const t = type || 'info';
    const d = duration || 2500;
    const id = ++idRef.current;
    setToasts(function(prev) { return [...prev, { id: id, message: message, type: t }]; });
    setTimeout(function() {
      setToasts(function(prev) { return prev.filter(function(x) { return x.id !== id; }); });
    }, d);
  }, []);

  const dismiss = useCallback(function(id) {
    setToasts(function(prev) { return prev.filter(function(x) { return x.id !== id; }); });
  }, []);

  return React.createElement(
    ToastContext.Provider,
    { value: show },
    children,
    React.createElement(
      View,
      { style: styles.container, pointerEvents: 'box-none' },
      toasts.map(function(t) {
        return React.createElement(ToastItem, { key: t.id, toast: t, onDismiss: function() { dismiss(t.id); } });
      })
    )
  );
}

function ToastItem({ toast, onDismiss }) {
  const anim = useRef(new Animated.Value(0)).current;
  const c = COLORS[toast.type] || COLORS.info;

  React.useEffect(function() {
    Animated.spring(anim, { toValue: 1, useNativeDriver: true, tension: 80, friction: 10 }).start();
  }, []);

  return React.createElement(
    Animated.View,
    {
      style: [
        styles.toast,
        { backgroundColor: c.bg, borderLeftColor: c.border },
        {
          opacity: anim,
          transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [40, 0] }) }],
        },
      ],
    },
    React.createElement(
      TouchableOpacity,
      { style: styles.toastInner, onPress: onDismiss, activeOpacity: 0.8 },
      React.createElement(
        View,
        { style: [styles.iconBox, { backgroundColor: c.border + '33' }] },
        React.createElement(Text, { style: [styles.icon, { color: c.icon }] }, ICONS[toast.type])
      ),
      React.createElement(Text, { style: [styles.msg, { color: c.text }] }, toast.message)
    )
  );
}

export function useToast() {
  var ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast debe usarse dentro de ToastProvider');
  return ctx;
}

var styles = StyleSheet.create({
  container: {
    position: 'absolute', bottom: 32, left: 16, right: 16,
    zIndex: 9999,
  },
  toast: {
    borderRadius: 12, borderLeftWidth: 4, marginTop: 8,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4, shadowRadius: 8, elevation: 8,
  },
  toastInner: {
    flexDirection: 'row', alignItems: 'center', padding: 14,
  },
  iconBox: {
    width: 32, height: 32, borderRadius: 16,
    alignItems: 'center', justifyContent: 'center', marginRight: 12,
  },
  icon: { fontSize: 13, fontWeight: 'bold' },
  msg: { flex: 1, fontSize: 14, lineHeight: 20 },
});