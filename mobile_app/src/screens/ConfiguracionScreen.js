import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator, ScrollView,
} from 'react-native';
import { getServerIp, getAdminPassword, saveServerIp, saveAdminPassword, getApiBaseUrl } from '../config';
import { colors } from '../theme';

export default function ConfiguracionScreen({ navigation, route }) {
  const [ip, setIp] = useState('');
  const [password, setPassword] = useState('');
  const [probando, setProbando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const esPrimeraVez = route?.params?.primeraVez === true;

  useEffect(() => {
    (async () => {
      const [savedIp, savedPwd] = await Promise.all([getServerIp(), getAdminPassword()]);
      setIp(savedIp);
      setPassword(savedPwd);
    })();
  }, []);

  const probarConexion = async () => {
    if (!ip.trim()) {
      Alert.alert('Error', 'Ingresa una IP válida');
      return;
    }
    setProbando(true);
    try {
      const url = `http://${ip.trim()}:8000/api/mobile/estadisticas`;
      const response = await fetch(url, {
        headers: { 'X-Admin-Password': password },
      });
      if (response.ok) {
        await saveServerIp(ip.trim());
        await saveAdminPassword(password);
        Alert.alert('Conexión exitosa', 'IP y contraseña guardadas correctamente.', [
          { text: 'OK', onPress: () => esPrimeraVez && navigation.replace('Main') },
        ]);
      } else if (response.status === 401 || response.status === 403) {
        Alert.alert('Contraseña incorrecta', 'La IP es correcta pero la contraseña no coincide.');
      } else {
        Alert.alert('Error', `El servidor respondió con código ${response.status}`);
      }
    } catch {
      Alert.alert('Sin conexión', 'No se pudo conectar. Verifica que la IP sea correcta y que el servidor esté encendido.');
    } finally {
      setProbando(false);
    }
  };

  const guardarSinProbar = async () => {
    if (!ip.trim()) {
      Alert.alert('Error', 'Ingresa una IP válida');
      return;
    }
    setGuardando(true);
    try {
      await saveServerIp(ip.trim());
      await saveAdminPassword(password);
      Alert.alert('Guardado', 'Configuración guardada.', [
        { text: 'OK', onPress: () => esPrimeraVez && navigation.replace('Main') },
      ]);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.card}>
        <Text style={styles.title}>Configuración del Servidor</Text>

        {esPrimeraVez && (
          <View style={styles.welcomeBanner}>
            <Text style={styles.welcomeText}>Bienvenido. Ingresa la IP del servidor para comenzar.</Text>
          </View>
        )}

        <Text style={styles.subtitle}>
          Ingresa la IP de la PC donde está instalado el sistema del taller.
          {'\n'}(Ejecuta ipconfig en esa PC para verla)
        </Text>

        <Text style={styles.label}>IP del Servidor</Text>
        <View style={styles.inputRow}>
          <Text style={styles.prefix}>http://</Text>
          <TextInput
            style={styles.input}
            value={ip}
            onChangeText={setIp}
            placeholder="192.168.1.100"
            placeholderTextColor={colors.textMuted}
            keyboardType="numeric"
            autoCapitalize="none"
          />
          <Text style={styles.suffix}>:8000</Text>
        </View>

        <Text style={styles.label}>Contraseña de Administrador</Text>
        <TextInput
          style={[styles.input, styles.inputFull]}
          value={password}
          onChangeText={setPassword}
          placeholder="Contraseña"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
          autoCapitalize="none"
        />

        <TouchableOpacity
          style={[styles.btnPrimary, probando && styles.btnDisabled]}
          onPress={probarConexion}
          disabled={probando || guardando}
        >
          {probando
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.btnText}>Probar y Guardar</Text>
          }
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.btnSecondary, guardando && styles.btnDisabled]}
          onPress={guardarSinProbar}
          disabled={probando || guardando}
        >
          {guardando
            ? <ActivityIndicator color={colors.textMuted} />
            : <Text style={styles.btnSecondaryText}>Guardar sin probar</Text>
          }
        </TouchableOpacity>
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>¿Cómo encontrar la IP?</Text>
        <Text style={styles.infoText}>1. En la PC del taller, abre la terminal</Text>
        <Text style={styles.infoText}>2. Escribe: ipconfig</Text>
        <Text style={styles.infoText}>3. Busca "Dirección IPv4"</Text>
        <Text style={styles.infoText}>4. Ejemplo: 192.168.1.50</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: 20 },
  card: {
    backgroundColor: colors.surface, borderRadius: 12,
    padding: 20, borderWidth: 1, borderColor: colors.border,
  },
  title: { fontSize: 18, fontWeight: '700', color: colors.text, marginBottom: 8 },
  subtitle: { fontSize: 13, color: colors.textMuted, marginBottom: 20, lineHeight: 20 },
  label: { fontSize: 12, fontWeight: '600', color: colors.textMuted, marginBottom: 8, textTransform: 'uppercase' },
  inputRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  prefix: { fontSize: 14, color: colors.textMuted, marginRight: 4 },
  suffix: { fontSize: 14, color: colors.textMuted, marginLeft: 4 },
  input: {
    flex: 1, backgroundColor: colors.background, borderWidth: 1,
    borderColor: colors.border, borderRadius: 8, paddingHorizontal: 12,
    paddingVertical: 10, fontSize: 16, color: colors.text, textAlign: 'center',
  },
  inputFull: {
    flex: 0, width: '100%', marginBottom: 20, textAlign: 'left',
  },
  btnPrimary: {
    backgroundColor: colors.primary, borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginBottom: 10,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  btnSecondary: { paddingVertical: 12, alignItems: 'center' },
  btnSecondaryText: { color: colors.textMuted, fontSize: 14 },
  infoCard: {
    backgroundColor: colors.surface, borderRadius: 12, padding: 16,
    borderWidth: 1, borderColor: colors.border, marginTop: 16,
  },
  infoTitle: { fontSize: 14, fontWeight: '700', color: colors.text, marginBottom: 10 },
  infoText: { fontSize: 13, color: colors.textMuted, marginBottom: 4 },
  welcomeBanner: {
    backgroundColor: '#dbeafe', borderRadius: 8, padding: 12, marginBottom: 16,
    borderLeftWidth: 4, borderLeftColor: '#1e40af',
  },
  welcomeText: { fontSize: 13, color: '#1e40af', fontWeight: '600' },
});
