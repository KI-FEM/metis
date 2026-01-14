<script setup lang="ts">
  import {computed} from 'vue'
  import type {Anchor} from 'vuetify'
  import {useWindowSize, useParentElement, useElementBounding} from '@vueuse/core'

  import {type storageKeyString, useOnboardingStore} from '@/stores/onboarding.ts'

  defineProps<{
    /**
     * A unique key that is used to store whether the onboarding step has been read.
     */
    storageKey: storageKeyString,
    /**
     * The text to show in the popup.
     */
    text: string,
    /**
     * Defines where the popup should be preferably placed.
     */
    location?: Anchor
  }>()

  const onboardingStore = useOnboardingStore()
  const windowSize = useWindowSize()
  const parentElement = useParentElement()
  const parentBoundingBox = useElementBounding(parentElement)

  const overlayPath = computed(() => {
    const borderRadius = Math.min(12, parentBoundingBox.width.value / 2, parentBoundingBox.height.value)
    const overlay = `M0,0 H${windowSize.width.value} V${windowSize.height.value} H0 Z`
    const spotlight = [`M${parentBoundingBox.left.value},${parentBoundingBox.top.value + borderRadius}`,
                       `v${parentBoundingBox.height.value - 2 * borderRadius}`,
                       `a${borderRadius},${borderRadius} 0 0 0 ${borderRadius},${borderRadius}`,
                       `h${parentBoundingBox.width.value - 2 * borderRadius}`,
                       `a${borderRadius},${borderRadius} 0 0 0 ${borderRadius},${-borderRadius}`,
                       `v-${parentBoundingBox.height.value - 2 * borderRadius}`,
                       `a${borderRadius},${borderRadius} 0 0 0 ${-borderRadius},${-borderRadius}`,
                       `h-${parentBoundingBox.width.value - 2 * borderRadius}`,
                       `a${borderRadius},${borderRadius} 0 0 0 ${-borderRadius},${borderRadius}`,
                       `Z`].join(' ')
    return `${overlay} ${spotlight}`
  })
</script>

<template>
  <Teleport to="#app">
    <svg v-if="!onboardingStore.isRead(storageKey)" class="onboarding-overlay">
      <path :class="storageKey" :d="overlayPath" />
    </svg>
  </Teleport>
  <v-menu v-if="!onboardingStore.isRead(storageKey)"
          class="onboarding-card"
          :close-on-content-click="false"
          :location="location"
          :model-value="true"
          offset="16"
          persistent
          :target="parentElement || undefined">
    <v-card max-width="400" width="fit-content">
      <v-card-text>{{ text }}</v-card-text>
      <v-card-actions class="justify-center">
        <v-btn :text="$t('onboardingHide')" @click="onboardingStore.markAsRead(storageKey)" />
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<style scoped lang="scss">
  .onboarding-overlay {
    position: fixed;
    top: 0;
    left: 0;
    height: 100%;
    width: 100%;
    opacity: .32;
    z-index: 1500;
    pointer-events: none;

    path {
      pointer-events: all;
    }
  }

  .onboarding-card .v-card {
    background-color: rgb(var(--v-theme-secondary-container)) !important;
    color: rgb(var(--v-theme-on-secondary-container)) !important;
    border: 3px solid rgb(var(--v-theme-outline)) !important;
  }
</style>
