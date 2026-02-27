<script setup lang="ts">
  import {useThemeStore} from '@/stores/theme.ts'

  const themeStore = useThemeStore()
</script>

<template>
  <v-btn :aria-label="$t('changeTheme')" icon variant="text">
    <v-icon icon="mdi:mdi-theme-light-dark" />
    <v-tooltip activator="parent" :text="$t('changeTheme')" />
    <v-menu activator="parent"
            :close-on-content-click="false"
            open-on-click
            :theme="themeStore.theme">
      <v-list mandatory
              :selected="[themeStore.colorMode]"
              slim
              @update:selected="themeStore.colorMode = $event[0]">
        <v-list-item prepend-icon="fas fa-desktop" :title="$t('themeAuto')" value="auto" />
        <v-list-item prepend-icon="fas fa-sun" :title="$t('themeLight')" value="light" />
        <v-list-item prepend-icon="fas fa-moon" :title="$t('themeDark')" value="dark" />
      </v-list>
    </v-menu>
  </v-btn>
</template>

<style scoped>

</style>
