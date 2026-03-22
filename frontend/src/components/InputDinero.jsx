/**
 * Input numérico con separadores de miles en formato colombiano.
 * Uso: <InputDinero value={valor} onChange={(v) => setValor(v)} />
 */
export default function InputDinero({ value, onChange, placeholder = "0", ...props }) {
  const fmt = (v) => {
    const n = String(v).replace(/\D/g, "");
    return n ? Number(n).toLocaleString("es-CO") : "";
  };
  return (
    <input
      type="text"
      inputMode="numeric"
      placeholder={placeholder}
      value={fmt(value)}
      onChange={(e) => {
        const raw = e.target.value.replace(/\D/g, "");
        onChange(raw ? Number(raw) : 0);
      }}
      {...props}
    />
  );
}
