// Commitlint configuration for Hiron Monorepo
// Enforces Conventional Commits specification per Engineering Guidelines §10
//
// DEVELOPER INSTRUCTIONS:
// - Commitlint depends on Node packages (@commitlint/config-conventional).
// - These packages will be installed during the dependency installation phase.
// - This configuration file exists now in Phase 0 so the project structure is ready.

module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Allowed commit types per Engineering Guidelines §10
    'type-enum': [
      2,
      'always',
      [
        'feat',     // New feature
        'fix',      // Bug fix
        'docs',     // Documentation only
        'style',    // Formatting, missing semi colons, etc.
        'refactor', // Code change that neither fixes a bug nor adds a feature
        'perf',     // Code change that improves performance
        'test',     // Adding missing tests or correcting existing tests
        'build',    // Changes that affect the build system or external dependencies
        'ci',       // Changes to CI configuration files and scripts
        'chore',    // Other changes that don't modify src or test files
        'revert',   // Reverts a previous commit
      ],
    ],

    // Allowed commit scopes per Engineering Guidelines §10
    'scope-enum': [
      2,
      'always',
      [
        'api',      // Core API backend
        'web',      // Next.js frontend
        'ai',       // AI microservice
        'worker',   // Celery background workers
        'db',       // Database schemas & migrations
        'infra',    // Docker & Infrastructure
        'config',   // Monorepo tooling & configurations
        'deps',     // Dependency updates
        'docs',     // Documentation
      ],
    ],

    'header-max-length': [2, 'always', 100],
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    'subject-full-stop': [2, 'never', '.'],
  },
};
