<script setup lang="ts">
  import {useThemeStore} from '@/stores/theme.ts'

  const {isOnDarkParent} = defineProps<{
    /** Define the color mode of the parent element to ensure the correct appearance. **/
    isOnDarkParent?: boolean
  }>()

  const themeStore = useThemeStore()
</script>

<template>
  <v-btn :aria-label="$t('changeContrast')"
         icon
         :theme="isOnDarkParent ? themeStore.darkHighContrastTheme : themeStore.highContrastTheme"
         variant="text">
    <v-icon icon="mdi:mdi-brightness-6" />
    <v-tooltip activator="parent" :text="$t('changeContrast')" />
    <v-menu activator="parent"
            :close-on-content-click="false"
            open-on-click
            :theme="themeStore.highContrastTheme">
      <v-list mandatory
              :selected="[themeStore.contrast]"
              slim
              @update:selected="themeStore.contrast = $event[0] ?? 'standard'">
        <v-list-item prepend-icon="mdi:mdi-brightness-5" :title="$t('contrastStandard')" value="standard" />
        <v-list-item prepend-icon="mdi:mdi-brightness-6" :title="$t('contrastMedium')" value="medium" />
        <v-list-item prepend-icon="mdi:mdi-brightness-7" :title="$t('contrastHigh')" value="high" />
      </v-list>
    </v-menu>
  </v-btn>
</template>

<style scoped>

</style>
