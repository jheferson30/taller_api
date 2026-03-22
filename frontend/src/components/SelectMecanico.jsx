import { useState, useEffect } from "react";
import { api } from "../api";

/**
 * Select de mecánicos activos con fallback a input de texto si no hay mecánicos.
 * Uso: <SelectMecanico value={val} onChange={(v) => setVal(v)} placeholder="Sin asignar" />
 */
export default function SelectMecanico({ value, onChange, placeholder = "— Sin asignar —" }) {
  const [mecanicos, setMecanicos] = useState([]);

  useEffect(() => {
    api.listarMecanicos()
      .then((data) => setMecanicos(data.filter((m) => m.activo)))
      .catch(() => {});
  }, []);

  if (mecanicos.length === 0) {
    return (
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{placeholder}</option>
      {mecanicos.map((m) => (
        <option key={m.id} value={m.nombre}>{m.nombre}</option>
      ))}
    </select>
  );
}
