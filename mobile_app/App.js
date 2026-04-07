import React, { useEffect, useState, useRef } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { TouchableOpacity, Text } from 'react-native';

import { ToastProvider } from './src/components/Toast';
import { ConnectionIndicator } from './src/components/ConnectionIndicator';
import HomeScreen from './src/screens/HomeScreen';
import HomeAdminScreen from './src/screens/HomeAdminScreen';
import AdminEconomiaScreen from './src/screens/AdminEconomiaScreen';
import TicketListScreen from './src/screens/TicketListScreen';
import TicketDetailScreen from './src/screens/TicketDetailScreen';
import AddProcesoScreen from './src/screens/AddProcesoScreen';
import AddRepuestoScreen from './src/screens/AddRepuestoScreen';
import AddFotoScreen from './src/screens/AddFotoScreen';
import CobroRapidoScreen from './src/screens/CobroRapidoScreen';
import ConfiguracionScreen from './src/screens/ConfiguracionScreen';
import LoginScreen from './src/screens/LoginScreen';

import { detectarIpActiva } from './src/config';
import authService from './src/services/authService';
import offlineService from './src/services/offlineService';
import { sessionEvents } from './src/services/sessionEvents';

const Stack = createNativeStackNavigator();

export default function App() {
  const [iniciando, setIniciando] = useState(true);
  const [hayConexion, setHayConexion] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const navigationRef = useRef(null);

  useEffect(() => {
    (async () => {
      // Detectar IP del servidor
      const ip = await detectarIpActiva();
      setHayConexion(!!ip);

      // Cargar tokens guardados - sesión persistente
      await authService.loadTokens();
      const authenticated = await authService.isAuthenticated();
      setIsAuthenticated(authenticated);
      if (authenticated) {
        const user = await authService.getUser();
        const roles = user?.roles || [];
        setIsAdmin(roles.includes('ADMIN'));
      }

      // Inicializar servicio offline
      await offlineService.initialize();
      offlineService.startAutoSync();
      // Si ya hay operaciones pendientes y hay conexión, sincronizar de inmediato
      const state = offlineService.getState();
      if (state.isOnline && state.pendingCount > 0) {
        offlineService.syncPendingOperations().catch(console.error);
      }

      setIniciando(false);
    })();

    // Escuchar sesión expirada
    const unsubSession = sessionEvents.onSessionExpired(() => {
      if (navigationRef.current) {
        navigationRef.current.reset({ index: 0, routes: [{ name: 'Login' }] });
      }
    });

    return () => {
      unsubSession();
      offlineService.stopAutoSync();
      offlineService.destroy();
    };
  }, []);

  if (iniciando) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f172a' }}>
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={{ color: '#94a3b8', marginTop: 12, fontSize: 14 }}>Buscando servidor...</Text>
      </View>
    );
  }

  const getInitialRoute = () => {
    if (!hayConexion) return 'Configuracion';
    if (!isAuthenticated) return 'Login';
    return isAdmin ? 'HomeAdmin' : 'Home';
  };

  return (
    <ToastProvider>
      <ConnectionIndicator />
      <NavigationContainer ref={navigationRef}>
        <Stack.Navigator
          initialRouteName={getInitialRoute()}
          screenOptions={{
            headerStyle: { backgroundColor: '#0F1923' },
            headerTintColor: '#fff',
            headerTitleStyle: { fontWeight: 'bold' },
          }}
        >
          <Stack.Screen
            name="Login"
            component={LoginScreen}
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="Home"
            component={HomeScreen}
            options={({ navigation }) => ({
              title: 'Taller Mecánico',
              headerRight: () => (
                <TouchableOpacity onPress={() => navigation.navigate('Configuracion')} style={{ marginRight: 4, padding: 6 }}>
                  <Text style={{ color: '#fff', fontSize: 20 }}>⚙</Text>
                </TouchableOpacity>
              ),
            })}
          />
          <Stack.Screen name="HomeAdmin" component={HomeAdminScreen} options={({ navigation }) => ({
            title: 'Panel Administrador',
            headerRight: () => (
              <TouchableOpacity onPress={() => navigation.navigate('Configuracion')} style={{ marginRight: 4, padding: 6 }}>
                <Text style={{ color: '#fff', fontSize: 20 }}>⚙</Text>
              </TouchableOpacity>
            ),
          })} />
          <Stack.Screen name="AdminEconomia" component={AdminEconomiaScreen} options={{ title: 'Economia del Dia' }} />
          <Stack.Screen
            name="Configuracion"
            component={ConfiguracionScreen}
            options={{ title: 'Configuración' }}
            initialParams={{ primeraVez: !hayConexion }}
          />
          <Stack.Screen name="TicketList" component={TicketListScreen} options={{ title: 'Tickets' }} />
          <Stack.Screen name="TicketDetail" component={TicketDetailScreen} options={{ title: 'Detalle del Ticket' }} />
          <Stack.Screen name="AddProceso" component={AddProcesoScreen} options={{ title: 'Agregar Proceso' }} />
          <Stack.Screen name="AddRepuesto" component={AddRepuestoScreen} options={{ title: 'Agregar Repuesto' }} />
          <Stack.Screen name="AddFoto" component={AddFotoScreen} options={{ title: 'Agregar Foto' }} />
          <Stack.Screen name="CobroRapido" component={CobroRapidoScreen} options={{ title: 'Cobro Rápido' }} />
        </Stack.Navigator>
      </NavigationContainer>
    </ToastProvider>
  );
}
