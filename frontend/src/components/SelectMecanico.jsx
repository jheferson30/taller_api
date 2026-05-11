import { useState, useEffect } from "react";
import { api } from "../api";

/**
 * Selector de usuarios del taller para asignar como mecánico/responsable.
 * Devuelve el user_id (entero) en onChange, no el nombre.
 *
 * Uso: <SelectMecanico value={val} onChange={(id) => setVal(id)} placeholder="Sin asignar" />
 */
export default function SelectMecanico({ value, onChange, placeholder = "— Sin asignar —" }) {
  const [usuarios, setUsuarios] = useState([]);

  useEffect(() => {
    api.listarUsuariosParaAsignacion()
      .then((data) => setUsuarios(data.users || []))
      .catch(() => {});
  }, []);

  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
    >
      <option value="">{placeholder}</option>
      {usuarios.map((u) => (
        <option key={u.id} value={u.id}>
          {u.nombre_completo || u.username}
        </option>
      ))}
    </select>
  );
}
