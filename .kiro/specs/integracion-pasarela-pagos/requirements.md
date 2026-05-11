# Documento de Requisitos: Integración Pasarela de Pagos

## Introducción

Este documento describe los requisitos para la integración de una pasarela de pagos en el sistema SaaS de gestión de talleres mecánicos.

Este spec es una **fase futura** — actualmente la facturación es manual (spec `planes-y-facturacion`). Este spec automatiza el cobro a los talleres clientes mediante una pasarela de pagos externa.

La pasarela principal es **Wompi** (Bancolombia) para el mercado colombiano, con arquitectura preparada para agregar **Stripe** para expansión internacional. Ninguna pasarela tiene costo fijo mensual — solo cobran comisión por transacción exitosa (~2.9% + tarifa fija).

**Prerequisitos:** El spec `planes-y-facturacion` debe estar completamente implementado antes de iniciar este spec.

---

## Glosario

- **Wompi**: Pasarela de pagos de Bancolombia. Soporta PSE, Nequi, tarjetas, Bancolombia a la mano. Sin mensualidad, ~2.9% + $900 COP por transacción.
- **Stripe**: Pasarela de pagos internacional. Estándar de la industria. Sin mensualidad, 2.9% + $0.30 USD por transacción.
- **Webhook**: Notificación HTTP que la pasarela envía al sistema cuando ocurre un evento (pago exitoso, fallido, reembolso).
- **Checkout**: Página o flujo de pago donde el cliente ingresa sus datos de pago.
- **Suscripcion_Automatica**: Cobro recurrente mensual sin intervención manual.
- **Sandbox**: Ambiente de pruebas de la pasarela que simula pagos sin dinero real.
- **Idempotencia**: Garantía de que procesar el mismo webhook dos veces no genera dos pagos registrados.

---

## Requisitos

### Requisito 1: Arquitectura de Integración

**User Story:** Como desarrollador, quiero una arquitectura de integración con pasarelas de pago que sea extensible, para poder agregar nuevas pasarelas sin reescribir el código de negocio.

#### Criterios de Aceptación

1. THE Sistema SHALL implementar una interfaz abstracta `PasarelaPagosBase` con métodos: `crear_checkout(taller_id, plan_id, monto, moneda)`, `verificar_pago(referencia)`, `procesar_webhook(payload, firma)`.
2. THE Sistema SHALL implementar `WompiPasarela` que extiende `PasarelaPagosBase` para el mercado colombiano.
3. THE Sistema SHALL implementar `StripePasarela` que extiende `PasarelaPagosBase` para el mercado internacional.
4. THE Sistema SHALL seleccionar la pasarela activa basándose en la `moneda` del taller: `COP` → Wompi, otras monedas → Stripe.
5. THE Sistema SHALL almacenar las credenciales de cada pasarela en variables de entorno o `SecretsManager`, nunca en el código.
6. THE Sistema SHALL soportar modo sandbox configurable por variable de entorno `PASARELA_SANDBOX=true` para desarrollo y pruebas.

---

### Requisito 2: Flujo de Pago con Wompi

