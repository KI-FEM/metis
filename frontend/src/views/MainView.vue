<script setup lang="ts">
  import {ref, watchEffect, onMounted} from 'vue'
  import {useDisplay} from 'vuetify'
  import {useRoute, useRouter} from 'vue-router'

  import {useThemeStore} from '@/stores/theme'
  import {useTopicsStore} from '@/stores/topics'
  import {useChatStore} from '@/stores/chat'
  import {useOnboardingStore} from '@/stores/onboarding'
  import {useStudyStore} from '@/stores/study'

  import moodyLogo from '@/assets/moody.svg'
  import wumLogo from '@/assets/wum.svg'

  import UserOnboarding from '@/components/UserOnboarding.vue'
  import TopicsList from '@/components/TopicsList.vue'
  import HelpList from '@/components/HelpList.vue'
  import ThemeToggleButton from '@/components/buttons/ThemeChangeButton.vue'
  import HelpButton from '@/components/buttons/HelpButton.vue'
  import LanguageChangeButton from '@/components/buttons/LanguageChangeButton.vue'
  import ContrastChangeButton from '@/components/buttons/ContrastChangeButton.vue'
  import SettingsButton from '@/components/buttons/SettingsButton.vue'

  const route = useRoute()
  const router = useRouter()
  const {mobile, thresholds, md} = useDisplay()
  const themeStore = useThemeStore()
  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()
  const onboardingStore = useOnboardingStore()
  const studyStore = useStudyStore()

  const showDrawer = ref<boolean | null>(null)

  topicsStore.fetchTopics()
  chatStore.fetchModels()

  if (route.name === 'topics')
    showDrawer.value = true

  watchEffect(async () => {
    // close mobile drawer on loading error
    if (topicsStore.isError && !md.value)
      showDrawer.value = false
  })
  const showStudyNotification = ref(false)

  function setDrawerOpened(value: boolean) {
    if (mobile.value)
      showDrawer.value = value
  }

  onMounted(() => {
    if (studyStore.isDateAfterTarget()) { 
      showStudyNotification.value = true
    }
  })

  function openStudyPage() {
    router.push({ name: 'study' })
  }
</script>

