import { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform, StatusBar, Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getServerIp } from '../config';
import authService from '../services/authService';

const SAVED_USERNAME_KEY = '@saved_username';
const REMEMBER_USER_KEY = '@remember_user';

export default function LoginScreen({ navigation, route }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [recordarUsuario, setRecordarUsuario] = useState(false);
  const [serverIp, setServerIp] = useState(null);
  const [checkingIp, setCheckingIp] = useState(true);

  const checkIp = async () => {
    setCheckingIp(true);
    const ip = await getServerIp();
    setServerIp(ip || null);
    setCheckingIp(false);
  };

  // Cargar usuario guardado al iniciar
  const loadSavedUsername = async () => {
    try {
      const [savedUser, rememberFlag] = await Promise.all([
        AsyncStorage.getItem(SAVED_USERNAME_KEY),
        AsyncStorage.getItem(REMEMBER_USER_KEY),
      ]);
      
      if (rememberFlag === 'true' && savedUser) {
        setUsername(savedUser);
        setRecordarUsuario(true);
      }
    } catch (err) {
      console.warn('Error cargando usuario guardado:', err);
    }
  };

  useEffect(() => { 
    checkIp(); 
    loadSavedUsername();
  }, []);

  useEffect(() => {
    const unsub = navigation.addListener('focus', checkIp);
    return unsub;
  }, [navigation]);

  const handleLogin = async () => {
    if (!username || !password) {
      setError('Por favor ingresa usuario y contraseña');
      return;
    }
    setLoading(true);
    setError('');
    try {
      // Guardar o eliminar solo el usuario según checkbox
      if (recordarUsuario) {
        await Promise.all([
          AsyncStorage.setItem(SAVED_USERNAME_KEY, username),
          AsyncStorage.setItem(REMEMBER_USER_KEY, 'true'),
        ]);
      } else {
        await Promise.all([
          AsyncStorage.removeItem(SAVED_USERNAME_KEY),
          AsyncStorage.removeItem(REMEMBER_USER_KEY),
        ]);
      }

      const data = await authService.login(username, password);
      const roles = data?.user?.roles || [];
      const returnTo = roles.includes('ADMIN') ? 'HomeAdmin' : (route.params?.returnTo || 'Home');
      navigation.replace(returnTo);
    } catch (err) {
      setError(err.message || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor="#0A1017" />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={s.container}>
      <TouchableOpacity style={s.settingsBtn} onPress={() => navigation.navigate('Configuracion', { primeraVez: false })}>
        <Ionicons name="settings-outline" size={24} color="#64748b" />
      </TouchableOpacity>

      <View style={s.content}>
        <View style={s.logoContainer}>
          <Image 
            source={require('../../assets/logo-login.png')} 
            style={s.logo}
            resizeMode="contain"
          />
        </View>
        <Text style={s.subtitle}>Iniciar Sesión</Text>

        {checkingIp && (
          <View style={s.banner}>
            <ActivityIndicator size="small" color="#fff" />
            <Text style={[s.bannerTxt, { marginTop: 6 }]}>Verificando conexion...</Text>
          </View>
        )}

        {!checkingIp && !serverIp && (
          <TouchableOpacity style={s.banner} onPress={() => navigation.navigate('Configuracion', { primeraVez: false })}>
            <Text style={s.bannerTxt}>Sin servidor configurado</Text>
            <Text style={s.bannerSub}>Toca aqui para configurar la IP</Text>
          </TouchableOpacity>
        )}

        <View style={s.form}>
          <TextInput
            style={s.input}
            placeholder="Usuario"
            placeholderTextColor="#64748b"
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            autoCorrect={false}
            editable={!loading}
          />

          <View style={s.inputRow}>
            <TextInput
              style={s.inputFlex}
              placeholder="Contraseña"
              placeholderTextColor="#64748b"
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!mostrarPassword}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
              onSubmitEditing={handleLogin}
            />
            <TouchableOpacity style={s.eyeBtn} onPress={() => setMostrarPassword(v => !v)}>
              <Ionicons name={mostrarPassword ? 'eye-off-outline' : 'eye-outline'} size={22} color="#64748b" />
            </TouchableOpacity>
          </View>

          {error ? <Text style={s.error}>{error}</Text> : null}

          <TouchableOpacity 
            style={s.checkboxRow} 
            onPress={() => setRecordarUsuario(!recordarUsuario)}
            disabled={loading}
          >
            <View style={[s.checkbox, recordarUsuario && s.checkboxActive]}>
              {recordarUsuario && <Ionicons name="checkmark" size={16} color="#0A1017" />}
            </View>
            <Text style={s.checkboxLabel}>Recordar usuario</Text>
          </TouchableOpacity>

          <TouchableOpacity style={[s.button, loading && s.buttonOff]} onPress={handleLogin} disabled={loading}>
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.buttonTxt}>Iniciar Sesión</Text>}
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
    </>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A1017' },
  settingsBtn: { position: 'absolute', top: 48, right: 20, zIndex: 10, padding: 8 },
  content: { flex: 1, justifyContent: 'center', paddingHorizontal: 24 },
  logoContainer: { 
    alignItems: 'center', 
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  logo: { 
    width: 200, 
    height: 120,
  },
  title: { fontSize: 32, fontWeight: 'bold', color: '#fff', textAlign: 'center', marginBottom: 8 },
  subtitle: { fontSize: 18, color: '#94a3b8', textAlign: 'center', marginBottom: 32 },
  banner: { backgroundColor: '#7f1d1d', borderRadius: 10, padding: 14, marginBottom: 16, alignItems: 'center' },
  bannerTxt: { color: '#fff', fontWeight: '700', fontSize: 14 },
  bannerSub: { color: 'rgba(255,255,255,0.8)', fontSize: 12, marginTop: 4 },
  form: { width: '100%' },
  input: {
    backgroundColor: '#1C2B3A', borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 8, paddingHorizontal: 16, paddingVertical: 12,
    fontSize: 16, color: '#fff', marginBottom: 16,
  },
  inputRow: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#1C2B3A', borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 8, marginBottom: 16,
  },
  inputFlex: {
    flex: 1, paddingHorizontal: 16, paddingVertical: 12,
    fontSize: 16, color: '#fff',
  },
  eyeBtn: { paddingHorizontal: 14 },
  checkboxRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginBottom: 16,
    paddingVertical: 4,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.3)',
    backgroundColor: 'transparent',
    marginRight: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxActive: {
    backgroundColor: '#D4920A',
    borderColor: '#D4920A',
  },
  checkboxLabel: {
    color: '#94a3b8',
    fontSize: 14,
  },
  button: { backgroundColor: '#D4920A', borderRadius: 12, paddingVertical: 16, alignItems: 'center', marginTop: 8 },
  buttonOff: { backgroundColor: '#475569' },
  buttonTxt: { color: '#0A1017', fontSize: 16, fontWeight: '700' },
  error: { color: '#ef4444', fontSize: 14, marginBottom: 12, textAlign: 'center' },
});
