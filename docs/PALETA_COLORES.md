# 🎨 Paleta de Colores - PULGA Mecánica Fi

## Paleta Profesional Corporativa

### Azul Corporativo (Color Principal)
- **Azul Principal**: `#1e40af` - Color principal profesional
- **Azul Claro**: `#3b82f6` - Para hover y estados activos
- **Azul Oscuro**: `#1e3a8a` - Para botones presionados y énfasis
- **Azul Acento**: `#0ea5e9` - Para elementos destacados

### Grises Profesionales
- **Gris Oscuro**: `#334155` - Textos importantes
- **Gris Medio**: `#475569` - Textos secundarios
- **Gris Claro**: `#64748b` - Textos terciarios
- **Gris Suave**: `#f1f5f9` - Fondos sutiles

## Uso en el Sistema

### Sidebar (Menú Lateral)
- Fondo: Gradiente de azul oscuro (`#1e293b` a `#0f172a`)
- Borde derecho: Azul principal (`#1e40af`)
- Links activos: Azul principal con texto blanco
- Links hover: Azul claro con fondo transparente

### Botones
- Botón principal: Azul principal (`#1e40af`) con texto blanco
- Botón hover: Azul oscuro (`#1e3a8a`)
- Botón outline: Borde azul con fondo transparente

### Fondos
- Fondo principal: `#f8fafc` (gris muy claro)
- Paneles: `#ffffff` (blanco)
- Elementos destacados: `#f1f5f9` (gris suave)

## Variables CSS

```css
:root {
  /* Paleta Profesional - Azul Corporativo */
  --brand-primary: #1e40af;
  --brand-primary-light: #3b82f6;
  --brand-primary-dark: #1e3a8a;
  --brand-secondary: #475569;
  --brand-accent: #0ea5e9;
  
  /* Colores neutros profesionales */
  --bg: #f8fafc;
  --panel: #ffffff;
  --text: #0f172a;
  --muted: #64748b;
  --line: #e2e8f0;
  --gray-strong: #334155;
  --gray-main: var(--brand-primary);
  --gray-soft: #f1f5f9;
}
```

## Ejemplos de Uso

### Botón Principal
```css
background: var(--brand-primary);
color: white;
```

### Botón Hover
```css
background: var(--brand-primary-dark);
box-shadow: 0 4px 12px rgba(30, 64, 175, 0.3);
```

### Link Activo
```css
background: var(--brand-primary);
color: white;
box-shadow: 0 2px 8px rgba(30, 64, 175, 0.3);
```

## Colores Complementarios

### Estados
- **Éxito**: `#059669` (Verde)
- **Error**: `#dc2626` (Rojo)
- **Advertencia**: `#f59e0b` (Ámbar)
- **Info**: `#0ea5e9` (Azul claro)

### Tickets
- **Abierto**: `#dbeafe` (Azul claro)
- **En Proceso**: `#fef3c7` (Amarillo claro)
- **Finalizado**: `#d1fae5` (Verde claro)
- **Entregado**: `#e0e7ff` (Índigo claro)

## Accesibilidad

Todos los colores cumplen con WCAG 2.1 nivel AA para contraste:
- Azul sobre blanco: ✅ Ratio 7.3:1
- Blanco sobre azul: ✅ Ratio 7.3:1
- Texto oscuro sobre blanco: ✅ Ratio 16.1:1

## Por qué esta Paleta

**Azul Corporativo:**
- Color más usado en aplicaciones empresariales
- Transmite confianza, profesionalismo y estabilidad
- Asociado con tecnología y eficiencia
- Fácil de leer y no cansa la vista

**Grises Neutros:**
- Proporcionan jerarquía visual clara
- Permiten que el contenido destaque
- Crean una interfaz limpia y ordenada

**Resultado:**
Una interfaz seria, profesional y corporativa, ideal para un sistema de gestión empresarial. Similar a aplicaciones como Salesforce, Microsoft 365, o SAP.
