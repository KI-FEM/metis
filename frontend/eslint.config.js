import {globalIgnores} from 'eslint/config'
import {defineConfigWithVueTs, vueTsConfigs} from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVueA11y from 'eslint-plugin-vuejs-accessibility'
import pluginVitest from '@vitest/eslint-plugin'
import pluginCypress from 'eslint-plugin-cypress/flat'

// To allow more languages other than `ts` in `.vue` files, uncomment the following lines:
// import { configureVueProject } from '@vue/eslint-config-typescript'
// configureVueProject({ scriptLangs: ['ts', 'tsx'] })
// More info at https://github.com/vuejs/eslint-config-typescript/#advanced-setup

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}']
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  pluginVueA11y.configs['flat/recommended'],

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*']
  },

  {
    ...pluginCypress.configs.recommended,
    files: [
      'cypress/e2e/**/*.{cy,spec}.{js,ts,jsx,tsx}',
      'cypress/support/**/*.{js,ts,jsx,tsx}'
    ]
  },
  {
    rules: {
      // strongly recommended Vue rules:
      'vue/first-attribute-linebreak': ['warn', {'singleline': 'beside', 'multiline': 'beside'}],
      'vue/html-closing-bracket-newline': ['warn', {'multiline': 'never'}],
      'vue/singleline-html-element-content-newline': ['warn', {'externalIgnores': ['router-link']}],
      'vue/max-attributes-per-line': ['warn', {'singleline': {'max': 3}}],

      // recommended Vue rules:
      'vue/attributes-order': ['warn', {alphabetical: true}],

      // uncategorized Vue rules:
      'vue/block-lang': ['error', {'script': {'lang': 'ts'}}],
      'vue/block-order': ['error', {'order': ['script', 'template', 'style']}],
      'vue/block-tag-newline': 'error',
      'vue/component-api-style': ['error', ['script-setup']],
      'vue/component-name-in-template-casing': ['warn', 'PascalCase', {
        registeredComponentsOnly: false,
        ignores: ['/^v-/']
      }],
      'vue/component-options-name-casing': 'warn',
      'vue/custom-event-name-casing': 'warn',
      'vue/define-emits-declaration': 'error',
      'vue/define-macros-order': 'error',
      'vue/define-props-declaration': 'error',
      'vue/enforce-style-attribute': 'error',
      'vue/html-button-has-type': 'warn',
      'vue/html-comment-content-newline': 'warn',
      'vue/html-comment-content-spacing': 'warn',
      'vue/html-comment-indent': 'warn',
      'vue/next-tick-style': 'error',
      'vue/no-bare-strings-in-template': 'error',
      'vue/no-boolean-default': 'error',
      'vue/no-ref-object-reactivity-loss': 'error',
      'vue/no-required-prop-with-default': 'error',
      'vue/no-root-v-if': 'warn',
      'vue/no-template-target-blank': 'warn',
      'vue/padding-line-between-blocks': 'error',
      'vue/require-emit-validator': 'warn',
      'vue/require-macro-variable-name': 'warn',
      'vue/require-prop-comment': 'warn',
      'vue/require-typed-object-prop': 'error',
      'vue/require-typed-ref': 'error',
      'vue/script-indent': ['warn', 2, {'baseIndent': 1, 'switchCase': 1}],

      // accessibility rules:
      'vuejs-accessibility/alt-text': ['error', {'img': ['Image', 'VImg']}],
      'vuejs-accessibility/label-has-for': ['error', {required: {every: ['id']}}]
    }
  }
)
