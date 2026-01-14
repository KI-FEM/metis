import {createApp} from 'vue'

import '@fontsource/source-sans-pro'
import '@fontsource-variable/montserrat'
import '@fontsource/source-code-pro'
import '@/assets/main.scss'

import App from '@/App.vue'
import router from '@/plugins/router'
import pinia from '@/plugins/pinia'
import vuetify from '@/plugins/vuetify'
import i18n from '@/plugins/i18n'

const app = createApp(App)

app.use(router)
app.use(pinia)
app.use(vuetify)
app.use(i18n)

app.mount('#app')
