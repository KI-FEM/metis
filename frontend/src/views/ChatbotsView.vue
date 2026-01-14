<script setup lang="ts">
  import {ref} from 'vue'

  import {useThemeStore} from '@/stores/theme'
  import {useTopicsStore} from '@/stores/topics'
  import {useChatStore} from '@/stores/chat'
  import {useOnboardingStore} from '@/stores/onboarding'

  import tuDresdenLogo from '@/assets/tu_dresden.svg'
  import moodyLogo from '@/assets/moody.svg'
  import wumLogo from '@/assets/wum.svg'

  import ChatbotList from '@/components/ChatbotList.vue'
  import HelpList from '@/components/HelpList.vue'
  import ThemeToggleButton from '@/components/buttons/ThemeChangeButton.vue'
  import HelpButton from '@/components/buttons/HelpButton.vue'
  import LanguageChangeButton from '@/components/buttons/LanguageChangeButton.vue'
  import ContrastChangeButton from '@/components/buttons/ContrastChangeButton.vue'
  import SettingsButton from '@/components/buttons/SettingsButton.vue'
  import OnboardingStep from '@/components/OnboardingStep.vue'

  const themeStore = useThemeStore()
  const chatbotsStore = useTopicsStore()
  const chatStore = useChatStore()
  const onboardingStore = useOnboardingStore()

  const openDrawer = ref<boolean | null>(null)

  chatbotsStore.fetchTopics()
  chatStore.fetchModels() // preload models
</script>

<template>
  <v-app-bar app
             class="bg-brand"
             :theme="themeStore.darkTheme">
    <v-img :alt="$t('logoTuDresden')"
           class="flex-grow-0"
           :src="tuDresdenLogo"
           width="30" />
    <v-app-bar-title class="text-headline-md" tag="h1">
      <RouterLink class="text-decoration-none font-weight-bold" :to="{name: 'start'}">{{ $t('chatBot') }}</RouterLink>
    </v-app-bar-title>
    <template #prepend>
      <v-app-bar-nav-icon v-if="$route.name !== 'help' && $route.name !== 'faq'"
                          :aria-label="openDrawer ? $t('closeNavigation') : $t('openNavigation')"
                          icon="fas fa-bars"
                          @click="openDrawer = !openDrawer" />
    </template>
    <template #append>
      <div>
        <v-btn :aria-label="$t('otherChatbots')" icon :theme="themeStore.darkHighContrastTheme">
          <v-icon icon="fas fa-robot fa-fw" />
          <v-tooltip activator="parent"
                     location="start"
                     :text="$t('otherChatbots')"
                     :theme="themeStore.theme" />
          <v-menu activator="parent"
                  max-width="420"
                  offset="24"
                  open-on-click
                  :theme="themeStore.theme">
            <v-list lines="three">
              <v-list-subheader class="text-title-sm" :title="$t('otherChatbotsTitle') + ':'" />
              <v-list-item href="https://whatsurmood.de/"
                           :subtitle="$t('wumDescription')"
                           :title="$t('wumTitle')">
                <template #prepend>
                  <v-img alt="" :src="wumLogo" />
                </template>
              </v-list-item>
              <v-list-item href="https://moodybot.de/"
                           :subtitle="$t('moodyDescription')"
                           :title="$t('moodyTitle')">
                <template #prepend>
                  <v-img alt="" :src="moodyLogo" />
                </template>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-btn>
      </div>
    </template>
  </v-app-bar>

  <v-navigation-drawer v-model="openDrawer"
                       mobile-breakpoint="lg"
                       style="padding: 0!important">
    <template #prepend>
      <div class="pa-2">
        <div class="h-100">
          <div class="mt-8 d-flex justify-center align-baseline gc-4">
            <h2 class="d-flex align-center text-headline-lg">
              <v-icon :icon="$route.name === 'help' || $route.name === 'faq' ? 'fas fa-book-open' : 'far fa-comments'"
                      start />
              {{ $route.name === 'help' || $route.name === 'faq' ? 'Hilfebereich' : $t('chatbots') }}
            </h2>
          </div>
          <div class="mt-2 mb-6 px-4 text-center text-title-md">
            {{ $t('chatbotsMotivation') }}
          </div>
        </div>
      </div>
    </template>
    <div class="pa-2 h-100 d-flex flex-column">
      <HelpList v-if="$route.name === 'help' || $route.name === 'faq'" v-model="openDrawer" />
      <ChatbotList v-else />
      <OnboardingStep v-if="openDrawer && onboardingStore.isRead('settings')"
                      location="top"
                      storage-key="topicSelection"
                      :text="$t('onboardingTopicSelection')" />
    </div>
    <template #append>
      <div class="pa-2">
        <v-divider />
        <v-container class="d-flex flex-wrap justify-center ga-4">
          <OnboardingStep v-if="openDrawer" storage-key="settings" :text="$t('onboardingSettings')" />
          <ContrastChangeButton />
          <ThemeToggleButton />
          <LanguageChangeButton />
          <HelpButton />
          <SettingsButton />
        </v-container>
        <v-container class="text-center pt-0">
          <RouterLink :to="{name: 'imprint'}">{{ $t('imprint') }}</RouterLink>
        </v-container>
      </div>
    </template>
  </v-navigation-drawer>

  <v-main class="bg-surface-container" scrollable>
    <div v-if="$route.name ==='chatbots'" class="h-100 d-flex flex-column justify-center align-center ga-6">
      <h2 class="text-headline-md">{{ $t('chatWelcome') }}</h2>
      <div v-if="!chatbotsStore.isError" class="position-absolute top-0 left-0 ma-4 d-flex align-center">
        <v-icon class="flex-shrink-0"
                :icon="openDrawer ? 'fas fa-arrow-left-long' : 'fas fa-arrow-up-long'"
                start
                style="--fa-animation-duration: 1.5s; width: 40px;" />
        <span class="text-title-md">{{ $t('chatPlaceholder') }}</span>
      </div>
      <v-alert v-else
               color="error-container"
               max-width="600"
               type="error">
        <I18nT keypath="loadingError" scope="global">
          <a href="#" @click.prevent="chatbotsStore.fetchTopics">{{ $t('loadingErrorTryAgain') }}</a>
        </I18nT>
      </v-alert>
    </div>
    <RouterView />
  </v-main>
</template>

<style scoped lang="scss">

</style>