**User Story:** Como ADMIN del taller, quiero pagar mi suscripción con PSE, Nequi o tarjeta desde la app, para no depender de transferencias manuales.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `POST /talleres/{taller_id}/pagos/checkout` protegido con `@require_role("ADMIN")` que genere un enlace de pago de Wompi.
2. WHEN el ADMIN del taller inicia un checkout, THE Sistema SHALL crear una transacción pendiente en la tabla `transacciones_pago` con estado `PENDIENTE` y retornar la URL de checkout de Wompi.
3. THE Sistema SHALL crear la tabla `transacciones_pago` con: `id` (PK), `taller_id` (FK), `plan_id` (FK), `pasarela` (enum: `WOMPI`, `STRIPE`), `referencia_externa` (string, ID de la transacción en la pasarela), `monto` (integer), `moneda` (string 3), `estado` (enum: `PENDIENTE`, `APROBADA`, `RECHAZADA`, `ANULADA`), `fecha_creacion` (timestamp), `fecha_actualizacion` (timestamp).
4. WHEN Wompi notifica un pago exitoso mediante webhook, THE Sistema SHALL actualizar la transacción a `APROBADA`, registrar el pago en `pagos_taller` (del spec `planes-y-facturacion`) y activar o renovar la suscripción del taller automáticamente.
5. WHEN Wompi notifica un pago fallido mediante webhook, THE Sistema SHALL actualizar la transacción a `RECHAZADA` y enviar una notificación interna al ADMIN del taller.
6. THE Sistema SHALL validar la firma del webhook de Wompi usando el `events_secret` de Wompi antes de procesar cualquier notificación.
7. THE Sistema SHALL implementar idempotencia en el procesamiento de webhooks: si se recibe el mismo `referencia_externa` dos veces, el segundo se ignora sin error.

---

### Requisito 3: Flujo de Pago con Stripe

**User Story:** Como ADMIN de un taller internacional, quiero pagar con tarjeta de crédito internacional, para usar el sistema desde cualquier país.

#### Criterios de Aceptación

1. THE Sistema SHALL usar Stripe Checkout Sessions para generar el flujo de pago internacional.
2. WHEN el ADMIN del taller inicia un checkout con Stripe, THE Sistema SHALL crear una Stripe Checkout Session y retornar la URL de checkout de Stripe.
3. WHEN Stripe notifica un pago exitoso mediante webhook, THE Sistema SHALL procesar el pago de la misma forma que Wompi (criterio 4 del Requisito 2).
4. THE Sistema SHALL validar la firma del webhook de Stripe usando `stripe.Webhook.construct_event` con el `webhook_secret` de Stripe.
5. THE Sistema SHALL soportar suscripciones recurrentes de Stripe (`Stripe Subscriptions`) para cobro automático mensual sin intervención del ADMIN.

---

### Requisito 4: Seguridad de Pagos

**User Story:** Como desarrollador, quiero que el sistema de pagos sea seguro y cumpla con los estándares de la industria, para proteger los datos financieros de los clientes.

#### Criterios de Aceptación

1. THE Sistema SHALL nunca almacenar datos de tarjetas de crédito — toda la información sensible se maneja exclusivamente en la pasarela.
2. THE Sistema SHALL validar la firma de todos los webhooks antes de procesar su contenido.
3. THE Sistema SHALL exponer el endpoint de webhooks en una ruta separada sin autenticación JWT: `POST /webhooks/wompi` y `POST /webhooks/stripe`.
4. THE Sistema SHALL aplicar rate limiting estricto a los endpoints de webhook: máximo 100 requests por minuto por IP.
5. THE Sistema SHALL registrar en Audit_Log cada transacción de pago con acción `PAGO_PROCESADO` incluyendo la pasarela, monto y estado.
6. THE Sistema SHALL usar HTTPS obligatorio para todos los endpoints relacionados con pagos en producción.

---

### Requisito 5: Reembolsos y Disputas

**User Story:** Como SUPER_ADMIN, quiero poder gestionar reembolsos desde la plataforma, para resolver disputas con clientes sin acceder directamente a la pasarela.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `POST /talleres/{taller_id}/pagos/{pago_id}/reembolso` protegido con `@require_role("SUPER_ADMIN")` para iniciar un reembolso.
2. WHEN el SUPER_ADMIN inicia un reembolso, THE Sistema SHALL llamar a la API de la pasarela correspondiente para procesar el reembolso y actualizar el estado de la transacción.
3. WHEN un reembolso es procesado exitosamente, THE Sistema SHALL ajustar la `fecha_vencimiento` del taller según corresponda y enviar una notificación interna al ADMIN del taller.
4. THE Sistema SHALL registrar en Audit_Log cada reembolso con acción `PAGO_REEMBOLSADO` incluyendo el motivo.
