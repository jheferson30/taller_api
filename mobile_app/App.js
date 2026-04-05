import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { TouchableOpacity, Text } from 'react-native';

import { ToastProvider } from './src/components/Toast';
import { ConnectionIndicator } from './src/components/ConnectionIndicator';
import HomeScreen from './src/screens/HomeScreen';
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

const Stack = createNativeStackNavigator();

export default function App() {
  const [iniciando, setIniciando] = useState(true);
  const [hayConexion, setHayConexion] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    (async () => {
      // Detectar IP del servidor
      const ip = await detectarIpActiva();
      setHayConexion(!!ip);

      // Cargar tokens guardados
      await authService.loadTokens();
      const authenticated = await authService.isAuthenticated();
      setIsAuthenticated(authenticated);

      // Inicializar servicio offline
      await offlineService.initialize();
      offlineService.startAutoSync();

      setIniciando(false);
    })();

    return () => {
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
    return 'Home';
  };

  return (
    <ToastProvider>
      <ConnectionIndicator />
      <NavigationContainer>
        <Stack.Navigator
          initialRouteName={getInitialRoute()}
          screenOptions={{
            headerStyle: { backgroundColor: '#1e40af' },
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
              title: 'PULGA Mecánica Fi',
              headerRight: () => (
                <TouchableOpacity
                  onPress={() => navigation.navigate('Configuracion')}
                  style={{ marginRight: 4, padding: 6 }}
                >
                  <Text style={{ color: '#fff', fontSize: 20 }}>⚙</Text>
                </TouchableOpacity>
              ),
            })}
          />
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
