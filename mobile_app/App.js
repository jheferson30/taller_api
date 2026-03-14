import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './src/screens/HomeScreen';
import TicketListScreen from './src/screens/TicketListScreen';
import TicketDetailScreen from './src/screens/TicketDetailScreen';
import AddProcesoScreen from './src/screens/AddProcesoScreen';
import AddRepuestoScreen from './src/screens/AddRepuestoScreen';
import AddFotoScreen from './src/screens/AddFotoScreen';
import AddCompraScreen from './src/screens/AddCompraScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Home"
        screenOptions={{
          headerStyle: {
            backgroundColor: '#1e40af',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: 'bold',
          },
        }}
      >
        <Stack.Screen 
          name="Home" 
          component={HomeScreen}
          options={{ title: 'PULGA Mecánica Fi' }}
        />
        <Stack.Screen 
          name="TicketList" 
          component={TicketListScreen}
          options={{ title: 'Tickets' }}
        />
        <Stack.Screen 
          name="TicketDetail" 
          component={TicketDetailScreen}
          options={{ title: 'Detalle del Ticket' }}
        />
        <Stack.Screen 
          name="AddProceso" 
          component={AddProcesoScreen}
          options={{ title: 'Agregar Proceso' }}
        />
        <Stack.Screen 
          name="AddRepuesto" 
          component={AddRepuestoScreen}
          options={{ title: 'Agregar Repuesto' }}
        />
        <Stack.Screen 
          name="AddFoto" 
          component={AddFotoScreen}
          options={{ title: 'Agregar Foto' }}
        />
        <Stack.Screen 
          name="AddCompra" 
          component={AddCompraScreen}
          options={{ title: 'Registrar Compra' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
