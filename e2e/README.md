# E2E Tests - Taller Mecánico System

## Overview

This directory contains end-to-end tests for the taller mecánico system using Playwright. These tests validate critical user flows across the entire application.

## Test Coverage

The E2E test suite covers 5 critical flows:

1. **Login Flow** (`tests/login.spec.js`)
   - Successful login redirects to dashboard
   - Failed login shows error message
   - Empty fields validation
   - Show/hide password functionality
   - Password recovery flow

2. **Tickets Flow** (`tests/tickets.spec.js`)
   - Navigate to reception page
   - Display list of tickets
   - Filter tickets by status
   - View ticket details
   - Search tickets

3. **Payments Flow** (`tests/payments.spec.js`)
   - Navigate to economy page
   - Display economy statistics
   - Register a payment
   - View payment history
   - Filter movements by date

4. **Search Flow** (`tests/search.spec.js`)
   - Search by license plate
   - Handle no results
   - Clear search
   - Case-insensitive search
   - Search by client

5. **Logout Flow** (`tests/logout.spec.js`)
   - Successful logout redirects to login
   - Protected routes inaccessible after logout
   - Tokens removed from localStorage
   - Can login again after logout
   - Logout works from different pages

## Prerequisites

- Node.js 18+ installed
- Frontend server running on `http://localhost:5173`
- Backend API running on `http://localhost:8000`

## Installation

```bash
cd e2e
npm install
npx playwright install chromium
```

## Running Tests

### Run all tests
```bash
npm run test:e2e
```

### Run tests in UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Run tests in headed mode (see browser)
```bash
npm run test:e2e:headed
```

### Run specific test file
```bash
npx playwright test tests/login.spec.js
```

## Configuration

The Playwright configuration is in `playwright.config.js`:

- **Base URL**: `http://localhost:5173` (frontend)
- **Browser**: Chromium (Desktop Chrome)
- **Screenshots**: Captured on failure
- **Videos**: Retained on failure
- **Traces**: Captured on first retry

## Test Structure

Each test file follows this structure:

```javascript
import { test, expect } from '@playwright/test';

test.describe('Feature Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Setup (e.g., login)
  });

  test('specific scenario', async ({ page }) => {
    // Test implementation
  });
});
```

## Debugging

### View test report
```bash
npx playwright show-report
```

### Debug specific test
```bash
npx playwright test tests/login.spec.js --debug
```

### View traces
```bash
npx playwright show-trace trace.zip
```

## CI/CD Integration

The tests are configured to run in CI environments:

- Retries: 2 attempts in CI, 0 locally
- Workers: 1 in CI, unlimited locally
- Reporter: HTML report generated

## Notes

- Tests are designed to be resilient to UI changes
- Selectors use text content and semantic HTML when possible
- Tests handle cases where features may not be visible
- All tests include proper waits and timeouts

## Troubleshooting

### Frontend not starting
Ensure the frontend dev server is running:
```bash
cd ../frontend
npm run dev
```

### Backend not available
Ensure the backend API is running:
```bash
cd ..
python -m uvicorn app.main:app --reload
```

### Tests timing out
Increase timeout in `playwright.config.js`:
```javascript
use: {
  timeout: 30000, // 30 seconds
}
```
