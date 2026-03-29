# Bugfix Requirements Document

## Introduction

Al guardar un repuesto marcado como "comprado" desde la pantalla `AddRepuestoScreen` en la app móvil (React Native / Expo), la app lanza el error `Cannot read property 'reload' of undefined`. El error ocurre en `handleGuardar` cuando intenta invocar un callback `reload` que no existe en `route.params`, ya que `RepuestosTab` navega a `AddRepuesto` pasando únicamente `{ ticketId }` sin incluir dicho callback.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN el usuario completa el formulario de "Agregar Repuesto" con `fueComprado = true` y presiona "Guardar Repuesto" THEN el sistema lanza `TypeError: Cannot read property 'reload' of undefined` y no guarda el repuesto ni la compra.

1.2 WHEN `AddRepuestoScreen` intenta acceder a `route.params.reload` después de guardar THEN el sistema falla porque `RepuestosTab` navega a la pantalla con `navigation.navigate('AddRepuesto', { ticketId })` sin pasar el parámetro `reload`.

### Expected Behavior (Correct)

2.1 WHEN el usuario completa el formulario con `fueComprado = true` y presiona "Guardar Repuesto" THEN el sistema SHALL guardar el repuesto y la compra asociada sin lanzar ningún error.

2.2 WHEN `AddRepuestoScreen` termina de guardar exitosamente THEN el sistema SHALL volver a la pantalla anterior con `navigation.goBack()` sin intentar invocar ningún callback de `route.params`.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN el usuario guarda un repuesto con `fueComprado = false` THEN el sistema SHALL CONTINUE TO guardar el repuesto correctamente y volver a la pantalla anterior.

3.2 WHEN el usuario vuelve a la pantalla `TicketDetail` después de guardar un repuesto THEN el sistema SHALL CONTINUE TO recargar los datos del ticket mediante `useFocusEffect` al recuperar el foco.

3.3 WHEN el usuario cancela el formulario de "Agregar Repuesto" THEN el sistema SHALL CONTINUE TO volver a la pantalla anterior sin guardar nada.
