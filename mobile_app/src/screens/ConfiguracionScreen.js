import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import {
  getServerIp,
  saveServerIp,
  getIpsGuardadas,
  eliminarIp,
  detectarIpActiva,
  getAdminPassword,
  saveAdminPassword,
} from '../config';
import authService from '../services/authService';

export default function ConfiguracionScreen({ navigation, route }) {
  const [ip, setIp] = useState('');
  const [password, setPassword] = useState('');
  const [ipsGuardadas, setIpsGuardadas] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [user, setUser] = useState(null);

  const primeraVez = route.params?.primeraVez || false;

  useEffect(() => {
    cargarDatos();
  }, []);

  const cargarDatos = async () => {
    const [ipActual, pwd, lista, currentUser] = await Promise.all([
      getServerIp(),
      getAdminPassword(),
      getIpsGuardadas(),
      authService.getUser(),
    ]);
    setIp(ipActual);
    setPassword(pwd);
    setIpsGuardadas(lista);
    setUser(currentUser);
  };

  const guardar = async () => {
    if (!ip) {
      Alert.alert('Error', 'Ingresa una IP válida');
      return;
    }
    await saveServerIp(ip);
    await saveAdminPassword(password);
    Alert.alert('Éxito', 'Configuración guardada');
    await cargarDatos();
    if (primeraVez) {
      navigation.replace('Login');
    }
  };

  const buscarAutomatico = async () => {
    setBuscando(true);
    try {
      const ipEncontrada = await detectarIpActiva(password);
      if (ipEncontrada) {
        setIp(ipEncontrada);
        Alert.alert('Éxito', `Servidor encontrado en ${ipEncontrada}`);
        await cargarDatos();
      } else {
        Alert.alert('No encontrado', 'No se pudo detectar el servidor automáticamente');
      }
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setBuscando(false);
    }
  };

  const seleccionarIp = async (ipSeleccionada) => {
    setIp(ipSeleccionada);
    await saveServerIp(ipSeleccionada);
    await cargarDatos();
  };

  const borrarIp = async (ipABorrar) => {
    Alert.alert(
      'Confirmar',
      `¿Eliminar ${ipABorrar}?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: async () => {
            await eliminarIp(ipABorrar);
            await cargarDatos();
          },
        },
      ]
    );
  };

  const handleLogout = async () => {
    Alert.alert(
      'Cerrar Sesión',
      '¿Estás seguro que deseas cerrar sesión?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Cerrar Sesión',
          style: 'destructive',
          onPress: async () => {
            await authService.logout();
            navigation.replace('Login');
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Servidor</Text>
        
        <Text style={styles.label}>IP del Servidor</Text>
        <TextInput
          style={styles.input}
          placeholder="192.168.1.100"
          placeholderTextColor="#64748b"
          value={ip}
          onChangeText={setIp}
          keyboardType="numeric"
        />

        <Text style={styles.label}>Contraseña Admin (Legacy)</Text>
        <TextInput
          style={styles.input}
          placeholder="Contraseña"
          placeholderTextColor="#64748b"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity style={styles.button} onPress={guardar}>
          <Text style={styles.buttonText}>Guardar Configuración</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary]}
          onPress={buscarAutomatico}
          disabled={buscando}
        >
          <Text style={styles.buttonText}>
            {buscando ? 'Buscando...' : 'Buscar Automáticamente'}
          </Text>
        </TouchableOpacity>
      </View>

      {ipsGuardadas.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>IPs Guardadas</Text>
          {ipsGuardadas.map((ipGuardada) => (
            <View key={ipGuardada} style={styles.ipItem}>
              <TouchableOpacity
                style={styles.ipButton}
                onPress={() => seleccionarIp(ipGuardada)}
              >
                <Text style={styles.ipText}>{ipGuardada}</Text>
                {ipGuardada === ip && <Text style={styles.ipActive}>✓</Text>}
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.deleteButton}
                onPress={() => borrarIp(ipGuardada)}
              >
                <Text style={styles.deleteText}>✕</Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>
      )}

      {user && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Sesión</Text>
          <Text style={styles.userInfo}>Usuario: {user.username}</Text>
          <Text style={styles.userInfo}>Rol: {user.role}</Text>
          
          <TouchableOpacity
            style={[styles.button, styles.buttonDanger]}
            onPress={handleLogout}
          >
            <Text style={styles.buttonText}>Cerrar Sesión</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  section: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    color: '#94a3b8',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: '#fff',
    marginBottom: 16,
  },
  button: {
    backgroundColor: '#3b82f6',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  buttonSecondary: {
    backgroundColor: '#475569',
  },
  buttonDanger: {
    backgroundColor: '#ef4444',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  ipItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  ipButton: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginRight: 8,
  },
  ipText: {
    color: '#fff',
    fontSize: 16,
  },
  ipActive: {
    color: '#10b981',
    fontSize: 18,
    fontWeight: 'bold',
  },
  deleteButton: {
    backgroundColor: '#ef4444',
    borderRadius: 8,
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  userInfo: {
    color: '#94a3b8',
    fontSize: 14,
    marginBottom: 8,
  },
});
