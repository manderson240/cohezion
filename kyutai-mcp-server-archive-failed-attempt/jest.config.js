/**
 * Jest configuration for Obsidian plugin TypeScript tests
 */

module.exports = {
  // Use ts-jest for TypeScript support
  preset: 'ts-jest',
  testEnvironment: 'node',

  // Root directory for test files
  testMatch: [
    '<rootDir>/tests/**/*.test.ts',
    '<rootDir>/tests/**/*.spec.ts'
  ],

  // Module name mapper for path aliases
  moduleNameMapper: {
    '@/(.*)': '<rootDir>/src/$1',
    '@tests/(.*)': '<rootDir>/tests/$1'
  },

  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/tests/setup.ts'
  ],

  // Coverage configuration
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/index.ts',
    '!src/**/index.ts'
  ],
  coverageDirectory: 'tests/coverage',
  coverageReporters: ['html', 'text', 'lcov', 'json'],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },

  // TypeScript configuration
  globals: {
    'ts-jest': {
      tsconfig: {
        jsx: 'react',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true
      }
    }
  },

  // Test timeout
  testTimeout: 10000,

  // Verbose output
  verbose: true,

  // Clear mocks between tests
  clearMocks: true,

  // Reset mocks between tests
  resetMocks: true,

  // Restore mocks between tests
  restoreMocks: true
};
