<script setup lang="ts">
  import {useOnboardingStore} from '@/stores/onboarding'
  import {useTopicsStore} from '@/stores/topics'
  import {computed, ref, watchEffect} from 'vue'
  import VueMarkdown from 'vue-markdown-render'
  import {useDisplay} from 'vuetify'

  const emit = defineEmits<{
    close: [];
    setNavOpened: [value: boolean]
  }>()
  const {mobile} = useDisplay()
  const topicsStore = useTopicsStore()
  const onboardingStore = useOnboardingStore()

  const page = ref(0)

  const maxPage = computed(() => Object.values(onboardingStore.onboardingSteps).length - 1)

  watchEffect(() => {
    if (onboardingStore.showOnboarding) {
      page.value = 0
      emit('setNavOpened', false)
      document.body.classList.add('onboarding-active')
    } else {
      document.body.classList.remove('onboarding-active')
    }
  })

  const closeDialog = () => {
    if (onboardingStore.onboardingSteps[page.value].element) {
      const element = document.querySelector(onboardingStore.onboardingSteps[page.value].element)
      if (element) {
        (element as HTMLElement).classList.remove('to-front')
      }
    }
    document.body.classList.remove('onboarding-active')
    onboardingStore.setOnboardingCompleted(true)
    onboardingStore.showOnboarding = false
  }

  const movePage = (direction: number) => {
    const oldValue = page.value
    if (onboardingStore.onboardingSteps[oldValue].element) {
      const element = document.querySelector(onboardingStore.onboardingSteps[oldValue].element)
      if (element) {
        (element as HTMLElement).classList.remove('to-front')
      }
    }
    page.value = Math.min(maxPage.value, Math.max(0, page.value + direction))
    if (page.value == 1 || page.value == 2 || page.value == 6) {
      emit('setNavOpened', true)
    } else {
      emit('setNavOpened', false)
    }
    if (onboardingStore.onboardingSteps[page.value].element) {
      const element = document.querySelector(onboardingStore.onboardingSteps[page.value].element)
      if (element) {
        (element as HTMLElement).classList.add('to-front')
      }
    }
  }

  const pageProgress = computed(() => (page.value / maxPage.value * 100))
  const nextButtonEnabled = computed(() => {
    if (page.value == 2 && (topicsStore.selectedTopic == undefined || topicsStore.selectedTopic?.endpoint != "st")) {
      return false
    }
    return true
  })

  const backButtonEnabled = computed(() => {
    if (page.value == 0) {
      return true
    }
    return false
  })

  const alignItemsPosition = computed(() => {
    if(mobile.value && onboardingStore.onboardingSteps[page.value].position?.mobile) {
      return onboardingStore.onboardingSteps[page.value].position?.mobile
    }
    if(!mobile.value && onboardingStore.onboardingSteps[page.value].position?.desktop) {
      return onboardingStore.onboardingSteps[page.value].position?.desktop
    }
    return 'center'
  })
</script>

<template>
  <div>
    <Teleport to="body">
      <div v-if="onboardingStore.showOnboarding" />
    </Teleport>
    <v-dialog v-if="onboardingStore.showOnboarding"
              v-model="onboardingStore.showOnboarding"
              class="topmost"
              persistent
              :scrim="false"
              :style="{ alignItems: alignItemsPosition, marginTop: alignItemsPosition === 'start' ? '2rem' : '' }">
      <v-card id="onboarding-card" class="mx-auto w-lg-50 w-100">
        <v-card-title class="d-flex justify-space-between align-center">
          <div class="text-h6 ps-2">
            {{ $t('onboardingTitle') }}
          </div>
          <v-btn :aria-label="$t('closeButton')"
                 icon="fas fa-xmark"
                 variant="text"
                 @click="closeDialog" />
        </v-card-title>
        <v-card-text>
          <div v-for="(elem, id) in onboardingStore.onboardingSteps" :key="id">
            <div v-if="page==id">
              <VueMarkdown class="mb-n4" :source="$t(elem.textCode)" />
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="d-flex flex-row justify-space-between">
          <v-btn :disabled="backButtonEnabled" :text="$t('backButton')" @click="movePage(-1)" />
          {{ page+1 }} / {{ maxPage+1 }}
          <v-tooltip v-if="page<maxPage" :disabled="nextButtonEnabled" location="top">
            <span>{{ $t('onboardingTopicsTooltip') }}</span>
            <template #activator="{ props }">
              <div v-bind="props">
                <v-btn :disabled="!nextButtonEnabled"
                       v-bind="props"
                       @click="movePage(1)">
                  {{ $t('nextButton') }}
                </v-btn>
              </div>
            </template>
          </v-tooltip>
          <v-btn v-if="page==maxPage" :text="$t('closeButton')" @click="closeDialog" />
        </v-card-actions>
        <v-progress-linear v-model="pageProgress"
                           color="primary"
                           :height="5" />
      </v-card>
    </v-dialog>
  </div>
</template>

<style lang="scss" scoped>
  .topmost {
    z-index: 2409 !important;
  }
</style>
