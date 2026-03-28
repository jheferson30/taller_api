import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { TouchableOpacity, Text } from 'react-native';

import { ToastProvider } from './src/components/Toast';
import HomeScreen from './src/screens/HomeScreen';
import TicketListScreen from './src/screens/TicketListScreen';
import TicketDetailScreen from './src/screens/TicketDetailScreen';
import AddProcesoScreen from './src/screens/AddProcesoScreen';
import AddRepuestoScreen from './src/screens/AddRepuestoScreen';
import AddFotoScreen from './src/screens/AddFotoScreen';
import AddCompraScreen from './src/screens/AddCompraScreen';
import CobroRapidoScreen from './src/screens/CobroRapidoScreen';
import ConfiguracionScreen from './src/screens/ConfiguracionScreen';
import { detectarIpActiva } from './src/config';

const Stack = createNativeStackNavigator();

export default function App() {
  const [iniciando, setIniciando] = useState(true);
  const [hayConexion, setHayConexion] = useState(false);

  useEffect(() => {
    (async () => {
      const ip = await detectarIpActiva();
      setHayConexion(!!ip);
      setIniciando(false);
    })();
  }, []);

  if (iniciando) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f172a' }}>
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={{ color: '#94a3b8', marginTop: 12, fontSize: 14 }}>Buscando servidor...</Text>
      </View>
    );
  }

  return (
    <ToastProvider>
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={hayConexion ? 'Home' : 'Configuracion'}
        screenOptions={{
          headerStyle: { backgroundColor: '#1e40af' },
          headerTintColor: '#fff',
          headerTitleStyle: { fontWeight: 'bold' },
        }}
      >
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
        <Stack.Screen name="AddCompra" component={AddCompraScreen} options={{ title: 'Registrar Compra' }} />
        <Stack.Screen name="CobroRapido" component={CobroRapidoScreen} options={{ title: 'Cobro Rápido' }} />
      </Stack.Navigator>
    </NavigationContainer>
    </ToastProvider>
  );
}