<template>
  <v-snackbar v-model="showStudyNotification"
              color="success"
              location="top"
              :timeout="100000">
    {{ $t('postQuestionnaireText') }}
    <template #actions>
      <v-chip class="bg-primary"
              prepend-icon="fa-solid fa-arrow-right"
              :text="$t('toStudyPage')" 
              :to="{name: 'study'}" />
    </template>
  </v-snackbar>

  <v-app-bar app
             class="bg-brand"
             :theme="themeStore.darkTheme">
    <v-app-bar-title class="text-headline-md" tag="h1">
      <RouterLink class="text-decoration-none font-weight-bold" :to="{name: 'start'}">{{ $t('chatBot') }}</RouterLink>
    </v-app-bar-title>
    <template #prepend>
      <v-app-bar-nav-icon v-if="$route.name !== 'help' && $route.name !== 'faq'"
                          :aria-label="showDrawer ? $t('closeNavigation') : $t('openNavigation')"
                          icon="fas fa-bars"
                          @click="showDrawer = !showDrawer" />
    </template>
    <div id="survey">
      <v-btn :aria-label="$t('openStudyPage')"
             class="text-label-sm position-relative"
             icon
             :theme="themeStore.darkHighContrastTheme">
        <v-badge class="poll-badge"
                 color="#db3636"
                 dot
                 location="top end"
                 :model-value="showStudyNotification"> 
          <v-icon icon="fas fa-poll fa-fw" />
        </v-badge>
        <v-tooltip activator="parent"
                   :text="$t('openStudyPage')"
                   :theme="themeStore.theme" />
        <v-menu activator="parent"
                max-width="420"
                offset="16"
                :theme="themeStore.theme">
          <v-list lines="two" rounded="xl">
            <v-list-subheader class="text-title-sm" inset :title="$t('evalSubheader')" />
            <v-list-item :prepend-icon="'fas fa-link'"
                         :subtitle="$t('openStudyPageDescription')"
                         :title="$t('openStudyPage')"
                         @click="openStudyPage" />
          </v-list>
        </v-menu>
      </v-btn>
    </div>
    <div id="other-chatbots">
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
  </v-app-bar>

  <v-navigation-drawer v-model="showDrawer"
                       mobile-breakpoint="md"
                       style="padding: 0!important">
    <template #prepend>
      <div class="pa-2">
        <div id="nav-header" class="h-100">
          <div class="mt-8 d-flex justify-center align-baseline gc-4">
            <h2 id="navigation-title" class="d-flex align-center text-headline-lg">
              <v-icon :icon="$route.name === 'help' || $route.name === 'faq' ? 'fas fa-book-open' : 'mdi mdi-bookshelf'" />
              {{ $route.name === 'help' || $route.name === 'faq' ? 'Hilfebereich' : $t('topics') }}
            </h2>
          </div>
          <div class="mt-2 mb-6 px-4 text-center text-title-md">
            {{ $t('topicsMotivation') }}
          </div>
        </div>
      </div>
    </template>
    <div id="topics" class="pa-2">
      <HelpList v-if="$route.name === 'help' || $route.name === 'faq'" v-model="showDrawer" />
      <TopicsList v-else />
    </div>
    <template #append>
      <div class="pa-2">
        <v-divider />
        <v-container id="settings" class="d-flex flex-wrap justify-center ga-4">
          <ContrastChangeButton />
          <ThemeToggleButton />
          <LanguageChangeButton />
          <HelpButton />
          <!--        <SettingsButton /> -->
        </v-container>
        <v-container class="text-center pt-0">
          <RouterLink :to="{name: 'imprint'}">{{ $t('imprint') }}</RouterLink>
        </v-container>
      </div>
    </template>
  </v-navigation-drawer>

  <UserOnboarding @set-nav-opened="(v : boolean) => setDrawerOpened(v)" />

  <v-main class="bg-surface-container" scrollable>
    <v-container height="100%" :max-width="thresholds.md">
      <RouterView />
      <!--      <div class="h-100 d-flex flex-column justify-center align-center ga-3"> -->
      <!--        <v-alert v-if="topicsStore.isError" -->
      <!--                 color="error-container" -->
      <!--                 max-width="600" -->
      <!--                 type="error"> -->
      <!--          <I18nT keypath="loadingError" scope="global"> -->
      <!--            <a href="#" @click.prevent="topicsStore.fetchTopics">{{ $t('loadingErrorTryAgain') }}</a> -->
      <!--          </I18nT> -->
      <!--        </v-alert> -->
      <!--        <v-alert v-else-if="$route.name === 'topics'" -->
      <!--                 color="secondary-container" -->
      <!--                 max-width="600" -->
      <!--                 :text="$t('chatPlaceholder')" -->
      <!--                 type="info" /> -->
      <!--      </div> -->
    </v-container>
  </v-main>
</template>

<style lang="scss" scoped>
  .to-front.white-shadow {
    box-shadow: 8px 10px -5px var(--v-shadow-key-umbra-opacity, rgba(255, 255, 255, 0.2)), 0px 16px 24px 2px var(--v-shadow-key-penumbra-opacity, rgba(255, 255, 255, 0.14)), 0px 6px 30px 5px var(--v-shadow-key-ambient-opacity, rgba(255, 255, 255, 0.12)) !important
  }

  nav:has(#topics.to-front) {
    z-index: 2019 !important;
    border: rgba(0, 0, 0, .3);

    & #nav-header {
      box-shadow: inset 0px 0px 0px 9999px rgba(0, 0, 0, .3), 0px 0px 0px 9999px rgba(0, 0, 0, .3) !important;
    }

    & #settings {
      box-shadow: inset 0px 0px 0px 9999px rgba(0, 0, 0, .3), 0px 0px 0px 9999px rgba(0, 0, 0, .3) !important;
    }

    & .to-front {
      box-shadow: 0px 0px 0px 9999px rgba(0, 0, 0, .3) !important;
      border-radius: 1rem;
    }
  }

  //nav:has(#settings.to-front) is in main.scss since scoped limits the selector to the current file and v-avatar cannot be modified

  header:has(.to-front) {
    z-index: 2018 !important;

    & .to-front {
      z-index: 2019 !important;
      display: inline-block;
      position: relative;
      border-radius: .7rem;
      box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 0.4), 0 0 20px 10px rgba(var(--v-theme-accent), 0.4);

      &::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        box-shadow: 0px 0px 0px 9999px rgba(0, 0, 0, .3);
        border-radius: .7rem;
      }
    }
  }
  
  /* Badge positioning for poll icon */
  .poll-badge {
    position: relative;
    display: inline-flex;
  }
  
  .poll-badge :deep(.v-badge__badge) {
    top: -2px !important;
    right: -2px !important;
  }
</style>
