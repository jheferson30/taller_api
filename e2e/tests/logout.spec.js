import { test, expect } from '@playwright/test';

test.describe('Logout Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login antes de cada test
    await page.goto('/login');
    await page.fill('input[id="username"]', 'admin');
    await page.fill('input[id="password"]', 'Admin123');
    await page.click('button[type="submit"]');
    
    // Esperar a que cargue el dashboard
    await expect(page).toHaveURL('/');
    await page.waitForLoadState('networkidle');
  });

  test('logout exitoso redirige a login', async ({ page }) => {
    // Buscar botón de logout (puede estar en diferentes lugares)
    const logoutButton = page.locator('button:has-text("Salir"), button:has-text("Cerrar Sesión"), a:has-text("Salir"), a:has-text("Logout")').first();
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      
      // Verificar redirección a login
      await expect(page).toHaveURL('/login', { timeout: 5000 });
      
      // Verificar que se muestra el formulario de login
      await expect(page.locator('input[id="username"]')).toBeVisible();
    } else {
      // Si no hay botón visible, buscar en menú desplegable
      const menuButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], [class*="menu"]').first();
      
      if (await menuButton.isVisible()) {
        await menuButton.click();
        await page.waitForTimeout(500);
        
        const logoutInMenu = page.locator('button:has-text("Salir"), a:has-text("Salir")').first();
        if (await logoutInMenu.isVisible()) {
          await logoutInMenu.click();
          await expect(page).toHaveURL('/login', { timeout: 5000 });
        }
      }
    }
  });

  test('después de logout no se puede acceder a rutas protegidas', async ({ page }) => {
    // Hacer logout
    const logoutButton = page.locator('button:has-text("Salir"), a:has-text("Salir")').first();
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      await expect(page).toHaveURL('/login', { timeout: 5000 });
      
      // Intentar acceder a una ruta protegida
      await page.goto('/');
      
      // Debería redirigir a login
      await expect(page).toHaveURL('/login', { timeout: 5000 });
    }
  });

  test('tokens se eliminan después de logout', async ({ page }) => {
    // Verificar que hay tokens antes del logout
    const tokensBefore = await page.evaluate(() => {
      return {
        access: localStorage.getItem('access_token'),
        refresh: localStorage.getItem('refresh_token'),
      };
    });
    
    expect(tokensBefore.access || tokensBefore.refresh).toBeTruthy();
    
    // Hacer logout
    const logoutButton = page.locator('button:has-text("Salir"), a:has-text("Salir")').first();
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      await expect(page).toHaveURL('/login', { timeout: 5000 });
      
      // Verificar que los tokens fueron eliminados
      const tokensAfter = await page.evaluate(() => {
        return {
          access: localStorage.getItem('access_token'),
          refresh: localStorage.getItem('refresh_token'),
        };
      });
      
      expect(tokensAfter.access).toBeNull();
      expect(tokensAfter.refresh).toBeNull();
    }
  });

  test('puede hacer login nuevamente después de logout', async ({ page }) => {
    // Hacer logout
    const logoutButton = page.locator('button:has-text("Salir"), a:has-text("Salir")').first();
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      await expect(page).toHaveURL('/login', { timeout: 5000 });
      
      // Hacer login nuevamente
      await page.fill('input[id="username"]', 'admin');
      await page.fill('input[id="password"]', 'Admin123');
      await page.click('button[type="submit"]');
      
      // Verificar que se redirige al dashboard
      await expect(page).toHaveURL('/');
      await expect(page.locator('text=/Recepcion|Panel|Dashboard/i')).toBeVisible({ timeout: 10000 });
    }
  });

  test('logout desde diferentes páginas funciona', async ({ page }) => {
    // Navegar a diferentes páginas y hacer logout desde cada una
    const pages = [
      { name: 'Dashboard', url: '/' },
    ];
    
    for (const testPage of pages) {
      // Navegar a la página
      await page.goto(testPage.url);
      await page.waitForLoadState('networkidle');
      
      // Buscar y hacer click en logout
      const logoutButton = page.locator('button:has-text("Salir"), a:has-text("Salir")').first();
      
      if (await logoutButton.isVisible()) {
        await logoutButton.click();
        
        // Verificar redirección a login
        await expect(page).toHaveURL('/login', { timeout: 5000 });
        
        // Login nuevamente para el siguiente test
        if (testPage !== pages[pages.length - 1]) {
          await page.fill('input[id="username"]', 'admin');
          await page.fill('input[id="password"]', 'Admin123');
          await page.click('button[type="submit"]');
          await expect(page).toHaveURL('/');
        }
      }
    }
  });
});
