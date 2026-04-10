import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('login exitoso redirige al dashboard', async ({ page }) => {
    // Llenar formulario de login
    await page.fill('input[id="username"]', 'admin');
    await page.fill('input[id="password"]', 'Admin123');
    
    // Click en botón de login
    await page.click('button[type="submit"]');
    
    // Verificar redirección al dashboard
    await expect(page).toHaveURL('/');
    
    // Verificar que se muestra contenido del dashboard
    await expect(page.locator('text=/Recepcion|Panel|Dashboard/i')).toBeVisible({ timeout: 10000 });
  });

  test('login fallido muestra error', async ({ page }) => {
    // Llenar formulario con credenciales incorrectas
    await page.fill('input[id="username"]', 'admin');
    await page.fill('input[id="password"]', 'wrongpassword');
    
    // Click en botón de login
    await page.click('button[type="submit"]');
    
    // Verificar que se muestra mensaje de error
    await expect(page.locator('text=/error|inválid|incorrecta/i')).toBeVisible({ timeout: 5000 });
    
    // Verificar que NO se redirige
    await expect(page).toHaveURL('/login');
  });

  test('campos vacíos no permiten login', async ({ page }) => {
    // Intentar hacer click sin llenar campos
    await page.click('button[type="submit"]');
    
    // Verificar que sigue en la página de login
    await expect(page).toHaveURL('/login');
  });

  test('muestra/oculta contraseña al hacer click en el icono', async ({ page }) => {
    const passwordInput = page.locator('input[id="password"]');
    
    // Verificar que inicialmente es tipo password
    await expect(passwordInput).toHaveAttribute('type', 'password');
    
    // Click en el botón de mostrar/ocultar (buscar el botón hermano del input)
    await page.locator('input[id="password"] + button').click();
    
    // Verificar que ahora es tipo text
    await expect(passwordInput).toHaveAttribute('type', 'text');
  });

  test('formulario de recuperación de contraseña funciona', async ({ page }) => {
    // Llenar usuario y contraseña incorrecta para mostrar error
    await page.fill('input[id="username"]', 'admin');
    await page.fill('input[id="password"]', 'wrong');
    await page.click('button[type="submit"]');
    
    // Esperar a que aparezca el error
    await expect(page.locator('text=/error|inválid/i')).toBeVisible({ timeout: 5000 });
    
    // Click en "¿Olvidaste tu contraseña?"
    const forgotPasswordButton = page.locator('button:has-text("¿Olvidaste tu contraseña?")');
    if (await forgotPasswordButton.isVisible()) {
      await forgotPasswordButton.click();
      
      // Verificar que se muestra el formulario de recuperación
      await expect(page.locator('text=/enlace|correo|recuperación/i')).toBeVisible();
    }
  });
});
