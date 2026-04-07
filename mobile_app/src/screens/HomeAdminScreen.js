import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from "react-native";
import { colors } from "../theme";
import authService from "../services/authService";

const MENU = [
  { label: "Economia del dia", sub: "Ingresos, egresos y ganancia", screen: "AdminEconomia" },
  { label: "Estado de tickets", sub: "Ver tickets por estado", screen: "TicketList", params: { estado: null, titulo: "Todos los tickets" } },
  { label: "Cobro rapido", sub: "Registrar un pago", screen: "CobroRapido", params: {} },
];

export default function HomeAdminScreen({ navigation }) {
  const handleLogout = async () => {
    await authService.logout();
    navigation.replace("Login");
  };

  return (
    <ScrollView style={s.container}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Panel Administrador</Text>
      </View>

      <View style={s.list}>
        {MENU.map((item) => (
          <TouchableOpacity
            key={item.label}
            style={s.item}
            onPress={() => navigation.navigate(item.screen, item.params || {})}
          >
            <View style={s.itemContent}>
              <Text style={s.itemLabel}>{item.label}</Text>
              <Text style={s.itemSub}>{item.sub}</Text>
            </View>
            <Text style={s.arrow}>›</Text>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A1017' },
  header: { backgroundColor: '#0F1923', padding: 24, paddingTop: 32 },
  headerTitle: { color: "#fff", fontSize: 22, fontWeight: "bold" },
  list: { paddingTop: 8 },
  item: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: '#1C2B3A',
    paddingHorizontal: 20,
    paddingVertical: 18,
    marginHorizontal: 12,
    marginBottom: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.07)',
  },
  itemContent: { flex: 1 },
  itemLabel: { fontSize: 16, fontWeight: "600", color: '#fff' },
  itemSub: { fontSize: 13, color: '#94a3b8', marginTop: 2 },
  arrow: { fontSize: 24, color: '#D4920A' },
});