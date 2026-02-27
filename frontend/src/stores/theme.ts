import {computed} from 'vue'
import {defineStore} from 'pinia'
import {useTheme} from 'vuetify'
import {useStorage, usePreferredContrast, usePreferredDark} from '@vueuse/core'

export const useThemeStore = defineStore('theme', () => {
  const colorModeStorage = useStorage<'auto' | 'light' | 'dark'>('colorMode', 'auto')
  const contrastStorage = useStorage<'standard' | 'medium' | 'high'>('contrast', usePreferredContrast().value === 'more' ? 'medium' : 'standard')
  const vuetifyTheme = useTheme()

  const colorModeName = computed(() => colorModeStorage.value === 'auto' ? (usePreferredDark().value ? 'dark' : 'light') : colorModeStorage.value)

  const contrastName = computed(() => contrastStorage.value === 'standard' ? '' : (contrastStorage.value.charAt(0).toUpperCase() + contrastStorage.value.slice(1) + 'Contrast'))

  const theme = computed(() => {
    vuetifyTheme.change(colorModeName.value + contrastName.value)
    return vuetifyTheme.global.name.value
  })

  const lightTheme = computed(() => 'light' + contrastName.value)

  const darkTheme = computed(() => 'dark' + contrastName.value)

  const highContrastTheme = computed(() => colorModeName.value + 'HighContrast')

  const darkHighContrastTheme = computed(() => 'darkHighContrast')

  return {
    theme,
    lightTheme,
    darkTheme,
    highContrastTheme,
    darkHighContrastTheme,
    colorMode: colorModeStorage,
    contrast: contrastStorage
  }
})
