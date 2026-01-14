import '@fortawesome/fontawesome-free/css/all.css'
import '@mdi/font/css/materialdesignicons.css'
import {createVuetify} from 'vuetify'
import {md3} from 'vuetify/blueprints'
import {VFileUpload} from 'vuetify/labs/VFileUpload'
import {aliases, fa} from 'vuetify/iconsets/fa'
import {mdi} from 'vuetify/iconsets/mdi'
import {createVueI18nAdapter} from 'vuetify/locale/adapters/vue-i18n'
import {useI18n} from 'vue-i18n'

import i18n from '@/plugins/i18n'
import theme from '@/assets/material-theme.json'

const vuetify = createVuetify({
  locale: {
    adapter: createVueI18nAdapter({i18n, useI18n})
  },
  icons: {
    defaultSet: 'fa',
    aliases,
    sets: {fa, mdi}
  },
  blueprint: md3,
  components: {
    VFileUpload
  },
  theme: {
    themes: {
      light: {dark: false, colors: theme.schemes['light']},
      lightMediumContrast: {dark: false, colors: theme.schemes['light-medium-contrast']},
      lightHighContrast: {dark: false, colors: theme.schemes['light-high-contrast']},
      dark: {dark: true, colors: theme.schemes['dark']},
      darkMediumContrast: {dark: true, colors: theme.schemes['dark-medium-contrast']},
      darkHighContrast: {dark: true, colors: theme.schemes['dark-high-contrast']}
    }
  },
  defaults: {
    // apply MD3 to layout components
    VAppBar: {
      height: 64
    },
    VNavigationDrawer: {
      width: 360
    },
    VTooltip: {
      location: 'top',
      offset: 4
    }
  }
})

export default vuetify
