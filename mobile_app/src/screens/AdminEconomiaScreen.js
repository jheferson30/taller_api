import React, { useState, useCallback } from "react";
import { View, Text, StyleSheet, ScrollView, RefreshControl, ActivityIndicator, TouchableOpacity, Alert, Platform } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import DateTimePicker from "@react-native-community/datetimepicker";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "../api";
import { colors } from "../theme";
import { getAuthBaseUrl } from "../config";

const fmt = (n) => "$" + Number(n ?? 0).toLocaleString("es-CO");

const TIPO_CONFIG = {
  INGRESO_ANTICIPO: { label: "Anticipo",     color: "#0ea5e9" },
  INGRESO_FINAL:    { label: "Pago final",   color: "#10b981" },
  INGRESO_RAPIDO:   { label: "Cobro Rápido", color: "#f59e0b" },
  EGRESO:           { label: "Egreso",       color: "#ef4444" },
};

function hoyISO() {
  return new Date().toISOString().split("T")[0];
}

function sumarDias(iso, dias) {
  const d = new Date(iso + "T12:00:00");
  d.setDate(d.getDate() + dias);
  return d.toISOString().split("T")[0];
}

function formatoVisible(iso) {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

export default function AdminEconomiaScreen() {
  const insets = useSafeAreaInsets();
  const [fecha, setFecha] = useState(hoyISO());
  const [mostrarPicker, setMostrarPicker] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState(null);

  const cargar = async (f) => {
    try {
      setError(null);
      setData(await api.getEconomia(f));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { cargar(fecha); }, [fecha]));

  const onRefresh = () => { setRefreshing(true); cargar(fecha); };

  const cambiarFecha = (dias) => {
    const nueva = sumarDias(fecha, dias);
    setFecha(nueva);
    setLoading(true);
  };

  const onPickerChange = (event, selectedDate) => {
    setMostrarPicker(Platform.OS === "ios");
    if (selectedDate) {
      const iso = selectedDate.toISOString().split("T")[0];
      if (iso !== fecha) {
        setFecha(iso);
        setLoading(true);
      }
    }
  };

  const descargarPDF = async () => {
    setDescargando(true);
    try {
      const baseUrl = await getAuthBaseUrl();
      const token = await AsyncStorage.getItem("@auth_access_token");
      const url = `${baseUrl}/economia-dia/pdf?fecha=${fecha}`;
      const destino = FileSystem.documentDirectory + `economia_${fecha}.pdf`;

      const resultado = await FileSystem.downloadAsync(url, destino, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (resultado.status === 200) {
        const puedeCompartir = await Sharing.isAvailableAsync();
        if (puedeCompartir) {
          await Sharing.shareAsync(resultado.uri, {
            mimeType: "application/pdf",
            dialogTitle: "Economia " + fecha,
          });
        } else {
          Alert.alert("Descargado", "PDF guardado en: " + resultado.uri);
        }
      } else {
        Alert.alert("Error", "No se pudo descargar el PDF");
      }
    } catch (err) {
      Alert.alert("Error", err.message);
    } finally {
      setDescargando(false);
    }
  };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color={colors.primary} /></View>;
  if (error)   return <View style={s.center}><Text style={s.errorTxt}>{error}</Text></View>;

  const ganancia = data?.saldo_caja ?? 0;
  const ingresos = data?.total_ingresos ?? 0;
  const gastos   = data?.total_gastos ?? 0;
  const maxBar   = Math.max(ingresos, gastos, 1);

  return (
    <ScrollView style={s.container} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>

      {/* Selector de fecha */}
      <View style={s.fechaRow}>
        <TouchableOpacity style={s.fechaBtn} onPress={() => cambiarFecha(-1)}>
          <Text style={s.fechaBtnTxt}>{"<"}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.fechaCenter} onPress={() => setMostrarPicker(true)}>
          <Text style={s.fechaTxt}>{formatoVisible(fecha)}</Text>
          <Text style={s.fechaHoy}>{fecha === hoyISO() ? "Hoy  —  toca para cambiar" : "toca para cambiar"}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.fechaBtn} onPress={() => cambiarFecha(1)} disabled={fecha >= hoyISO()}>
          <Text style={[s.fechaBtnTxt, fecha >= hoyISO() && { color: colors.border }]}>{">"}</Text>
        </TouchableOpacity>
      </View>

      {mostrarPicker && (
        <DateTimePicker
          value={new Date(fecha + "T12:00:00")}
          mode="date"
          display={Platform.OS === "ios" ? "spinner" : "calendar"}
          maximumDate={new Date()}
          onChange={onPickerChange}
        />
      )}

      {/* Badge */}
      <View style={s.topRow}>
        <View style={[s.badge, { backgroundColor: ganancia >= 0 ? "#1A7A4A" : "#C0392B" }]}>
          <Text style={[s.badgeTxt, { color: "#ffffff" }]}>
            {ganancia >= 0 ? "Positivo" : "Negativo"}
          </Text>
        </View>
      </View>

      {/* KPIs */}
      <View style={s.kpiRow}>
        <View style={[s.kpiCard, { borderTopColor: "#1A7A4A" }]}>
          <Text style={s.kpiLbl}>Ingresos</Text>
          <Text style={[s.kpiVal, { color: "#1A7A4A" }]}>{fmt(ingresos)}</Text>
        </View>
        <View style={[s.kpiCard, { borderTopColor: "#C0392B" }]}>
          <Text style={s.kpiLbl}>Egresos</Text>
          <Text style={[s.kpiVal, { color: "#C0392B" }]}>{fmt(gastos)}</Text>
        </View>
      </View>

      {/* Ganancia */}
      <View style={[s.gananciaCard, { borderTopColor: "#D4920A" }]}>
        <Text style={s.gananciaLbl}>Ganancia del dia</Text>
        <Text style={[s.gananciaVal, { color: "#D4920A" }]}>{fmt(ganancia)}</Text>
        <Text style={s.gananciaTickets}>{data?.tickets_finalizados ?? 0} tickets cerrados</Text>
      </View>

      {/* Barras */}
      <View style={s.section}>
        <Text style={s.sectionTitle}>Comparacion visual</Text>
        <BarRow label="Ingresos" value={ingresos} max={maxBar} color="#1A7A4A" />
        <BarRow label="Egresos"  value={gastos}   max={maxBar} color="#C0392B" />
        <BarRow label="Ganancia" value={Math.abs(ganancia)} max={maxBar} color="#D4920A" />
      </View>

      {/* Desglose */}
      {data?.desglose_ingresos && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>Desglose de ingresos</Text>
          <DesgloseRow label="Anticipos"      value={data.desglose_ingresos.anticipos} color="#D4920A" />
          <DesgloseRow label="Pagos finales"  value={data.desglose_ingresos.finales} color="#D4920A" />
          <DesgloseRow label="Cobros rapidos" value={data.desglose_ingresos.rapidos} color="#D4920A" />
        </View>
      )}

      {/* Ultimos movimientos */}
      {data?.ultimos_movimientos?.length > 0 && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>Ultimos movimientos</Text>
          {data.ultimos_movimientos.map((m, i) => {
            const cfg = TIPO_CONFIG[m.tipo] || { label: m.tipo, color: colors.textMuted };
            return (
              <View key={i} style={s.movRow}>
                <View style={[s.movDot, { backgroundColor: cfg.color }]} />
                <View style={s.movInfo}>
                  <Text style={s.movConcepto}>
                    {m.tipo === 'INGRESO_RAPIDO' ? `${cfg.label}: ${m.concepto}` : m.concepto}
                  </Text>
                  {m.placa ? <Text style={s.movPlaca}>{m.placa}</Text> : null}
                </View>
                <Text style={[s.movValor, { color: cfg.color }]}>
                  {m.tipo !== "EGRESO" ? "+" : "-"}{fmt(m.valor)}
                </Text>
              </View>
            );
          })}
        </View>
      )}

      {data?.ultimos_movimientos?.length === 0 && (
        <View style={s.empty}><Text style={s.emptyTxt}>Sin movimientos este dia</Text></View>
      )}

      {/* Boton PDF al final */}
      <TouchableOpacity
        style={[s.pdfBtn, descargando && { opacity: 0.6 }, { marginBottom: insets.bottom + 16 }]}
        onPress={descargarPDF}
        disabled={descargando}
      >
        <Text style={s.pdfBtnTxt}>{descargando ? "Descargando..." : "Descargar PDF"}</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}

function BarRow({ label, value, max, color }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <View style={s.barRow}>
      <Text style={s.barLabel}>{label}</Text>
      <View style={s.barTrack}>
        <View style={[s.barFill, { width: pct + "%", backgroundColor: color }]} />
      </View>
      <Text style={[s.barValue, { color }]}>{fmt(value)}</Text>
    </View>
  );
}

function DesgloseRow({ label, value, color }) {
  return (
    <View style={s.desgloseRow}>
      <Text style={s.desgloseLabel}>{label}</Text>
      <Text style={[s.desgloseValue, { color }]}>{fmt(value)}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A1017' },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24, backgroundColor: '#0A1017' },
  errorTxt: { color: '#fff', textAlign: "center" },
  fechaRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: '#0F1923', borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  fechaBtn: { padding: 8 },
  fechaBtnTxt: { fontSize: 28, color: '#D4920A', fontWeight: "bold" },
  fechaCenter: { alignItems: "center" },
  fechaTxt: { fontSize: 18, fontWeight: "700", color: '#fff' },
  fechaHoy: { fontSize: 11, color: '#D4920A', fontWeight: "600", marginTop: 2 },
  topRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 16, paddingVertical: 10 },
  badge: { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 12, borderWidth: 0 },
  badgeTxt: { fontSize: 12, fontWeight: "700" },
  pdfBtn: { backgroundColor: '#D4920A', marginHorizontal: 16, marginVertical: 16, paddingVertical: 14, borderRadius: 10, alignItems: "center" },
  pdfBtnTxt: { color: '#0A1017', fontWeight: "700", fontSize: 15 },
  kpiRow: { flexDirection: "row", gap: 12, paddingHorizontal: 16, marginBottom: 12 },
  kpiCard: { flex: 1, backgroundColor: '#0F1923', borderRadius: 12, padding: 16, borderTopWidth: 3, borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)', elevation: 2 },
  kpiLbl: { fontSize: 12, color: 'rgba(255,255,255,0.45)', fontWeight: "600", textTransform: "uppercase", marginBottom: 6 },
  kpiVal: { fontSize: 22, fontWeight: "bold" },
  gananciaCard: { marginHorizontal: 16, marginBottom: 16, backgroundColor: '#0F1923', borderRadius: 12, padding: 20, borderTopWidth: 3, borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)', elevation: 2, alignItems: "center" },
  gananciaLbl: { fontSize: 13, color: 'rgba(255,255,255,0.45)', fontWeight: "600", textTransform: "uppercase", marginBottom: 6 },
  gananciaVal: { fontSize: 36, fontWeight: "bold", marginBottom: 4 },
  gananciaTickets: { fontSize: 12, color: '#94a3b8' },
  section: { backgroundColor: '#0F1923', marginHorizontal: 16, marginBottom: 12, borderRadius: 12, padding: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)', elevation: 1 },
  sectionTitle: { fontSize: 12, fontWeight: "700", color: 'rgba(255,255,255,0.45)', textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 14 },
  barRow: { flexDirection: "row", alignItems: "center", marginBottom: 12 },
  barLabel: { width: 70, fontSize: 13, color: '#fff' },
  barTrack: { flex: 1, height: 10, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 5, marginHorizontal: 8, overflow: "hidden" },
  barFill: { height: "100%", borderRadius: 5 },
  barValue: { width: 70, fontSize: 13, fontWeight: "700", textAlign: "right" },
  desgloseRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  desgloseLabel: { fontSize: 14, color: '#fff' },
  desgloseValue: { fontSize: 14, fontWeight: "700" },
  movRow: { flexDirection: "row", alignItems: "center", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  movDot: { width: 10, height: 10, borderRadius: 5, marginRight: 12 },
  movInfo: { flex: 1 },
  movConcepto: { fontSize: 14, color: '#fff', fontWeight: "500" },
  movPlaca: { fontSize: 12, color: '#94a3b8', marginTop: 2 },
  movValor: { fontSize: 15, fontWeight: "700" },
  empty: { padding: 32, alignItems: "center" },
  emptyTxt: { color: '#94a3b8', fontSize: 14 },
});
